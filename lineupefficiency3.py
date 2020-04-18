import requests #***
from bs4 import BeautifulSoup #***
import copy
import pandas as pd #for creating dataframe ***
import numpy as np
import itertools #for finding 4/3/2-player lineup combinations
import sys #for error handling

import time

import lineupefficiency2 as le2


'''
This program gathers all the lineup data for both teams in a game so we can
evaluate offensive and defensive efficiencies for each lineup.

This scraper works when team's athletics website is in PrestoSports html format
ex: http://www.ucsbgauchos.com/sports/m-baskbl/2017-18/schedule

Author: Matt Wang
'''

#GLOBALS
START_TIME_M = "20:00"
START_TIME_W = "10:00"
START_TIME_OT = "05:00"
POSS_RATIO = 0.44

'''
Takes one game's boxscore page and scrapes "raw" play by play table

Args:
soup - game boxscore page in BeautifulSoup form
homeaway - "HOME" or "AWAY"
mw - men or women? 'M' or 'W' (all caps)

Return: All the data needed as individual lists
(times, scores, team_details, opp_details)
'''
def get_pbp(soup, homeaway, mw):
    if mw == 'M':
        start_time = START_TIME_M
        OTcheck = 1
    elif mw == 'W':
        start_time = START_TIME_W
        OTcheck = 3
        
    table_soup = soup.find("div", {"class":"stats-box full"})
    
    times = []
    scores = []
    home_details = []
    away_details = []
    
    times.append(start_time)
    scores.append("0-0")
    home_details.append("START OF PERIOD")
    away_details.append("START OF PERIOD")
    
    
    #TIMES
    time_soup = soup.findAll("td", {"class":"time"})
    for t in time_soup:
        times.append(t.contents[0])
    
    #SCORES
    score_soup = table_soup.findAll("td", {"class":"score"})
    for s in score_soup:
        visitor = s.find("span", {"class":"v-score"})
        home = s.find("span", {"class":"h-score"})
        
        #handle empty score container
        score = "0-0"
        if visitor != None:
            if homeaway == "HOME":
                score = home.contents[0] + "-" + visitor.contents[0]
            elif homeaway == "AWAY":
                score = visitor.contents[0] + "-" + home.contents[0]
        scores.append(score)
        
    #TEAM AND OPPONENT PLAY DETAILS
    rows = table_soup.findAll("tr")
    
    delete = [] #THIS LIST ALSO STORES END OF PERIOD LOCATIONS
    for n, row in enumerate(rows):
        if len(row.findAll("td")) < 4:
            delete.append(n)
    for n in reversed(delete):
        rows.pop(n)
    
    details = []
    for row in rows:
        details.append(row.find("span", {"class":"text"}).contents[0].\
                       replace("  ", "").replace('..', '.').replace("\n", ""))
    #for d in details: print d
        
    '''
    OK in order to figure out which team a detail is about, we're gonna loop
    through all the details and look in the position of where the home team's
    detail should be. If it matches, it belongs to the home team. If it doesn't,
    then it's the away team's.
    '''
    for n, row in enumerate(rows):
        contents = row.find_all("td")
        if contents[3].text.replace("  ", "").replace("\n", "") == details[n]:
            #print "yes. home."
            home_details.append(details[n].upper())
            away_details.append("")
        else:
            #print "away"
            away_details.append(details[n].upper())
            home_details.append("")
    
    #print len(home_details), len(away_details), len(scores), len(times)
    
    
    #ADD DATA FOR END AND START OF PERIODS
    shift = 1
    periods_played = 0
    for n, rownum in enumerate(delete):
        #figure out how many periods have been played so far
        for m in delete:
            if n>m: periods_played = periods_played + 1
        
        periods_played = periods_played+1
        
        #write start of period
        if periods_played <= OTcheck: times.insert(rownum+shift, start_time)
        else: times.insert(rownum+shift, START_TIME_OT)
        times.insert(rownum+shift, "00:00")
        scores.insert(rownum+shift, scores[rownum+shift-1])
        scores.insert(rownum+shift, scores[rownum+shift-1])
        home_details.insert(rownum+shift, "START OF PERIOD")
        home_details.insert(rownum+shift, "END OF PERIOD")
        away_details.insert(rownum+shift, "START OF PERIOD")
        away_details.insert(rownum+shift, "END OF PERIOD")
        shift = shift + 1
    
    #for n, s in enumerate(away_details[:-1]): print times[n], scores[n], s, \
        #home_details[n]
    
    if homeaway == "HOME":
        return times[:-1], scores[:-1], home_details[:-1], away_details[:-1]
    elif homeaway == "AWAY":
        return times[:-1], scores[:-1], away_details[:-1], home_details[:-1]
    else:
        return None 


