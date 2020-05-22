import requests #***
from bs4 import BeautifulSoup #***
import copy
import pandas as pd #for creating dataframe ***
import numpy as np
from selenium import webdriver #for getting around website's protections ***
import itertools #for finding 4/3/2-player lineup combinations
import sys #for error handling
from difflib import SequenceMatcher
import time

'''
This program gathers all the lineup data for both teams in a game so we can
evaluate minutes, offensive and defensive efficiencies, etc for each lineup.

This scraper works on a school's website in the SIDEARM Sports html format.
ex: http://uclabruins.com/schedule.aspx?schedule=496

Author: Matt Wang
'''

#GLOBALS
START_TIME_M = "20:00"
START_TIME_W = "10:00"
START_TIME_OT = "05:00"
POSS_RATIO = 0.44
GAME_MINUTES = 40
ONE_PCT = 0.01


'''
Use Selenium library to circumvent NCAA website's protection against scraping

Returns: a BeautifulSoup object that works on the NCAA site
'''
def get_site(url):
    browser = webdriver.Firefox()
    browser.get(url)
    time.sleep(0.2)
    html = browser.execute_script('return document.body.innerHTML')
    #html = browser.page_source
    browser.close()
    return_soup = BeautifulSoup(html, 'html.parser')
    if not return_soup:
        omg = raw_input("THIS RAN! ")
        browser = webdriver.Firefox()
        browser.get(url)
        time.sleep(0.2)
        html = browser.execute_script('return document.body.innerHTML')
        browser.close()
        return_soup = BeautifulSoup(html, 'html.parser')
    return return_soup



'''
Takes one game's boxscore page and scrapes "raw" play by play table

Args:
soup - game boxscore page in BeautifulSoup form
homeaway - "HOME" or "AWAY"
mw - men or women? 'M' or 'W' (all caps)

Return: All the data needed as individual lists
(times, scores, team_details, opp_details, end_of_period_locs)
'''
def get_pbp(soup, homeaway, mw):
    if mw == 'M':
        start_time = START_TIME_M
        OTcheck = 1
    elif mw == 'W':
        start_time = START_TIME_W
        OTcheck = 3
    
    table_soup = soup.findAll("table", {"class":"sidearm-table play-by-play"})
    
    end_of_period_locs = []
    index = 0
    
    times = []   
    scores = []
    details_team = []
    details_opp = []
        
    #as you loop through tables for each period, add game data AND rows for
    #... start and end of period
    periods_played = 0
    index = 0
    for n, row in enumerate(table_soup):
        #add start of period info
        if periods_played <= OTcheck: times.append(start_time)
        else: times.append(START_TIME_OT)
        if periods_played == 0: scores.append("0-0")
        else: scores.append(scores[index-1])
        details_team.append("START OF PERIOD")
        details_opp.append("START OF PERIOD")
        index = index+1

        #TIMES
        current_time = start_time
        for t in table_soup[n].findAll("th", {"scope":"row"}):
            index = index+1
            if ':' not in t.contents[0]: #if the data isn't a valid time
                times.append(current_time)
            else:
                current_time = t.contents[0]
                times.append(current_time)
        
        #SCORES
        for s in table_soup[n].findAll("td", {"class":"hide-on-large text-bold"}):
            try:
                if homeaway == "AWAY":
                    scores.append(str(s.contents[1]).strip())
                elif homeaway == "HOME":
                    scores.append(flip(str(s.contents[1]).strip()))
                else:
                    print("ERROR with homeaway argument. Likely doesn't equal" \
                          + " 'HOME' or 'AWAY'")
                    break
            except:
                scores.append("")
    
        current_score = "0-0"
        for num, item in enumerate(scores):
            if "PERIOD" not in item:
                if item: #if nonempty
                    current_score = item
                else:
                    scores[num] = current_score
                
        #TEAM AND OPPONENT GAME DETAILS
        for t in table_soup[n].findAll("td", \
                                {"class":"text-right hide-on-medium-down"}):
            try: details_team.append(t.contents[0].replace("  ", " ").upper())
            except: details_team.append("")
        for num, o in enumerate(table_soup[n].findAll("td", \
                                                      {"style":"width:40%"})):
            if num%2==1:
                try: details_opp.append(o.contents[0].replace("  ", " ").upper())
                except: details_opp.append("")
        
        #add end of period info
        times.append("00:00")
        scores.append(scores[index-1])
        details_team.append("END OF PERIOD")
        details_opp.append("END OF PERIOD")
        periods_played = periods_played+1
            
    #program defaults to setting team as away, so flip if needed
    if homeaway == "HOME":
        temp = details_opp
        details_opp = details_team
        details_team = temp

    return times, scores, details_team, details_opp, end_of_period_locs


'''
Given all the data collected in get_pbp, create a nice formatted table

This function also adds rows with appropriate data for end of period and start
of period, and columns with the current lineups for each time.

Args:
cols - lists of data [TIMES, SCORES, TEAM_DETAILS, OPP_DETAILS]
starters
arg - integer - lets us run this function on multiple html styles
    0 - SidearmSports
    1 - PrestoSports
    2 - CBSi

Return:
table - a nested list; format:
      - [TIME, SCORE, TEAM_DETAIL, OPP_DETAIL, TEAM_LINEUP, OPP_LINEUP]
'''
def copy_table(cols, starters, arg):        
    table = []
    periods_played = 0 #used to run update_court
    
    court = sorted(starters)

    #ADD DATA
    for index in range(len(cols[0])):
        #run update_court to calculate lineups if it's not the very beginning
        #..of the game and we know the starters are out there
        if index != 0:
            court_holder = update_court(court, cols[2], index, arg)
        else:
            court_holder = (court, False)
        court = sorted(court_holder[0])
        midsub = court_holder[1]
                
        temp = []
        temp.append(cols[0][index]) #times
        temp.append(cols[1][index]) #scores
        #team details
        temp.append(cols[2][index].replace(',', '.'))
        #opponent details
        temp.append(cols[3][index].replace(',', '.'))
        if midsub:
            temp.append(["SUBSTITUTION IN PROGRESS"])
        else:
            temp.append(court) #lineup

        table.append(temp)
    
    #for i in range(len(table)):
        #print table[i][0], table[i][4]
    #print "len copy_table:", len(table)
                     
    #RUN FIND_MISSING_PLAYERS TO FILL IN GAPS IN PLAY DATA
    end_locs = []
    for num, row in enumerate(cols[2]):
        if "END OF" in row:
            end_locs.append(num)
    for index, loc in enumerate(end_locs[:len(end_locs)-1]):
        start = end_locs[index]+1
        end = end_locs[index+1]+1
        segment = table[start : end]
        #print start, end
        mod_table = find_missing_players(segment, 0, arg)
        table = table[:start] + mod_table + table[end:]
    
    #df = pd.DataFrame(data=table)
    #df.to_csv('test_copytable.csv') 
    
    return table


'''
Helper to update the list of who is on the court and keep track of subs. Used
in copy_table()

Args:
court - list of players on court
col - specified list in cols (the argument of copy_table), will either
      correspond to column of team details, or opponent details
index - iteration of loop in copy_table
arg - integer - lets us run this function on multiple html styles
    0 - SidearmSports
    1 - PrestoSports
    2 - CBSi

Return:
(new, midsub)
new - new list of players on court
midsub - tracks whether we are in the middle of a substitution. responsible for
         lines that read 'subbing in progress'
'''
def update_court(court, col, index, arg):
    if arg == 0:
        tagin = "SUB IN"
        tagin_replace = "SUB IN BY "
        tagout = "SUB OUT"
        tagout_replace = "SUB OUT BY "
        tag1 = "SUB"
        tag2 = "SUB"
    elif arg == 1:
        tagin = "ENTERS THE GAME"
        tagin_replace = "ENTERS THE GAME"
        tagout = "GOES TO THE BENCH"
        tagout_replace = "GOES TO THE BENCH"
        tag1 = "ENTERS THE"
        tag2 = "TO THE BENCH"
    elif arg == 2:
        tagin = "SUB IN"
        tagin_replace = "SUB IN : "
        tagout = "SUB OUT"
        tagout_replace = "SUB OUT: "
        tag1 = "SUB"
        tag2 = "SUB"
    
    midsub = False #tells you when sub in line is read without sub out line
    copy = court[:]
    
    #it's not possible for lineup changes to be made exactly at end of period
    if "END OF" in col[index]:
        return copy, midsub
    
    #if it's a new period, start with a blank slate. this method is not called
    #..on the original run through when starters are known already
    elif "START OF" in col[index]:
        return [], midsub
    
    elif tagin in col[index]:
        name = col[index].replace(tagin_replace, "")
        name = nice_name(name)
        
        if name not in copy:
            copy.append(name)

        if tag1 in col[index+1] or tag2 in col[index+1]:
            midsub = True
        
        return copy, midsub
    
    elif tagout in col[index]:
        name = col[index].replace(tagout_replace, "")
        name = nice_name(name)
        
        if tag1 in col[index+1] or tag2 in col[index+1]:
            midsub = True
        
        try:
            copy.remove(name)
            return copy, midsub
        except:
            #print "SPECIAL CASE"
            return copy, midsub
    
    else:
        return copy, midsub
        

'''
Gets starting lineup from gamecast page. Used at start of copy_table()

Args:
soup - gamecast page as BeautifulSoup data
homeaway

Returns:
starters - list of length 5 with each player in the starting lineup
None - if exhibition game
'''
def get_starters(soup, homeaway):
    game_info = soup.find('aside', {'class':'game-details'}).text.upper()
    if 'EXHIBITION' in game_info:
        print("exhibition game. returning None.")
        return None
    
    table_info = soup.find('table', {'class':'sidearm-table'}).text.upper()
    if "EXH" in table_info:
        print("exhibition game. returning None.")
        return None
    
    starters = []
    
    if homeaway == "AWAY":
        table = soup.find('div', {'id':'DataTables_Table_0_wrapper'})
    else:
        table = soup.find('div', {'id':'DataTables_Table_1_wrapper'})
    
    if not table: print(table)
    
    rows = table.find_all('th', {'scope':'row'})
    for row in rows[:5]:
        name = row.text
        space = name.find(' ')
        name = name[space+1:].upper()
        name = nice_name(name)
        starters.append(name)

    #print "starters:", starters
    return starters


'''
Helper to flip order of score string. Basically "44-30" becomes "30-44".

Used to make sure score is always in format: "your_score-opponent_score"
(when getting data for home team)
'''
def flip(score):
    lst = score.split('-')
    return str(lst[1] + '-' + lst[0])


'''
Pulls team names

Args:
soup - gamecast page in BeautifulSoup form

Returns:
(AWAY_NAME, HOME_NAME)
'''
def get_team_names(soup):
    container = soup.find("div", {"class":"box-score-graphic"})
    teams = container.findAll("div", {"class":"team"})
    
    names = []
    for n, x in enumerate(teams):
        names.append(str(teams[n].div.img)[ \
                                     10 : str(teams[n].div.img).find(" logo")])
    
    return names


'''
Helper method to solve the problem with not knowing who starts periods other
than the first half.  Helper function called in copy_table

Args:
table - a segment of the table to evaluate; ex: feed it the second half data
ind - index of end of locations list that marks row number that corresponds to
      the start of the period
teamopp - 0 if we want to run this function on team's data
          1 if we want to run this function on opponent's data
arg - integer - lets us run this function on multiple html styles
    0 - SidearmSports
    1 - PrestoSports
    2 - CBSi

Returns:
tcopy - modified deep copy of inputted table
'''
def find_missing_players(table, teamopp, arg):
    if arg == 0:
        tagout = "SUB OUT"
        tagout_replace = "SUB OUT BY "
    elif arg == 1:
        tagout = "GOES TO THE BENCH"
        tagout_replace = "GOES TO THE BENCH"
    elif arg == 2:
        tagout = "SUB OUT"
        tagout_replace = "SUB OUT: "    
    
    if teamopp == 0: mark = 2
    elif teamopp == 1: mark = 3
    
    tcopy = copy.deepcopy(table)
    flag = True #True if player subbed in needs to be added to rows
    
    '''
    If a player is mentioned coming out, add that player to the lineup list
    for all the rows above. We're only looking for players who started the
    period, and the table as is has data for every nonstarter. So if the player
    was already listed in any of the lineup lists, they didn't start, so stop
    trying to add them
    '''
    for n, row in enumerate(tcopy):
        if tagout in row[mark]:
            name = row[mark].replace(tagout_replace, "")
            name = nice_name(name)
            
            for x in reversed(tcopy[:n]):
                #print x[0], x[4]
                if name in x[mark+2]:
                    flag = False
                    break
            
            #print name, flag, "\n"
            
            if flag:
                for num, x in enumerate(tcopy[:n]):
                    if "SUBSTITUTION IN PROGRESS" not in tcopy[num][mark+2]:
                        tcopy[num][mark+2].append(name)
                        tcopy[num][mark+2] = sorted(tcopy[num][mark+2])
                            
            flag = True
            
    '''
    And if a player never subs out, look for details that involve them anywhere
    in the half and that's our missing starter(s), because everyone else will
    have been accounted for
    '''
    missing = find_super_missing_players(tcopy, teamopp, arg)
    #if missing:
        #print len(missing), "missing players via find_super_missing_players:", missing
    for num, x in enumerate(tcopy):
        for player in missing:
            if "SUBSTITUTION IN PROGRESS" not in tcopy[num][mark+2]:
                tcopy[num][mark+2].append(player)
                tcopy[num][mark+2] = sorted(tcopy[num][mark+2])
    
    #for i in range(len(tcopy)):
        #print tcopy[i][0], tcopy[i][4]
    
    return tcopy



'''
Helper for find_missing_players() to find players who never sub out

Args:
table
teamopp - 0 if we want to run this function on team's data
          1 if we want to run this function on opponent's data
arg - integer - lets us run this function on multiple html styles
    0 - SidearmSports
    1 - PrestoSports
    2 - CBSi

Return:
missing - list of players that never subbed out of the period
'''
def find_super_missing_players(table, teamopp, arg):
    if teamopp == 0: mark = 2
    elif teamopp == 1: mark = 3
    
    found = []
    for row in table:
        for player in row[mark+2]:
            if player not in found:
                found.append(player)

    missing = []
    
    for row in table:
        if " BY " in row[mark] and arg != 1:
            if arg == 0:
                name = row[mark][row[mark].find("BY ")+3:].\
                    replace("(FASTBREAK)", "").replace("(IN THE PAINT)", "")
                
            if arg == 2:
                name = row[mark]
                if "BY " in name:
                    name = name[name.find("BY ")+3:].replace('[FB/PNT]', '').\
                        replace('[PNT]', '').replace('[FB]', '').\
                        replace('THE BENCH', '')
                else:
                    name = name[name.find(": ")+2:].replace('SUB IN : ', '').\
                           replace('SUB OUT:', '')
                name = remove_foul_details(name)
                
            name = nice_name(name) 
            
            if name not in found and name != "TEAM" and "(DEADBALL)" not in name \
                                                    and "(TEAM)" not in name: 
                if name not in missing and name:
                    missing.append(name)
                    
        elif arg == 1:
            replace = ["FOUL", "ENTERS THE GAME", "GOES TO THE BENCH", \
                       "TURNOVER", "MISSED", "3-PT.", \
                       "DEFENSIVE", "REBOUND", "OFFENSIVE", "DEADBALL", \
                       "MADE", "ASSIST", "LAYUP", "STEAL", "BLOCK", \
                       "TIP-IN",
                       "THROW", "START OF PERIOD", "END OF PERIOD", "DUNK",\
                       "TECHNICAL", "BY", "FREE", "JUMP", "SHOT", "TEAM"]
            
            name = row[mark]
            
            for word in replace:
                name = name.replace(word, "")
            
            name = nice_name(name) 
            
            if name not in found and name != "" and name != ".":
                if name not in missing:
                    missing.append(name)
    
    return missing