'''
Pulls team names

Args:
soup - gamecast page in BeautifulSoup form

Returns:
(AWAY_NAME, HOME_NAME)
'''
def get_team_names(soup):
    teams = soup.findAll("span", {"class":"team-name"})
    
    if not teams: #handle games not yet played
        return None
    
    names = []
    for n, x in enumerate(teams[:2]):
        names.append(x.contents[0].upper().encode('ascii', 'ignore'))
    
    return names


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
    if not teamnames: #handle games not yet played
        return None, None
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
            print "running similar()..."
            print awayteam, hometeam
            home_similar = le2.similar(hostname, hometeam)
            away_similar = le2.similar(hostname, awayteam)
    
            if home_similar > away_similar and home_similar > 0.7:
                print "similarity:", home_similar
                homeaway = "HOME"
                teamnames = (hostname, awayteam)
                return homeaway, teamnames
            elif away_similar > home_similar and away_similar > 0.7:
                print "similarity:", away_similar
                homeaway = "AWAY"
                teamnames = (hostname, hometeam)
                return homeaway, teamnames

        print ("\n\nThe boxscore page is using a different name than"
               " the given hostname. Do either of these options look like "
               "they could be for the host team?")
        print "\nTeam A:", awayteam, "\nTeam B:", hometeam
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
Gets starting lineup from gamecast page. Used at start of copy_table()

Args:
soup - gamecast page as BeautifulSoup data
homeaway

Returns:
starters - list of length 5 with each player in the starting lineup
'''
def get_starters(soup, homeaway):
    starters = []
    
    if homeaway == "AWAY":
        table_soup = soup.find("div", {"class":"stats-box full lineup visitor clearfix"})
        name_soup = table_soup.find_all("a", {"class":"player-name"})
        #for name in name_soup[:5]:
            #name = name.contents[0].upper().encode('ascii', 'ignore')
            #name = le2.nice_name(name)
            
            #starters.append(name)
                
    if homeaway == "HOME":
        table_soup = soup.find("div", {"class":"stats-box full lineup home clearfix"})
        name_soup = table_soup.find_all("a", {"class":"player-name"})
        
    for name in name_soup[:5]:
        name = name.contents[0].upper().encode('ascii', 'ignore')
        name = le2.nice_name(name)
        
        starters.append(name)                
    
    print "starters:", starters
    return starters


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
only shot types are 3-PT. JUMP SHOT, JUMP SHOT, LAYUP, 3PTR, FREE THROW,
DUNK
'''
'''
def stats(rows, col):
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
        
    #print "2pt fgm:", fgm_2; print "2pt fga:", fga_2; print "3pt fgm:", fgm_3
    #print "3pt fga:", fga_3; print "ftm:", ftm; print "fta:", fta
    #print "ast:", ast; print "to:", to; print "dreb:",dreb; print "oreb:",oreb
    #print "steal:", stl; print "block:", blk; print "fouls:", foul

    return [poss, fgm, fga, fgm_2, fga_2, fgm_3, fga_3, ftm, fta, ast, to, \
            oreb, dreb, stl, blk, foul]
'''

'''
Returns date in string form: Month XX, 20XX
'''
def get_date(soup):
    holder = soup.find('div', {'class':'head'})
    return holder.find('h1').span.text


'''
Uses url path to determine whether the game played is a men's game or a
women's game, regardless of whether its given a schedule url or an individual
game url

Returns:
'M' - for men
'W' - for women
'''
'''
def menwomen(url):
    if url.find('w-baskbl') != -1: return 'W'
    elif url.find('m-baskbl') != -1: return 'M'
    else:
        print "\n\nERRORMESSAGE: No 'w-baskbl' or 'm-baskbl' in url.", \
              "Exiting.\n\n"
        sys.exit(1)
'''


'''
Looks at quarter scoring table in box score to see the game was played in 
2 twenty-minute halves or 4 ten-minute quarters.

Returns:
'M' - for men
'W' - for women / 2018 NIT games
'''
def menwomen(soup):
    table = soup.find("div", {"class":"linescore"})
    periods = table.find_all("th", {"class":"col-head score"})
        
    try:
        value = periods[3].text
    except:
        return 'M'
    
    if value == '4': return 'W'
    else: return 'M'
    
    