'''
Takes the play data table created by copy_table and creates a table that holds
data for each lineup rotation and the stats for that rotation.

FORMAT for each row:
Team, Opponent, Lineup, Time @start of rotation, Time @end, Total time on court,
    Score @start, Score @end, +/-, # possessions, *ALL OFFENSIVE STATS*, *ALL
    DEFENSIVE STATS*
    
    OFFENSEIVE/DEFENSEIVE STATS:
    2ptFGM, 2ptFGA, 3ptFGM, 3ptFGA, FTM, FTA, AST, TO, OREB, STL, BLK

Args:
in_table - game's play data table in nested list form (like the first entry
           of the tuple returned by copy_table())
names - tuple of (team_name, opponent_name) in nested list form (like that
        returned by get_team_names())
filename - hostname.replace(' ', '').lower()
date
arg

Return:
no return
'''
def lineup_table(in_table, names, filename, date, arg):
    table = []
    
    #find locations where lineup changes are made
    subrows = [] #also has location of last row
    lineup_atm = []
    for n, row in enumerate(in_table):
        if (lineup_atm != row[4] and row[4] != ["SUBSTITUTION IN PROGRESS"]) \
           or "START OF" in row[2]:
            subrows.append(n)
            lineup_atm = row[4]
    #handle games with no sub info
    if len(subrows) < 6:
        print("\nERROR: it's likely the game page exists with play-by-play " \
              "data but has no substitution information. Skipping game.\n\n")
        return
    subrows.append(len(in_table)-1)
    
    #print len(subrows), subrows, len(in_table)
    
    #calculate info for each rotation
    for n, x in enumerate(subrows[:-1]):
        temp = []
        
        temp.append(date) #date
        temp.append(names[0]) #team name
        temp.append(names[1]) #opponent name
        temp.append(in_table[subrows[n]][0]) #start time
        
        #end time
        if n == len(subrows[:-1])-1:
            temp.append(in_table[subrows[n+1]][0])
        else:
            if time_convert(in_table[subrows[n+1]-1][0])>time_convert(temp[3]):
                temp.append("00:00")
            else:
                temp.append(in_table[subrows[n+1]-1][0])
        
        temp.append(time_convert(temp[3]) - time_convert(temp[4])) #total time
        temp.append(in_table[subrows[n]][1]) #score start
        
        #score end
        if n == len(subrows[:-1])-1:
            temp.append(in_table[subrows[n+1]][1])
        else:
            temp.append(in_table[subrows[n+1]-1][1])
        
        temp.append((plus_minus(temp[7])-plus_minus(temp[6]))) #+/-
        
        #PUT SUB DATA INPUT ERROR ALGORITHM HERE
        if len(in_table[subrows[n]][4]) != 5:
            #print "\n", in_table[subrows[n]][1], in_table[subrows[n]][4]
            in_table = minimize_input_errors(in_table, subrows, n, arg)
            
        #team lineup: 1 cell per player
        for i in range(5):
            if len(in_table[subrows[n]][4]) == 5:
                temp.append(in_table[subrows[n]][4][i])
            else:
                if i < len(in_table[subrows[n]][4]):
                    temp.append(in_table[subrows[n]][4][i])
                else:
                    temp.append('')
        #temp.append(in_table[subrows[n]][4]) #team lineup
        #temp.append(in_table[subrows[n]][5]) #opponent lineup
        
        row_subset = in_table[subrows[n] : subrows[n+1]]
        if arg == 0:
            team_stats_holder = stats_sidearm(row_subset, 2)
            opp_stats = stats_sidearm(row_subset, 3)
        elif arg == 1:
            team_stats_holder = stats_presto(row_subset, 2)
            opp_stats = stats_presto(row_subset, 3)
        elif arg == 2:
            team_stats_holder = stats_cbsi(row_subset, 2)
            opp_stats = stats_cbsi(row_subset, 3)
        for m, s in enumerate(team_stats_holder):
            temp.append((team_stats_holder[m]))
        for a, b in enumerate(opp_stats):
            temp.append((opp_stats[a]))
                    
        table.append(temp)
            
    #CREATE DATAFRAME FOR GAME
    cols = ["DATE","TEAM","OPPONENT","TIME IN","TIME OUT","TOTAL TIME",\
            "SCORE IN","SCORE OUT","+/-","TEAM A","TEAM B","TEAM C",\
            "TEAM D","TEAM E",\
            #"OPPONENT LINEUP",\
            "POSS.","FGM","FGA","2ptFGM","2ptFGA","3ptFGM","3ptFGA","FTM",\
            "FTA","AST","TO","OREB","DREB","STL","BLK","FOULS","Opp POSS.",\
            "Opp FGM","Opp FGA","Opp 2ptFGM","Opp 2ptFGA","Opp 3ptFGM",\
            "Opp 3ptFGA","Opp FTM","Opp FTA","Opp AST","Opp TO","Opp OREB",\
            "Opp DREB","Opp STL","Opp BLK","Opp FOULS"]
    
    df = pd.DataFrame(table, columns=cols)
    #del df["OPPONENT LINEUP"] #just for now?
    
    with open(filename+'_all_lineups.csv', 'a') as f:
        df.to_csv(f, header=False)
        
    print(df.head())
    #print df[:5].to_string()

            

'''
Given a set of rows (representing all the play data for a given rotation),
calculate all the box score data. Helper function used in lineup_table()

Args:
rows - subset of rows of in_table
col - column to read data from. will be 2 for team data, 3 for opponent data

Returns:
stats - list of all stats in the following format
        [POSSESSIONS, 2ptFGM, 2ptFGA, 3ptFGM, 3ptFGA, FTA, FTM, AST, TO,
        OREB, DREB, STL, BLK, FOULS]
        
ALSO POSSIBLE TO CALCULATE:
POINTS IN THE PAINT
FAST BREAK POINTS
POINTS
FGM/FGA

ASSUMPTIONS:
only shot types are JUMPER, LAYUP, 3PTR, FT, TIPIN, DUNK
'''
def stats_sidearm(rows, col):
    #print "stats sidearm"
    fgm_2 = 0; fga_2 = 0; fgm_3 = 0; fga_3 = 0; fta = 0; ftm = 0; ast = 0
    to = 0; dreb = 0; oreb = 0; stl = 0; blk = 0; foul = 0
    
    for row in rows:
        if 'ASSIST' in row[col]:
            ast += 1
        elif 'REBOUND DEF' in row[col]:# or 'REBOUND DEADB' in row[col]:
            dreb += 1
        elif 'REBOUND OFF' in row[col]:
            oreb += 1
        elif 'TURNOVER' in row[col]:
            to += 1
        elif 'GOOD JUMPER' in row[col] or 'GOOD LAYUP' in row[col] \
             or 'GOOD TIPIN' in row[col] or 'GOOD DUNK' in row[col]:
            fgm_2 += 1
            fga_2 += 1
        elif 'MISS JUMPER' in row[col] or 'MISS LAYUP' in row[col] \
             or 'MISS TIPIN' in row[col] or 'MISS DUNK' in row[col]:
            fga_2 = fga_2 + 1
        elif 'GOOD 3PTR' in row[col]:
            fgm_3 += 1
            fga_3 += 1
        elif 'MISS 3PTR' in row[col]:
            fga_3 += 1
        elif 'GOOD FT' in row[col]:
            ftm += 1
            fta += 1
        elif 'MISS FT' in row[col]:
            fta += 1
        elif 'STEAL' in row[col]:
            stl += 1
        elif 'BLOCK' in row[col]:
            blk += 1
        elif 'FOUL' in row[col]:
            foul += 1
    
    fga = fga_2 + fga_3
    fgm = fgm_2 + fgm_3
    poss = fga + (fta * POSS_RATIO) + to - oreb

    return [poss, fgm, fga, fgm_2, fga_2, fgm_3, fga_3, ftm, fta, ast, to, \
            oreb, dreb, stl, blk, foul]


'''
Same as stats_sidearm except this one works on PrestoSports provided pbps

ASSUMPTIONS:
only shot types are 3-PT. JUMP SHOT, JUMP SHOT, LAYUP, 3PTR, FREE THROW,
DUNK
'''
def stats_cbsi(rows, col):
    #print "stats cbsi"
    fgm_2 = 0; fga_2 = 0; fgm_3 = 0; fga_3 = 0; fta = 0; ftm = 0; ast = 0
    to = 0; dreb = 0; oreb = 0; stl = 0; blk = 0; foul = 0
    
    for row in rows:
        if 'ASSIST' in row[col]:
            ast += 1
        #reb by deadball doesn't count
        elif 'REBOUND (DEF)' in row[col] and "(DEADBALL)" not in row[col]:
            dreb += 1
        elif 'REBOUND (OFF)' in row[col] and "(DEADBALL)" not in row[col]:
            oreb += 1
        elif 'TURNOVR' in row[col]:
            to += 1
        elif 'GOOD! JUMPER' in row[col] or 'GOOD! LAYUP' in row[col] \
             or 'GOOD! TIP-IN' in row[col] or 'GOOD! DUNK' in row[col]:
            fgm_2 += 1
            fga_2 += 1
        elif 'MISSED JUMPER' in row[col] or 'MISSED LAYUP' in row[col] \
             or 'MISSED DUNK' in row[col] or 'MISSED DUNK' in row[col]:
            fga_2 = fga_2 + 1
        elif 'GOOD! 3 PTR' in row[col]:
            fgm_3 += 1
            fga_3 += 1
        elif 'MISSED 3 PTR' in row[col]:
            fga_3 += 1
        elif 'GOOD! FT SHOT' in row[col]:
            ftm += 1
            fta += 1
        elif 'MISSED FT SHOT' in row[col]:
            fta += 1
        elif 'STEAL' in row[col]:
            stl += 1
        elif 'BLOCK' in row[col]:
            blk += 1
        elif 'FOUL' in row[col]:
            foul += 1
    
    fga = fga_2 + fga_3
    fgm = fgm_2 + fgm_3
    poss = fga + (fta * POSS_RATIO) + to - oreb

    return [poss, fgm, fga, fgm_2, fga_2, fgm_3, fga_3, ftm, fta, ast, to, \
            oreb, dreb, stl, blk, foul]


'''
Same as stats_sidearm except this one works on PrestoSports provided pbps

ASSUMPTIONS:
only shot types are 3-PT. JUMP SHOT, JUMP SHOT, LAYUP, 3PTR, FREE THROW,
DUNK
'''
def stats_presto(rows, col):
    #print "stats presto"
    fgm_2 = 0; fga_2 = 0; fgm_3 = 0; fga_3 = 0; fta = 0; ftm = 0; ast = 0
    to = 0; dreb = 0; oreb = 0; stl = 0; blk = 0; foul = 0
    
    for row in rows:
        if 'ASSIST' in row[col]:
            ast += 1
        elif 'DEFENSIVE REBOUND' in row[col]:# or 'REBOUND DEADB' in row[col]:
            dreb += 1
        elif 'OFFENSIVE REBOUND' in row[col]:
            oreb += 1
        elif 'TURNOVER' in row[col]:
            to += 1
        elif 'MADE JUMP SHOT' in row[col] or 'MADE LAYUP' in row[col] \
             or 'MADE DUNK' in row[col]:
            fgm_2 += 1
            fga_2 += 1
        elif 'MISSED JUMP SHOT' in row[col] or 'MISSED LAYUP' in row[col] \
             or 'MISSED DUNK' in row[col]:
            fga_2 = fga_2 + 1
        elif 'MADE 3-PT. JUMP SHOT' in row[col]:
            fgm_3 += 1
            fga_3 += 1
        elif 'MISSED 3-PT. JUMP SHOT' in row[col]:
            fga_3 += 1
        elif 'MADE FREE THROW' in row[col]:
            ftm += 1
            fta += 1
        elif 'MISSED FREE THROW' in row[col]:
            fta += 1
        elif 'STEAL' in row[col]:
            stl += 1
        elif 'BLOCK' in row[col]:
            blk += 1
        elif 'FOUL' in row[col]:
            foul += 1
    
    fga = fga_2 + fga_3
    fgm = fgm_2 + fgm_3
    poss = fga + (fta * POSS_RATIO) + to - oreb

    return [poss, fgm, fga, fgm_2, fga_2, fgm_3, fga_3, ftm, fta, ast, to, \
            oreb, dreb, stl, blk, foul]


'''
Takes two times in string format and calculates the game time difference 
between them. The second arg will be subtracted from the first. Used in
lineup_table.

ex: difference("20:00", "16:28") returns "3:32"

code borrowed from user Brandon Rhodes and Paolo Bergantino on stack overflow
'''
def difference(start, end):
    x = time_convert(start)
    y = time_convert(end)
    mins, secs = divmod(x-y, 60)
    return "%02d:%02d" % (mins, secs)


'''
Takes game time as a string and returns number of seconds. Used in difference.

Code borrowed from user thafritz on stack overflow
'''
def time_convert(timestr):
    ftr = [60, 1]
    return sum([a*b for a,b in zip(ftr, map(int,timestr.split(':')))])


'''
Calculate difference in score. Input of "26-23" returns "3". Input of "13-19"
returns -6. The +/- is always calculated in terms of the first score listed.

Return: +/- in integer form
'''
def plus_minus(score):
    lst = score.split('-')
    return int(lst[0]) - int(lst[1])


'''
'''
def get_date(soup):
    holder = soup.find("div", {"class":"large-4 columns game-details-container"})
    return holder.find('dd').text


'''
DEAR GOD I've been dreading writing this function for a while... basically
the play data is input by some human running some software, and that person
messes up sometimes.  They record a player (or playerS) subbing in without a
different player subbing off so now we have too many players on the court, or
vice versa.  Sometimes, we can sleuth around the play data to pick out the
missing or extra players.  

If the number of players on the court < 5:
Look in the lineup's (small) window for a player mentioned in a play detail
that isn't one of the players we have on the court.

If the number of players on the court > 5:
This is even worse.  Hope that all 5 players who are actually on the court
are mentioned doing something cause that's the only way to know who's actually
there

For the flawed lineups that we can't fix, just throw away the data as suggested

ARGS:
in_table
subrows - locations of rows of in_table where substitutions occur
index - current index of subrows in the iteration at the time of call
arg

Returns:
new_in_table - only if changes are made to the original 
'''
def minimize_input_errors(in_table, subrows, index, arg):
    if index == len(subrows)-1: return in_table #dont get last index of subrow
    
    #IF WE NEED TO FIND A 'MISSING' PLAYER:
    if len(in_table[subrows[index]][4]) < 5:
        to_add = []
    
        for n, row in enumerate(in_table[ subrows[index] : subrows[index+1] ]):
            if arg == 0: #SidearmSports
                if "BY" in row[2] and "SUB " not in row[2]:
                    name = row[2][row[2].find(' BY ')+4:].\
                        replace("(FASTBREAK)","").replace("(IN THE PAINT)", "")
                    name = nice_name(name)
                    
                    if name not in row[4]:
                        if name not in to_add and name != "TEAM":
                            to_add.append(name)
                            
            elif arg == 1: #PrestoSports
                replace = ["FOUL", "ENTERS THE GAME", "GOES TO THE BENCH", \
                           "TURNOVER", "MISSED", "3-PT.", \
                           "DEFENSIVE", "REBOUND", "OFFENSIVE", "DEADBALL", \
                           "MADE", "ASSIST", "LAYUP", "STEAL", "BLOCK", \
                           "THROW", "START OF PERIOD", "END OF PERIOD", "DUNK",\
                           "TIP-IN",
                           "TECHNICAL", "BY", "FREE", "JUMP", "SHOT"]
                
                name = row[2]
                
                for word in replace:
                    name = name.replace(word, "")
                name = nice_name(name)
                
                if name not in row[4] and "TEAM" not in name and name != "" \
                                      and "ENTERS THE GAME" not in row[2]\
                                      and "GOES TO THE BENCH" not in row[2]:
                    if name not in to_add:
                        to_add.append(name)
                    
            elif arg == 2: #CBSi
                if " BY " in row[2]:
                    name = row[2][row[2].find(' BY ')+4:].\
                        replace('[FB/PNT]', '').replace('[PNT]', '').\
                        replace('[FB]', '').replace('THE BENCH', '')
                    name = remove_foul_details(name)
                    name = nice_name(name)
                    
                    if name not in row[4] and "(DEADBALL)" not in name \
                                          and "(TEAM)" not in name:
                        if name not in to_add:
                            to_add.append(name)
                
        
        if len(to_add) > 0:
            new_table = copy.deepcopy(in_table)
            for name in to_add:
                for n, row in enumerate(new_table[subrows[index]: \
                                                 subrows[index+1]]):
                    row[4].append(name)
                    row[4] = sorted(row[4])
            
            #print "Reduced sub data input errors! Added:", to_add
            return new_table
        #else:
            #print "found nothing new "
    
    #IF WE NEED TO REMOVE THE EXTRA PLAYERS
    elif len(in_table[subrows[index]][4]) > 5:
        true_court = []
        
        for n, row in enumerate(in_table[ subrows[index] : subrows[index+1] ]):
            if arg == 0: #SidearmSports
                if "BY" in row[2]:
                    name = row[2][row[2].find(' BY ')+4:].\
                        replace("(FASTBREAK)","").replace("(IN THE PAINT)", "")
                    name = nice_name(name)
                    
                    if name != "TEAM" and "SUB " not in row[2]:
                        if name not in true_court:
                            true_court.append(name)
                            
            elif arg == 1: #PrestoSports
                replace = ["FOUL", "ENTERS THE GAME", "GOES TO THE BENCH", \
                           "TURNOVER", "MISSED", "3-PT.", \
                           "DEFENSIVE", "REBOUND", "OFFENSIVE", "DEADBALL", \
                           "MADE", "ASSIST", "LAYUP", "STEAL", "BLOCK", \
                           "THROW", "START OF PERIOD", "END OF PERIOD", "DUNK",\
                           "TIP-IN",
                           "TECHNICAL", "BY", "FREE", "JUMP", "SHOT"]
                
                name = row[2]
                
                for word in replace:
                    name = name.replace(word, "")
                name = nice_name(name) 
                
                if name not in true_court and "TEAM" not in name and name != "" \
                                      and "ENTERS THE GAME" not in row[2]\
                                      and "GOES TO THE BENCH" not in row[2]:
                    true_court.append(name)
                        
            elif arg == 2: #CBSi
                if " BY " in row[2]:
                    name = row[2][row[2].find(' BY ')+4:].\
                        replace('[FB/PNT]', '').replace('[PNT]', '').\
                        replace('[FB]', '').replace('SUB IN : ', '').\
                        replace('THE BENCH', '')
                    name = remove_foul_details(name)
                    name = nice_name(name)
                    #name = name.replace(' ', '')
                    
                    if name not in true_court and "(DEADBALL)" not in name \
                                              and "(TEAM)" not in name:
                        true_court.append(name)
                        
        #if players in true_court exceeds 5, then the pbp data is so screwed up
        #.. that we still don't know who's on the court so reset to empty
        if len(true_court) > 5:
            true_court = []
        
        #whatever true_court may be, replace the current, flawed lineup
        #because at least we know the players we have were actually on the
        #court and we can still evaluate 4, 3, or even 2-man efficiencies    
        new_table = copy.deepcopy(in_table)
        if not true_court:
            z = subrows[index]
            x = new_table[subrows[index]][4]
            y = new_table[subrows[index]]
            for n, row in enumerate(new_table[subrows[index]: \
                                             subrows[index+1]]):
                row[4] = sorted(true_court)
        else:
            for lineup in true_court:
                for n, row in enumerate(new_table[subrows[index]: \
                                                 subrows[index+1]]):
                    row[4] = sorted(true_court)

        #print "Reduced sub data input errors. New:", true_court
        return new_table
    
    return in_table
    
    