'''
Scrape all boxscores given a team's schedule URL.  Helper for scrape_all.

Args:
soup
schedule_url - used for creating url base
hostname

Returns:
urls - list of all links to boxscore
new_info - tells the scrape_all method to actually scrape data from the urls
           if they haven't already been written in read_already
           
http://www.gorhody.com/sports/m-baskbl/2017-18/schedule
'''
def get_boxscores(bigsoup, schedule_url, hostname):
    #bigsoup = le2.get_site(schedule_url)
    
    read_already = le2.been_read(hostname)
    print "\nGames read already:", len(read_already)
    for r in read_already: print r
    
    base = schedule_url[: schedule_url.find("/sports") ]
    
    rows_soup = bigsoup.find_all('div', {'class':'event-info clearfix'})
    if not rows_soup:
        return get_boxscores1(bigsoup, base, read_already)
    
    urls = []
    for row in rows_soup:
        #handle exhibition games
        #assuming exhibition tag is always '#'...
        if "#" not in row.text.upper() and "EXH" not in row.text.upper() and \
           "EXB" not in row.text.upper():
            links = row.find_all('a', {'class':'link'})
            
            for l in links:
                goal = l.get('href')
                if 'boxscore' in goal:
                    if base+goal not in read_already:
                        urls.append(base+goal)
    
    print "\nGames found:", len(urls)
    for u in urls: print u
    return urls


'''
Helper for get_boxscores to scrape from alternate schedule format
ex: http://umbcretrievers.com/sports/mbkb/2017-18/schedule
'''
#TODO: FIND SOMETHING IN THIS FORMAT THAT HAS AN EXHIBITION GAME AND HANDLE
def get_boxscores1(soup, base, read_already):
    rows_soup = soup.find_all('td', {'class':'e_links'})

    urls = []
    for row in rows_soup:
        links = row.find_all('a', {'class':'link'})
        for l in links:
            goal = l.get('href')
            if 'boxscore' in goal:
                if base+goal not in read_already:
                    urls.append(base+goal)
    
    print "Games found:", len(urls)
    for u in urls: print u
    return urls


'''
Given the link to a team's schedule, this function grabs and creates tables
for all the data for every game and writes each to its own file(s)

Args:
schedule_url - link to team's schedule page
               ex: http://gobonnies.sbu.edu/sports/m-baskbl/2017-18/schedule
'''
def scrape_all(soup, schedule_url, hostname): 
    filename = hostname.replace(' ', '').lower().replace('.', '')

    links = get_boxscores(soup, schedule_url, hostname) #111
    #links = ['https://www.santaclarabroncos.com/sports/m-baskbl/2017-18/boxscores/20180201_230l.xml?view=plays#prd2']
    if links == None:
        print "All available data has been scraped alraedy, according to", \
              "TEAMNAME_DONE.txt" 
    
    for l in links:
        print "WORKING ON:", l
        
        r = requests.get(l)
        soup = BeautifulSoup(r.content, "html.parser")   
        
        homeaway, teamnames = run_teamnames(soup, hostname)
        if not homeaway: #handle games not yet played
            break
        
        mw = menwomen(soup)
        
        print hostname, teamnames, homeaway, mw
        
        filename = hostname.replace(' ', '').lower()        
        arg = 1
        
        starters = get_starters(soup, homeaway)
        if not starters:
            #print "\n\nERROR MESSAGE no starters found. Exiting.\n\n"
            #sys.exit(1)
            raise UserWarning("ERROR MESSAGE no starters found")
        else:
            pbp = get_pbp(soup, homeaway, mw)
            play_table = le2.copy_table(pbp, starters, arg)
            le2.lineup_table(play_table, teamnames, filename, get_date(soup), arg)
        
        with open(filename + "DONE.txt",'a') as file:
            file.write(l + "\n")

        print "\n"
    
    le2.dataframe(hostname)
    
    

'''
Args:
soup - soup object to schedule page
schedule_url
hostname - who's website are we scraping from? All caps as it appears on box
           score table header
'''
def main(soup, schedule_url, hostname):
    scrape_all(soup, schedule_url, hostname)
    
'''#111
if __name__ == '__main__':
    start_time = time.time()
    
    main('soup', '', 'SANTA CLARA')
    
    print "\n*done* --- %.4s seconds ---" % (time.time() - start_time)
'''