'''
Looks at quarter scoring table in box score to see the game was played in 
2 twenty-minute halves or 4 ten-minute quarters.

Returns:
'M' - for men
'W' - for women / 2018 NIT games
'''
def menwomen(soup):
    table = soup.find("figure", {"class":"box-score-header"})
    periods = table.find_all("th", {"scope":"col"})
    
    if len(periods) >= 5 and periods[4].text == '4':
        return 'W'
    else:
        return 'M'


'''
Driver that runs get_teamnames, gets user input if the team names don't match
the given hostname, and finds homeaway and team names (in correct order)

Args:
soup
hostname

Returns:
(homeaway, teamnames)
'''
def run_teamnames(soup, hostname):
    teamnames = get_team_names(soup)
    awayteam = teamnames[0].upper()
    hometeam = teamnames[1].upper()
    
    homeaway = ""
    if awayteam == hostname:
        homeaway = "AWAY"
        teamnames = (awayteam, hometeam)
    elif hometeam == hostname:
        homeaway = "HOME"
        teamnames = (hometeam, awayteam)
    else:
        #handle msu vs michigan game hostname: michigan state
        if hostname == awayteam.replace(' STATE', '').replace(' ST', '') or \
           hostname == hometeam.replace(' STATE', '').replace(' ST', '') or \
           hostname == hometeam + " STATE" or \
           hostname == awayteam + " STATE" or \
           hostname == hometeam + " ST" or \
           hostname == awayteam + " ST":
            pass
        else:
            print("running similar()...")
            print(awayteam, hometeam)
            home_similar = le2.similar(hostname, hometeam)
            away_similar = le2.similar(hostname, awayteam)
    
            if home_similar > away_similar and home_similar > 0.7:
                print("similarity:", home_similar)
                homeaway = "HOME"
                teamnames = (hostname, awayteam)
                return homeaway, teamnames
            elif away_similar > home_similar and away_similar > 0.7:
                print("similarity:", away_similar)
                homeaway = "AWAY"
                teamnames = (hostname, hometeam)
                return homeaway, teamnames

        print ("\n\nThe boxscore page is using a different name than"
               " the given hostname. Do either of these options look like "
               "they could be for the host team?")
        print("\nTeam A:", awayteam, "\nTeam B:", hometeam)
        selection = raw_input("\n'A' or 'B' or 'neither': ").upper()
        if selection == 'A':
            homeaway = "AWAY"
            teamnames = (hostname, hometeam)
        elif selection == 'B':
            homeaway = "HOME"
            teamnames = (hostname, awayteam)
        else:
            raise UserWarning("\n\nERROR MESSAGE: Something went wrong "\
                              "determining", "home/away teams.\nCheck if "\
                              "hostname argument was " \
                              "entered correctly\nExiting...\n\n")
    
    return homeaway, teamnames


'''
Given the link to a team's schedule, this function grabs and creates tables
for all the data for every game and writes each to its own file(s)

Args:
schedule_url - link to team's schedule page
               ex: https://mgoblue.com/schedule.aspx?schedule=456
'''
def scrape_all(soup, schedule_url, hostname):
    links = get_boxscores(soup, schedule_url, hostname)
    #links = ['http://www.pepperdinewaves.com/sports/m-baskbl/stats/2017-2018/pepmbb01.html'] #111
    if links == None:
        print("All available data has been scraped alraedy, according to", \
              "TEAMNAME_DONE.txt")
    
    for l in links:        
        print("\nWORKING ON:", l)
        
        soup = get_site(l)    
        
        homeaway, teamnames = run_teamnames(soup, hostname)
        
        mw = menwomen(soup)
        
        print(hostname, teamnames, homeaway, mw)
        
        filename = hostname.replace(' ', '').lower()
        arg = 0
        
        starters = get_starters(soup, homeaway)
        if not starters:
            print("skipping exhibition game")
        else:
            pbp = get_pbp(soup, homeaway, mw)
            play_table = copy_table(pbp, starters, arg)
            lineup_table(play_table, teamnames, filename, get_date(soup), arg)
        
        #ADD GAME URL TO READ_ALREADY FILE
        with open(hostname.replace(' ', '').lower()+"DONE.txt",'a') as file:
            file.write("\n" + l)

        print("\n")
    
    dataframe(hostname) #111
    

'''
Looks in the cwd for existing lineup files for each game (by looking for csv)
files with teamname in them) and creates a dataframe in the lineup tool's
'final form' and exports it as a csv

Args:
hostname
'''
def dataframe(hostname):
    filename_base = hostname.lower().replace(' ', '')
    filename_lineups = filename_base + '_all_lineups.csv'
    
    cols = ["index","DATE","TEAM","OPPONENT","TIME IN","TIME OUT","TOTAL TIME",\
            "SCORE IN","SCORE OUT","+/-","TEAM A","TEAM B","TEAM C",\
            "TEAM D","TEAM E",\
            "POSS.","FGM","FGA","2ptFGM","2ptFGA","3ptFGM","3ptFGA","FTM",\
            "FTA","AST","TO","OREB","DREB","STL","BLK","FOULS","Opp POSS.",\
            "Opp FGM","Opp FGA","Opp 2ptFGM","Opp 2ptFGA","Opp 3ptFGM",\
            "Opp 3ptFGA","Opp FTM","Opp FTA","Opp AST","Opp TO","Opp OREB",\
            "Opp DREB","Opp STL","Opp BLK","Opp FOULS"]
    try:
        df = pd.read_csv(filename_lineups, names=cols)
    except IOError as e:
        #print "\n\nIOError: HOSTNAME_all_lineups.csv not found. Exiting:\n",\
              #hostname,"\n\n"
        #raise UserWarning("Error: HOSTNAME_all_lineups.csv not found.")
        print("Error: HOSTNAME_all_lineups.csv not found.")
        return
    
    df = df.fillna('MISSING')
    
    df = df.groupby(['TEAM','TEAM A','TEAM B','TEAM C','TEAM D','TEAM E'], \
                    as_index=False)[['TOTAL TIME','+/-',"POSS.","FGM","FGA",\
                     "2ptFGM","2ptFGA","3ptFGM","3ptFGA","FTM",\
                     "FTA","AST","TO","OREB","DREB","STL","BLK","FOULS",\
                     "Opp POSS.","Opp FGM","Opp FGA","Opp 2ptFGM","Opp 2ptFGA",\
                     "Opp 3ptFGM","Opp 3ptFGA","Opp FTM","Opp FTA","Opp AST",\
                     "Opp TO","Opp OREB","Opp DREB","Opp STL","Opp BLK",\
                     "Opp FOULS"]].sum()
    df = df.sort_values("TOTAL TIME", ascending=False)
    #df['TOTAL TIME'] = df['TOTAL TIME'].apply(to_clock)
    df = df.reset_index(drop=True)

    print("\n\nMASTER CONSOLIDATED DF:")
    print(df.head())
    
    #get 1/2/3/4-player lineups 
    for n in range(1, 5):
        dfn = n_player_lineups(df, n)
        filename_n = filename_base.upper() + '%s.csv' % (str(n))
        dfn.to_csv(filename_n)
    
    
    #5-PLAYER LINEUPS
    print("\ngetting 5 player lineup...")
    df5 = df.copy()
    #filter out lineups that were on court for less than 1% of possessions
    threshold = df5['TOTAL TIME'].sum() * ONE_PCT
    #print 'poss. threshold:', to_clock(threshold)
    df5 = df5[df5['TOTAL TIME'] > threshold]
    #run stats and ranks helpers
    df5 = df_stats(df5, 5)
    df5 = df_ranks(df5, 5)
    df5 = df5.reset_index(drop=True).round(4)
    df5['TOTAL TIME'] = df5['TOTAL TIME'].apply(to_clock)
    
    #print "\n\n5 PLAYER LINEUP"
    #print df5.to_string()
    
    filename_5 = filename_base.upper() + '5.csv'
    df5.to_csv(filename_5)
    

'''
Updates dataframe returned by dataframe() and adds stats

Offensive efficiency (OE), EFG%, TO%, OREB%, FTRATE, 3PTARATE, total effic.
...And the same stats for defense

Args:
df
nplayers - int - calculate stats for 5/4/3/2-player lineups (ex: 4)
'''
def df_stats(df, nplayers):
    #create columns to hold values for all the stats
    df['OE'] = np.nan; df['eFG%'] = np.nan
    df['TOrate'] = np.nan; df['OREB%'] = np.nan; df['FTrate'] = np.nan
    df['3PTrate'] = np.nan; df['NET'] = np.nan
    df['PACE'] = np.nan
    
    df['DE'] = np.nan; df['Opp eFG%'] = np.nan
    df['Opp TOrate'] = np.nan; df['Opp OREB%'] = np.nan
    df['Opp FTrate'] = np.nan; df['Opp 3PTrate'] = np.nan
    
    for i in df.index:
        threept_fgm = df.at[i,'3ptFGM']; fgm = float(df.at[i,'FGM'])
        fga = df.at[i,'FGA']; poss = df.at[i, 'POSS.']
        points = float(df.at[i,'2ptFGM']*2 + threept_fgm*3 + df.at[i,'FTM'])
        oreb = df.at[i,'OREB']; opp_dreb = df.at[i,'Opp DREB']
        
        opp_threept_fgm = df.at[i,'Opp 3ptFGM']; dreb = df.at[i,'DREB']
        opp_points = float(df.at[i,'Opp 2ptFGM']*2 + opp_threept_fgm*3 + \
                           df.at[i,'Opp FTM'])
        opp_fgm = float(df.at[i,'Opp FGM']); opp_fga = df.at[i,'Opp FGA']
        opp_poss = df.at[i, 'Opp POSS.']; opp_oreb = df.at[i,'Opp OREB']
        
        #offensive efficiency, turnover rate, plus/minus over possession
        if poss == 0:
            df.at[i, 'OE'] = 0.0
            df.at[i,'TOrate'] = 0.0
        else:
            df.at[i, 'OE'] = (points/poss)
            df.at[i,'TOrate'] = (float(df.at[i,'TO']) / poss)
    
        #effective field goal percentage, free throw rate, three point rate, fg%
        #FTrate = fta / fga ??? what if fta is nonzero but fga is?
        if fga == 0:
            df.at[i,'eFG%'] = 0.0
            df.at[i,'FTrate'] = 0.0
            df.at[i,'3PTrate'] = 0.0
        else:
            df.at[i,'eFG%'] = (fgm + (0.5*threept_fgm)) / float(fga)
            df.at[i,'FTrate'] = float(df.at[i,'FTA']) / float(fga)
            df.at[i,'3PTrate'] = float(df.at[i,'3ptFGA']) / float(fga)
        
        #offensive rebounding percentage
        #oreb / (oreb + opp-dreb) ?
        if oreb+opp_dreb == 0:
            df.at[i,'OREB%'] = 0.0
        else:
            df.at[i,'OREB%'] = float(oreb) / float(oreb+opp_dreb)
        
        #defensive efficiency and opponent turnover rate
        if opp_poss == 0:
            df.at[i, 'DE'] = 0.0
            df.at[i,'Opp TOrate'] = 0.0
        else:
            df.at[i, 'DE'] = (opp_points/opp_poss)
            df.at[i,'Opp TOrate'] = (float(df.at[i,'Opp TO']) / opp_poss)
            
        #opponent effective field goal percentage, opponent free throw rate,
        #...opponent three point rate, opponent field goal percentage
        if opp_fga == 0:
            df.at[i,'Opp eFG%'] = 0.0
            df.at[i,'Opp FTrate'] = 0.0
            df.at[i,'Opp 3PTrate'] = 0.0
        else:
            df.at[i,'Opp eFG%'] = (opp_fgm + (0.5*opp_threept_fgm)) / \
                                   float(opp_fga)
            df.at[i,'Opp FTrate'] = float(df.at[i,'Opp FTA']) / float(opp_fga)
            df.at[i,'Opp 3PTrate'] = float(df.at[i,'Opp 3ptFGA']) / \
                                           float(opp_fga)
            
        #opponent offensive rebounding percentage
        #oreb / (oreb + opp-dreb) ?
        if dreb+opp_oreb == 0:
            df.at[i,'Opp OREB%'] = 0.0
        else:
            df.at[i,'Opp OREB%'] = float(opp_oreb) / float(opp_oreb+dreb)
            
        #total efficiency
        df.at[i,'NET'] = df.at[i,'OE'] - df.at[i,'DE']
        
        #pace 
        df.at[i,'PACE'] = GAME_MINUTES * ((df.at[i,'POSS.'] + \
                        df.at[i,'Opp POSS.']) / (2*(df.at[i,'TOTAL TIME']/60)))
        
    cols_base = ['TOTAL TIME', 'POSS.', 'PACE', 'NET', 'OE', 'eFG%', \
                '3PTrate', 'TOrate', 'OREB%', 'FTrate', 'DE', 'Opp eFG%', \
                'Opp 3PTrate', 'Opp TOrate', 'Opp OREB%', 'Opp FTrate']
    player_cols = ['TEAM A', 'TEAM B', 'TEAM C', 'TEAM D', 'TEAM E']
    team_col = ['TEAM']
    
    new_cols = team_col + player_cols[:nplayers] + cols_base

    df_stats = df[new_cols]
    return df_stats



'''
Helper in dataframe.  Adds rank columns for each of the stats calcualated in
df_stats

Args:
df
nplayers - int - calculate stats for 5/4/3/2-player lineups (ex: 4)
'''
def df_ranks(df, nplayers):
    pct = pd.read_csv('percentiles.csv')
    
    df = pct_desc(df, pct, 'PACE')
    df = pct_desc(df, pct, 'NET')
    df = pct_desc(df, pct, 'OE')
    df = pct_desc(df, pct, 'eFG%')
    df = pct_desc(df, pct, '3PTrate')
    df = pct_desc(df, pct, 'OREB%')
    df = pct_desc(df, pct, 'FTrate')
    df = pct_desc(df, pct, 'Opp TOrate')
    df = pct_asce(df, pct, 'DE')
    df = pct_asce(df, pct, 'TOrate')
    df = pct_asce(df, pct, 'Opp 3PTrate')
    df = pct_asce(df, pct, 'Opp eFG%')
    df = pct_asce(df, pct, 'Opp FTrate')
    df = pct_asce(df, pct, 'Opp OREB%')
                    
    cols_base = ['TOTAL TIME', 'POSS.', 'PACE', 'PACE PCTL', 'NET', \
                 'NET PCTL', 'OE', 'OE PCTL', 'DE', 'DE PCTL', \
                 'eFG%', 'eFG% PCTL', '3PTrate', '3PTrate PCTL', 'TOrate', \
                 'TOrate PCTL', 'OREB%', 'OREB% PCTL', 'FTrate', \
                 'FTrate PCTL', 'Opp eFG%', 'Opp eFG% PCTL', \
                 'Opp 3PTrate', 'Opp 3PTrate PCTL', 'Opp TOrate', \
                 'Opp TOrate PCTL', 'Opp OREB%', 'Opp OREB% PCTL', \
                 'Opp FTrate', 'Opp FTrate PCTL']
    player_cols = ['TEAM A', 'TEAM B', 'TEAM C', 'TEAM D', 'TEAM E']
    team_col = ['TEAM']
    
    new_cols = team_col + player_cols[:nplayers] + cols_base
    
    df_new = df[new_cols]    
    
    return df_new



'''
Helper for df_ranks to use percentiles df and calculate the percentile
relative to the nation for every lineup of one column of a dataframe

It's split up into pct_desc and pct_asce because sometimes its better to have
a high number (pct_desc) and sometimes its better to have a low number 
(pct_asce)

Args:
df
pct_df - from percentiles.csv
col_name - name of column of df to read analyze. ex: "PACE"
'''
def pct_desc(df, pct_df, col_name):
    col_pct_name = col_name + " PCTL"
    for i in df.index:
        #for every lineup...
        for index, row in enumerate(pct_df[col_name]):
            on_chart = False #zeroth percentile
            if df.at[i,col_name] >= row:
                df.at[i,col_pct_name] = pct_df.at[index,'Percentile']
                on_chart = True
                break
            if not on_chart: df.at[i,col_pct_name] = 0.01
    return df



'''
Same as the docs for pct_desc
'''
def pct_asce(df, pct_df, col_name):
    col_pct_name = col_name + " PCTL"
    for i in df.index:
        #for every lineup...
        for index, row in enumerate(pct_df[col_name]):
            on_chart = False #zeroth percentile
            if df.at[i,col_name] <= row:
                df.at[i,col_pct_name] = pct_df.at[index,'Percentile']
                on_chart = True
                break
            if not on_chart: df.at[i,col_pct_name] = 0.01
    return df
            


'''
Helper for dataframe().  Takes amount of seconds as an integer and converts
it to XX:XX clock form.

Ex: 431 becomes "07:11"
'''
def to_clock(seconds):
    seconds = int(seconds)
    mins, secs = divmod(seconds, 60)
    return "%02d:%02d" % (mins, secs)



'''
Creates, and returns dataframe of 1/2/3/4-player lineups.  Helper called in
dataframe.

Args:
df - the full dataframe; 5-player version
n - number of players in lineup as integer (ex: 3) 
'''
def n_player_lineups(df, n):
    print("\ngetting", n, "player lineup...")
    #creaete df with appropriate columns for given argument n
    headers_base = ['TOTAL TIME',\
               '+/-',"POSS.","FGM","FGA","2ptFGM","2ptFGA","3ptFGM","3ptFGA",\
               "FTM","FTA","AST","TO","OREB","DREB","STL","BLK","FOULS",\
               "Opp POSS.","Opp FGM","Opp FGA","Opp 2ptFGM","Opp 2ptFGA",\
               "Opp 3ptFGM","Opp 3ptFGA","Opp FTM","Opp FTA","Opp AST",\
               "Opp TO","Opp OREB","Opp DREB","Opp STL","Opp BLK","Opp FOULS"]
    player_headers = ['TEAM A','TEAM B','TEAM C','TEAM D','TEAM E']
    headers = ['TEAM'] + player_headers[:n] + headers_base
    
    #dfn = dataframe with n-player columns
    dfn = pd.DataFrame(columns=headers)
    for i in df.index:
        court = []
        court.append(df.at[i,'TEAM A']); court.append(df.at[i,'TEAM B'])
        court.append(df.at[i,'TEAM C']); court.append(df.at[i,'TEAM D'])
        court.append(df.at[i,'TEAM E'])

        row = df.iloc[[i]]
        #remove appropriate player columns before adding to dfn
        for col in player_headers[n:]:
            row = row.drop([col], axis=1)

        #create a copy for each 3-man combination for each row
        #5C3 = 10 so this multiplies the length of the df by a factor of 10
        #^ not accounting for ignoring combinations with "MISSING" player data
        sets_n = list(itertools.combinations(court, n))
        for group in sets_n:
            if 'MISSING' not in group:
                row[player_headers[:n]] = group
                dfn = dfn.append(row)
                #print row.to_string()
                
    #run groupby to consolidate dfn... after converting col types to int
    dfn = df_toint(dfn)
    dfn = dfn.groupby(['TEAM']+player_headers[:n],as_index=False)[['TEAM',\
                                                           'TOTAL TIME','+/-',\
        "POSS.","FGM","FGA","2ptFGM","2ptFGA","3ptFGM","3ptFGA","FTM","FTA",\
        "AST","TO","OREB","DREB","STL","BLK","FOULS","Opp POSS.","Opp FGM",\
        "Opp FGA","Opp 2ptFGM","Opp 2ptFGA","Opp 3ptFGM","Opp 3ptFGA",\
        "Opp FTM","Opp FTA","Opp AST","Opp TO","Opp OREB","Opp DREB","Opp STL",\
        "Opp BLK","Opp FOULS"]].sum()
    
    dfn = dfn.sort_values("TOTAL TIME", ascending=False)
    if n != 1:
        threshold = dfn['TOTAL TIME'].sum() * ONE_PCT
        dfn = dfn[dfn['TOTAL TIME'] > threshold]
    else:
        #dfn = dfn[dfn['POSS.'] > 15.0] #111 so we can see more mistakes in testing
        pass
    dfn = df_stats(dfn, n)
    dfn = df_ranks(dfn, n)
    dfn = dfn.reset_index(drop=True).round(4)
    dfn['TOTAL TIME'] = dfn['TOTAL TIME'].apply(to_clock)
    
    #print dfn.to_string() 
    return dfn



'''
Pandas reads integer data as strings, which makes it impossible to sum them.
So we convert the values of all the columns that should be integers to integers
and return that df.
'''
def df_toint(dfn):
    dfn[['TOTAL TIME','+/-',"FGM","FGA","2ptFGM","2ptFGA","3ptFGM","3ptFGA",\
         "FTM","FTA","AST","TO","OREB","DREB","STL","BLK","FOULS","Opp FGM",\
         "Opp FGA","Opp 2ptFGM","Opp 2ptFGA","Opp 3ptFGM","Opp 3ptFGA",\
         "Opp FTM","Opp FTA","Opp AST","Opp TO","Opp OREB","Opp DREB",\
         "Opp STL","Opp BLK","Opp FOULS"]] = dfn[['TOTAL TIME','+/-',"FGM",\
         "FGA","2ptFGM","2ptFGA","3ptFGM","3ptFGA","FTM","FTA","AST","TO",\
         "OREB","DREB","STL","BLK","FOULS","Opp FGM","Opp FGA","Opp 2ptFGM",\
         "Opp 2ptFGA","Opp 3ptFGM","Opp 3ptFGA","Opp FTM","Opp FTA","Opp AST",\
         "Opp TO","Opp OREB","Opp DREB","Opp STL","Opp BLK","Opp FOULS"]].\
         astype(int)
    return dfn



'''
Some schedule pages within the SidearmSports provider have different html 
formats.

Ex: Wisonsin, Chattenooga, Cornell, ?

This is a helper for scrape_all that scrapes the alternate format and returns
all the boxscore links on a team's schedule page

Args:
bigsoup
base - base of url to add boxscore extention to
read_already - list of urls read aleady
'''
def get_alt1_boxscores(bigsoup, base, read_already):
    print("get_alt1_boxscores")
      
    results_soup = bigsoup.find_all("div", {"class":"schedule_game_results"})

    #if results_soup is empty, then the website isn't in this format either
    if not results_soup:
        return get_alt2_boxscores(bigsoup, base, read_already)
    else:
        urls = []
        for row in results_soup:
            #handle exhibition games
            if "EXHIBITION" not in row.parent.parent.text.upper() and \
               "EXH" not in row.parent.parent.text.upper() and \
               "EXB" not in row.parent.parent.text.upper():
                if "BOX SCORE" in row.text.upper():
                    link = base + '/' + row.find('a').get('href')
                    if 'boxscore' in link and link not in read_already:
                        urls.append(link)
        return urls


'''
See documentation for get_alt2_boxscores.  It's the same except this one takes
the soup object instead of just the url.  This one works on Northwestern's
website.  This is a helper for get_alt1_boxscores

http://nusports.com/schedule.aspx?path=mbball
https://unipanthers.com/schedule.aspx?path=mbball

Returns:
urls - list of all urls to boxscores for each game on the team's schedule
'''
def get_alt2_boxscores(bigsoup, base, read_already):
    print("get_alt2_boxscores - trying with webdriver")
    
    results_soup = bigsoup.find_all("td", {"class":"schedule_dgrd_time/result"})
    urls = []
    for row in results_soup:
        #handle exhibition games
        if "EXHIBITION" not in row.parent.text.upper() and \
           "EXH" not in row.parent.text.upper() and \
           "EXB" not in row.parent.parent.text.upper():
            if "BOX SCORE" in row.text.upper():
                link = base + '/' + row.find_all('a')[1].get('href')
                if 'boxscore' in link and link not in read_already:
                    urls.append(link)
    return urls


'''
Scrape all boxscores given a team's schedule URL.  Helper for scrape_all.

Args:
bigsoup - soup object for schedule's url page
schedule_url - used for creating url base
read_already - list of urls on team's schedule that have already been read 
'''
def get_boxscores(bigsoup, schedule_url, hostname):
    #bigsoup = get_site(schedule_url)
    
    read_already = been_read(hostname)
    print("Games read already:", len(read_already))
    for r in read_already: print(r)
    
    base = schedule_url[: schedule_url.find("/sports") ]
    
    #get links to all games on schedule page
    #try 'normal' team schedule html layout first
    links = []
    links_soup = bigsoup.find_all("div", {"class": \
                    "sidearm-schedule-game-links hide-on-medium-only print-el"})
    
    #if 'normal' format doesn't work, try helpers to scrape alternate formats
    if not links_soup:
        links = get_alt1_boxscores(bigsoup, base, read_already)
    else:
        for l in links_soup:
            #handle exhibition games
            if "EXHIBITION" not in l.parent.parent.text.upper() and \
               "EXH" not in l.parent.parent.text.upper() and \
               "EXB" not in l.parent.parent.text.upper():
                if "BOX SCORE" in l.text.upper():
                    link_holder = l.find("a", {"target":"_blank"})
                    if not link_holder: continue
                    link = base + link_holder.get('href')
                    if 'boxscore' in link:
                        boxscore_links_exist = True
                        if link not in read_already:
                            links.append(link)
    
    print("Games found:", len(links))
    for l in links: print (l)
    return links


'''
Handle all different ways we encounter names

Return name in format: LASTNAME.FIRSTNAME
'''
def nice_name(name):
    name = name.rstrip().strip().upper()

    #strip of leading and trailing periods/commas
    trailing_period_removed = False
    if name and (name[0] == "." or name[0] == ","):
        name = name[1:]
    if name and name[len(name)-1] == ".":
        name = name[:len(name)-1]
        trailing_period_removed = True
            
    #get rid of "JR" and "II" and "III" and "IV"
    if "JR" in name:
        #handle JR,AVERY JOHNSON
        if name[:2] == "JR":
            name = name[3:]
        name = name.replace('JR,', '.').replace('JR..', '.').\
            replace('JR.', '.').replace("JR", '').rstrip().strip()
        if name[len(name)-1] == '.': #fix Ronnie Harrell Jr. --> RONNIEHARRELJR.
            name = name[:-1]
        if name[0] == '.' or name[0] == ',': #fix JR,ERIC DAVIS --> .ERICDAVIS
            name = name[1:]
    elif "III" in name:
        name = name.replace("III", "").rstrip().strip()
        #III,JAMES BANKS
        if name[0] == ',' or name[0] == '.':
            name = name[1:].strip()
    elif "II" in name:
        name = name.replace("II", "").rstrip().strip()
        #II,KERWIN ROACH
        if name[0] == ',' or name[0] == '.':
            name = name[1:].strip()
    
    #ABBREVIATIONS
    space = name.find(" ")
    if trailing_period_removed:
        check = 1
    else:
        check = 2
    #handle Burks, C.J. and Burks. C.J.
    if name.count('.') >= check and space != -1 and space < name.find('.', space+1):
        name = name[:space] + name[space+1:].replace('.', '')
    #handle J.C. Show
    elif name.count('.') >= check and space != -1 and space > name.find('.'):
        name = name.replace('.', '')
    #handle PAIGE,J.D.
    elif space == -1 and name.count('.') >= check:
        if ',' in name:
            name = name.replace('.', '').replace(',', '.')
    #handle DAVIS,D.C (trailing '.' not removed since it came from cbsi starters)
    elif ',' in name and name.count('.') == 1:
        name = name.replace('.', '').replace(',', '.')


    if '.' in name and ' ' not in name and ',' not in name and name.count('.') == 1:
        return name
    
    elif '.' in name and ' ' in name:
        name = name.replace(' ', '').replace(',', '').replace('..', '.')
    
    elif ',' in name:
        name = name.replace(",", ".").replace(" ", "")
    
    elif '(' in name or "TEAM" in name:
        return name
    
    #handle DAVIS.D.C
    elif name.count('.') > 1:
        loc = name.rfind('.')
        if loc < len(name)-1:
            name = name[:loc] + name[loc+1]
        
    else:
        space = name.rfind(" ")
        if space != -1:
            name = name[space:] + "." + name[:space]
            name = name.replace(" ", "").replace('.,', '..').replace('..', '.')
        
    #handle nicknames (Cheikh 'CB' Diallo)
    if name and (name[0] == "'" or name[0] == '"'):
        endquote = name.replace('"', "'").find("'", 1)
        name = name[endquote+1:] + name[:endquote+1]
        
    return name


'''
For CBSi style.  For fouls, they include personal and team foul data, which
interferes with the way we gather names.  This helper removes the foul data
and returns the updates string.  Used in find_super_missing_players

ex: FOUL by Jessup, Justinian (P1T7)
'''
def remove_foul_details(string):
    to_remove = "1234567890"
    for char in to_remove:
        string = string.replace(char, "")
    return string.replace("(PT)", "")


'''
Helper used in get_boxscores for comparing links scraped from site to links
saved in TEAMNAMEDONE.txt file.

Returns:
read_already - set with all links to not double-scrape
'''
def been_read(hostname):
    read_already = set()
    try:
        with open(hostname.replace(' ', '').lower()+"DONE.txt",'r') as file:
            read = file.read().splitlines()
    except:
        read = []
    for r in read:
        if r not in read_already:
            read_already.add(r)
    
    return read_already


'''
Used to handle team name inconsistency issues.
Ex: Wichita St. vs Wichita State
Called in run_teamnames
'''
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()



'''
Args:
soup - soup object to schedule page
sch_url
hostname
'''
def main(soup, sch_url, hostname):
    scrape_all(soup, sch_url, hostname)


'''#111
if __name__ == '__main__':
    print "*starting...*\n"
    
    start_time = time.time()
    
    main('soup_placeholder', 'xx', 'PEPPERDINE')

    print "\n*done* --- %s seconds ---" % (time.time() - start_time)
'''


'''
6/6
CONTINGENT ON:
aside from basic formatting stuff...
- sub out must be logged in the play data after sub in
- a player who starts a period that isn't the first half and player the whole
  period has to do SOMETHING and be mentioned in the play data in some way or
  they won't get recorded, as the algorithm is now. (i think)
- exhibition game's can't be identified if there is no mention that the game is
  an exhibition in the box score notes or on the game's row on the schedule 

IT'S BEEN HARD TO TEST ON MIDSEASON PAGES (NOT CRASHING WHEN ENCOUNTERING GAMES THAT HAVEN'T BEEN PLAYED)

USER QUIRKS:
-nameDONE.txt must have links to all games scraped already
-name_all_lineups.csv is where the tool gets all the lineup data to create
final product dataframes. so:
-name_all_lineups.csv is cleared for each new season 
-name_all_lineups.csv is not deleted midseason
-percentiles.csv is named precisely and is in directory
-percentiles.csv - all columns match the names of the output csv headers
 exactly, case, space, and all
-each game on sidearm schedule lists box score link before anything else
'''