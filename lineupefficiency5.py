import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import Select
import sys
import time

import lineupefficiency2 as le2

'''
A second attempt at a comprehensive scraper for the (many) CBSi formats.

A boxscore page can:
- (a) have tags, or (b) be plain text
- list home team names in boxscore as (a) LAST, First or (b) First Last
- list away team names in boxscore as (a) LAST, First or (b) First Last
- list home team names in play data as (a) LAST, First or (b) First Last
- list away team names in play data as (a) LAST, First or (b) First Last
- list host team names in boxscore with (a) links to player pages or (b) without
- list host team names in play data with (a)links to player pages or (b) without

A schedule and results page can:
- be provided by (a) CBSi (with 'more' button) or (b) Neulion

Author: Matt Wang
'''


'''
Gets starting lineup from boxscore page. Used at start of copy_table()

(*) The style of boxscore page the second get_starters helper works on also
requires we run webdriver to get the html page source.  That's why this method
also returns a soup object, as it's the first one called for a boxscore site

Args:
soup - boxscore page as BeautifulSoup data
homeaway

Returns:
starters - list of length 5 with each player in the starting lineup
soup - for reason, see above (*)
'''
def get_starters(soup, homeaway, url):
    #teach it to figure out what kind of website its on and what to run
    tables = soup.find_all("center")
    
    if len(tables) < 4:
        #run helpers for text-style
        holder = soup.find('pre')
        names = holder.find_all('a')
        
        if names:
            (starters, soup) = get_starters1(soup,homeaway)
        else:
            (starters, soup) = get_starters3(soup,homeaway)
            
    else:
        #run helpers for tag-style
        (starters, soup) = get_starters2(url,homeaway)
        
    print("starters:", starters)
    return (starters, soup)
    

'''
Helper
Works on no-tag, text-style boxscore page with starter names listed with
links to their player pages

Uses string parsing to find names of starters regardless of whether they are
linked or not (GW Terry Nolan Jr. bug)
'''
#http://www.goaztecs.com/sports/m-baskbl/stats/2017-2018/wooden04.html
#http://www.broncosports.com/sports/m-baskbl/stats/2017-2018/8dbdfb37.html
#http://www.villanova.com/sports/m-baskbl/stats/2017-2018/game5.html
#http://www.gwsports.com/sports/m-baskbl/stats/2017-2018/gm16uri.html
def get_starters1(soup,homeaway):
    #print "get_starters1"
    holder = soup.find('pre').text
    
    loc1 = holder.find('BLK S MIN')
    loc2 = holder.find('BLK S MIN', loc1+1)
    
    #focus on correct text block
    if homeaway == 'AWAY':
        holder = holder[loc1:loc2]
    elif homeaway == 'HOME':
        holder = holder[loc2:]
    
    #break up rows and ignore stats row
    loc = holder.find('\n')+1
    holder = holder[loc:]
    rows = holder.split('\n')
    
    #isolate name
    starters = []
    for r in rows[:5]:
        name = r[3:24].replace('.', '')
        name = le2.nice_name(name)
        starters.append(name)
    
    return (starters, soup)


'''
Helper
Works on boxscore page with tags, whether players listed with links or not

This page also needs to run webdriver to get the page source, so if this
helper is called, return the new soup object
'''
#http://www.uhcougars.com/sports/m-baskbl/stats/2017-2018/hou1206.html
#http://www.vucommodores.com/sports/m-baskbl/stats/2017-2018/180116m.html
def get_starters2(url, homeaway):
    #print "get_starters2"

    #initialize soup using webdriver 
    soup = le2.get_site(url)
    
    table_soup = soup.find_all("center")[2] #WILL IT ALWAYS BE THE 2nd index?
    
    starters = []
    
    if homeaway == "AWAY":
        rows = table_soup.find_all("tbody")[1].find_all("td", {"align":"left"})
    elif homeaway == "HOME":
        rows = table_soup.find_all("tbody")[2].find_all("td", {"align":"left"})
        
    for r in rows[1:6]:
        name = r.text.encode('ascii', 'ignore')
        name = le2.nice_name(name)
        starters.append(name)
    
    return starters, soup



'''
Helper
Works on text-style boxscore page with no tags, but also no links on player
names
'''
#http://www.lsusports.net/ViewContent.dbml?DB_OEM_ID=5200&CONTENT_ID=2140771
#http://www.goseattleu.com/fls/18200/stats/mbasketball/2017-18/SUMBB17.HTM
def get_starters3(soup, homeaway):
    #print "get_starters3"
    holder = soup.find('pre').text.encode('ascii', 'ignore')
    
    if homeaway == "HOME": tag = "HOME TEAM"
    else: tag = "VISITORS"
    
    newlines = []
    for i in range(len(holder)):
        if holder[i] == '\n':
            newlines.append(i)
    rows = []
    prev = 0
    for i in newlines:
        rows.append(holder[prev:i+1].replace('\n', ''))
        prev = i+1
    
    start = -1
    for i, r in enumerate(rows):
        if tag in r:
            start = i
    segment = rows[ start + 3 : start + 3 + 5 ]
    
    starters = []
    for row in segment:
        end = row.find("..", 3)
        if end == -1:
            end = row.find(". ", 3)
        if end == -1:
            end = row.find(" g", 3)
        if end == -1:
            end = row.find(" f", 3)
        if end == -1:
            end = row.find(" c", 3)
        
        name = row[3:end]
        name = le2.nice_name(name)
        starters.append(name)
        
    return starters, soup


'''
Takes one game's boxscore page and scrapes "raw" play by play table

Args:
soup - game boxscore page in BeautifulSoup form
homeaway - "HOME" or "AWAY"
mw - men or women? 'M' or 'W' (all caps)

Return: All the data needed as individual lists
(times, scores, team_details, opp_details)
'''
def get_pbp(soup,homeaway,mw):
    tables = soup.find_all("center")
    
    if len(tables) < 4:
        #run helper for text-style
        pbp = get_pbp1(soup,homeaway,mw)
        
    else:
        #run helper for tag-style
        pbp = get_pbp2(soup,homeaway,mw)
    
    return pbp

    
   
    
'''
Helper
Works on text-style, no tag boxscore page, regardless of whether or not they
link player names

Returns None if there is no play data or no sub data

from lineupefficiency4
'''
def get_pbp1(soup,homeaway,mw):
    #check for page with no sub data or no play data
    if "SUB IN : " not in soup.text.upper():
        return None
    
    if mw == 'M':
        start_time = le2.START_TIME_M
        OTcheck = 1
    elif mw == 'W':
        start_time = le2.START_TIME_W
        OTcheck = 3
        
    times = []
    scores = []
    home_details = []
    away_details = []
    
    current_score = "0-0"
    
    times.append(start_time)
    scores.append(current_score)
    home_details.append("START OF PERIOD")
    away_details.append("START OF PERIOD")
    
    try:
        pbp = soup.find("span", {"class":"presmall"}).get_text().\
                                                    encode('ascii', 'ignore')
    except:
        try:
            pbp = soup.find_all("pre")[1].get_text().encode('ascii', 'ignore')
        except:
            return None
    
    #split up text mass into rows
    spot = 0 #string index of last \n found
    newlines = []
    while spot < len(pbp)-1:
        nextt = pbp.find('\n', spot)
        spot = nextt+1
        newlines.append(nextt)
    
    rows = []
    for i in range(len(newlines)-1):
        rows.append(pbp[newlines[i]+1:newlines[i+1]])
    
    start_locs = []
    end_locs = []
    #FIND START AND END LOCATIONS IN ROWS
    for n, r in enumerate(rows):
        #print r 
        
        if '----------' in r:
            start_locs.append(n+1)
            
        if r == '\r' or not r: #there are no empty strings, only this \r tag
            if end_locs:
                #only want to add the first empty row, not all the other ones
                #in the buffer space between period pbp data
                if n > end_locs[len(end_locs)-1] + 10:
                    #print start_locs
                    #print end_locs
                    if len(end_locs) < len(start_locs):
                        end_locs.append(n)
            else:
                #don't add any rows too high up cause that just doesn't make
                #..sense
                if n > 10:
                    end_locs.append(n)
                
    #print start_locs
    #print end_locs

    periods_played = 0
    for i in range(len(start_locs)):
        segment = rows[ start_locs[i] : end_locs[i] ]
        
        for r in segment:
            #print r
            
            #TIME - 48th index
            times.append(r[48:48+5].encode('ascii', 'ignore'))
            
            #SCORE - 56th index to first space after
            score_now = r[54:r.find(' ', 56)]
            score_now = score_now.replace(' ', '')
            if score_now:
                if homeaway == "AWAY": score_now = le2.flip(score_now)
                scores.append(score_now.encode('ascii', 'ignore'))
                current_score = score_now.encode('ascii', 'ignore')
            else:
                scores.append(current_score)
                
            #HOME DETAIL
            home_details.append(r[:48].replace('  ', '').\
                            encode('ascii', 'ignore').upper().replace('\r', ''))
            
            #AWAY DETAIL - 67th index
            away_details.append(r[67:].replace('  ', '').\
                            encode('ascii', 'ignore').upper().replace('\r', ''))
        
        periods_played = periods_played + 1
        
        #Insert approproate start/end of period rows
        times.append("00:00")
        if periods_played > OTcheck: times.append(le2.START_TIME_OT)
        else: times.append(start_time)
        scores.append(current_score)
        scores.append(current_score)
        home_details.append("END OF PERIOD")
        home_details.append("START OF PERIOD")
        away_details.append("END OF PERIOD")
        away_details.append("START OF PERIOD")
            
    #for i in range(len(times)-1): print times[i], '\t', scores[i], '\t', away_details[i], '\t', home_details[i]
    
    if homeaway == "HOME":
        return times[:-1], scores[:-1], home_details[:-1], away_details[:-1]
    elif homeaway == "AWAY":
        return times[:-1], scores[:-1], away_details[:-1], home_details[:-1]
    else:
        return None 


'''
Helper
Works on text-style, no tag boxscore page, regardless of whether or not they
link player names

from lineupefficiency4b
'''
def get_pbp2(soup,homeaway,mw):
    #check for page with no sub data or no play data
    if "SUB IN : " not in soup.text.upper():
        return None
    
    if mw == 'M':
        start_time = le2.START_TIME_M
        OTcheck = 1
    elif mw == 'W':
        start_time = le2.START_TIME_W
        OTcheck = 3
    
    times = []
    scores = []
    home_details = []
    away_details = []
    
    current_score = "0-0"
    periods_played = 0
    
    times.append(start_time)
    scores.append(current_score)
    home_details.append("START OF PERIOD")
    away_details.append("START OF PERIOD")
    
    table_soup = soup.find_all("center")[4] #WILL IT ALWAYS BE THE 4TH index?
    
    #find lengths of each period's table
    tables = table_soup.find_all('tbody')
    
    for t in tables:
        
        rows = t.find_all("tr")[1:]

        #if it's a box score table and not a pbp table
        #i figured 6 rows was enough to know
        if len(rows) > 5:
            
            for row in rows:
                entries = row.find_all('td')
                
                #print len(entries), entries
            
                #handle jump ball / tie up lines that can mess everything up
                if len(entries) > 2:
                
                    times.append(entries[1].text.encode('ascii', 'ignore')) #times
                    
                    if entries[2].text: #scores
                        score_now = entries[2].text.encode('ascii', 'ignore')
                        if homeaway == 'AWAY':
                            score_now = le2.flip(score_now)
                        if score_now != current_score:
                            current_score = score_now.replace(' ', '')
                    scores.append(current_score)
                    
                    detail = entries[0].text #home details
                    if detail:
                        home_details.append(detail.encode('ascii', 'ignore').\
                                            upper())
                    else:
                        home_details.append('')
                        
                    detail = entries[4].text #away details
                    if detail:
                        away_details.append(detail.encode('ascii', 'ignore').\
                                            upper())
                    else:
                        away_details.append('')
            
            periods_played = periods_played + 1
            
            #Insert approproate start/end of period rows
            times.append("00:00")
            if periods_played > OTcheck: times.append(le2.START_TIME_OT)
            else: times.append(start_time)
            scores.append(current_score)
            scores.append(current_score)
            home_details.append("END OF PERIOD")
            home_details.append("START OF PERIOD")
            away_details.append("END OF PERIOD")
            away_details.append("START OF PERIOD")
            
    #for n, t in enumerate(away_details[:-1]): print times[n], scores[n], t, home_details[n]
    
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
l - url for it we need to run get_site

Returns:
(AWAY_NAME, HOME_NAME)
'''
def get_team_names(soup, l):
    tables = soup.find_all("center")
    
    if len(tables) < 4:
        #run helper for text-style
        teamnames = get_team_names1(soup)
        
    else:
        #run helper for tag-style
        teamnames = get_team_names2(soup, l)
    
    #print teamnames
    return teamnames



'''
Helper
Works on text-style boxscore pages with no tags

From lineupefficiency4
'''
def get_team_names1(soup):
    #some game pages have no data
    #(http://www.uhcougars.com/sports/m-baskbl/stats/2017-2018/hou0211.html)
    try:
        holder = soup.find("pre").get_text().encode('ascii', 'ignore')
    except:
        return None
        
    #AWAY NAME
    away_loc = holder.find('VISITORS:')
    holder = holder[away_loc:]
    
    #remove rankings marks ('#9 Notre Dame')
    mark2 = holder.find('\n')
    mark = holder[:mark2].find('#')
    if mark != -1:
        space = holder[mark:].find(' ')+1
        holder = holder[:mark] + holder[mark+space:]
    
    #figure out where team name ends
    num_loc = number_loc(holder)-1 
    space_loc = holder.find('\r')
    paren_loc = holder.find('(')-1 #cause trailing space
    locs = [num_loc, space_loc, paren_loc]
    
    to_remove = []
    for l in locs:
        if l < 0:
            to_remove.append(l)
    for l in to_remove:
        locs.remove(l)
        
    end_loc = min(locs)
    away = holder[10 : end_loc]
    
    #HOME NAME
    home_loc = holder.find('HOME TEAM:')
    holder = holder[home_loc:]
    
    #remove rankings marks ('#9 Notre Dame')
    mark2 = holder.find('\n')
    mark = holder[:mark2].find('#')
    if mark != -1:
        space = holder[mark:].find(' ')+1
        holder = holder[:mark] + holder[mark+space:]
    
    num_loc = number_loc(holder)-1
    space_loc = holder.find('\r')
    paren_loc = holder.find('(')-1
    locs = [num_loc, space_loc, paren_loc]
    
    to_remove = []
    for l in locs:
        if l < 0:
            to_remove.append(l)
    for l in to_remove:
        locs.remove(l)
        
    end_loc = min(locs)
    home = holder[11:end_loc]
    
    return away.upper().encode('ascii', 'ignore'), \
           home.upper().encode('ascii', 'ignore')


'''
Helper for get_team_names1.  Finds location of first digit in a string so that
we can isolate the team name and drop the team's record.
'''
def number_loc(string):
    for i in range(len(string)):
        if string[i].isdigit():
            return i


'''
Helper
Works on text-style, no tag boxscore page, regardless of whether or not they
link player names

from lineupefficiency4b
'''
def get_team_names2(soup, url):
    soup = le2.get_site(url)
    
    table = soup.find_all("center")[2] #WILL IT ALWAYS BE THE 2nd index?
    holders = table.find_all('h4')
        
    names = []
    for h in holders:
        h = h.text
        spaces_loc = h.find('  ')
        names.append(h[:spaces_loc].upper().encode('ascii', 'ignore'))
        
    return (names[0], names[1])



'''
Returns date in string form: MM/DD/YY

Works on text and tag formats
'''
def get_date(soup):
    #check format of page
    tables = soup.find_all("center")
        
    if len(tables) < 4:
        #if text style
        holder = soup.find('pre').get_text()

        #remove rankings marks to use isdigit() ('#9 Notre Dame')
        holder = holder[:holder.find('VISITORS')]
        mark = holder.find('#')
        if mark != -1:
            space = holder[mark:].find(' ')+1
            holder = holder[:mark] + holder[mark+space:]
        
        for i in range(len(holder)):
            x = holder[i]
            if holder[i].isdigit():
                break
        space = holder[i:].find(' ')
        date = holder[i:i+space]
    
    else:
        #if tag style
        #WILL IT ALWAYS BE THE 0th index?
        header = soup.find("center").text.encode('ascii', 'ignore')
        start = header.find('(') + 1
        end = header[start:].find(' ')
        date = header[start:start+end]
    
    return date.replace('-', '/').encode('ascii','ignore')


'''
Returns True is pbp data exists on page
False if it does not exist
'''
def pbp_check(soup):
    if 'Play-by-Play' in soup.text:
        return True
    else:
        print("Box score page has no play-by-play data.")
        return False


'''
Determines whether the game was played with 2 halves or 4 quarters.

Returns:
'M' - 2 halves
'W' - 4 quarters (women's games and NIT games)
'''
def menwomen(soup):
    if "4th PERIOD" in soup.text:
        return "W"
    else:
        return "M"


'''
Returns list links to all boxscores on a team's schedule page

Args:
soup
sch_url - link to schedule page
year - int - year of season.  2017-2018 season translates to code of 2017
'''
def get_boxscores(soup, sch_url, year, filename):
    try:
        with open(filename+"DONE.txt",'r') as file:
            read_already = file.read().splitlines()
    except:
        read_already = []
        
    print("read already:", len(read_already), read_already)
    
    if 'baskbl-sched' in sch_url:
        return get_boxscores1(soup,year,sch_url,read_already)
    else:
        return get_boxscores2(soup,sch_url,read_already)


'''
Helper

Works on style of scheudle site with "more" buttons
'''
def get_boxscores1(soup,year,sch_url,read_already):
    base = ("http://grfx.cstv.com/schools/xxschoolcodexx/data/xml/events/"
            "m-baskbl/xxyearxx/xxgameidxx.xml")
    base2 = sch_url[:sch_url.find('/', 7)]
    
    #check schedule year and if it isn't the right one...
    year_selection = str(year) + "-" + str(year+1)
    current_page = soup.find('div', {'class':'schedborder'}).find('div').\
        text.encode('ascii', 'ignore')
    if year_selection not in current_page:
        #..reset soup to page after selecting correct year from dropdown menu
        soup = get_correct_site(sch_url,year_selection)

    text = soup.text.encode('ascii', 'ignore')
    
    #get school code
    start = text.find('schoolCode')
    if start > 15000 or start == -1:
        temp = text.find('usefulSchoolInfo')
        start = text.find('school', temp)
    start1 = text.find('"', start)+1 #find ' or ", whichever comes first
    start2 = text.find("'", start)+1
    starts = []
    if start1 != -1: starts.append(start1)
    if start2 != -1: starts.append(start2)
    start = min(starts)
    end1 = text.find('"', start)
    end2 = text.find("'", start)
    ends = []
    if end1 != -1: ends.append(end1)
    if end2 != -1: ends.append(end2)
    end = min(ends)
    code = text[start:end]
    
    #find exhibition game marker from legend key
    key = soup.find('div', {'class':'schedule-legend-box'})
    if key:
        lines = key.find_all('div')
        exhibition_tag = "asdfadsfasdfasdfasdf"
        for i, l in enumerate(lines):
            if "exhibition" in l.text.lower():
                tag = lines[i-1].text
                if tag != "" and tag != ' ':
                    exhibition_tag = tag.encode('ascii','ignore').\
                        strip().rstrip()
        
    #get game ids
    ids = []
    table_soup = soup.find('table', {'id':'schedtable'})
    row_soup = table_soup.find_all('tr')
    for r in row_soup:
        #handle exhibition games
        if exhibition_tag not in r.text and "Exhibition" not in r.text and \
           "Exh." not in r.text:
            id_raw = r.get('id') #includes Nonetypes for non games
            if id_raw:
                #print id_raw
                ids.append(id_raw.encode('ascii', 'ignore'))
    
    #get interstitial pages with boxscore links
    info_pages = []
    for i in ids:
        info_pages.append(base.replace('xxgameidxx', i).replace('xxyearxx', \
                                    str(year)).replace('xxschoolcodexx', code))
        
    urls = []
    for link in info_pages:
        try:
            r = requests.get(link)
            soup2 = BeautifulSoup(r.content, "html.parser")
        except:
            continue
        
        holder = soup2.find('related')
        if holder:
            holder2 = holder.find_all('link')
            for h in holder2: 
                tag = h.get('value').lower()
                if "final stats" in tag or "box score" in tag or \
                   "stats" in tag or "results" in tag:
                    to_add = (base2 + h.get('url')).encode('ascii', 'ignore')
                    if to_add not in read_already:
                        urls.append(to_add.encode('ascii', 'ignore'))
    
    print("urls length:", len(urls))
    for url in urls: print(url)
    return urls


'''
Helper for get_boxscores1
Use Selenium library to open schedule webpage and select dropdown menu for
current year

Args:
url - team's schedule url
years_str - ex: 2017-2018 - needed to find dropdown selection

Returns: a BeautifulSoup object for the proper year's schedule
'''
def get_correct_site(url, years_str):
    print("running webdriver...")
    
    browser = webdriver.Firefox() 
    browser.get(url)
    
    select = Select(browser.find_element_by_id('Q_SEASON'))
    time.sleep(0.5)
    try:
        select.select_by_visible_text(years_str)
    except:
        browser.execute_script("window.scrollTo(0, 200)")
        time.sleep(1)
        select.select_by_visible_text(years_str)
    
    return_soup = BeautifulSoup(browser.page_source, "html.parser")
    browser.close()
    return return_soup


'''
Helper
'''
def get_boxscores2(soup,sch_url,read_already):
    holders = soup.find_all('a', {'target':'_STATS'})
    base = sch_url[:sch_url.find('/', 7)]
    
    urls = []
    for h in holders:
        link = h.get('href').encode('ascii', 'ignore')
        
        if 'http://' not in link:
            link = base+link
            
        if link not in read_already:
            urls.append(link)
    
    for u in urls: print(u)
    return urls


'''
Driver that runs get_teamnames, gets user input if the team names don't match
the given hostname, and finds homeaway and team names (in correct order)

Args:
soup
hostname
teamnames

Returns:
(homeaway, teamnames)
'''
def run_teamnames(soup, hostname, teamnames):
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

        print("\n\nThe boxscore page is using a different name than"
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
Driver to run the program

Args:
soup
hostname
sch_url 
year - int - ex: 2017 for 2017-2018 season
'''
def run(soup, hostname, sch_url, year):
    filename = hostname.replace(' ', '').lower()

    links = get_boxscores(soup, sch_url, year, filename)
    #links = ['http://www.pepperdinewaves.com/sports/m-baskbl/stats/2017-2018/pepmbb01.html'] #111
    
    print
    no_data = 0
    for l in links:
        print("\n\nworking on:", l)
        
        r = requests.get(l)
        soup = BeautifulSoup(r.content, "html.parser")
        
        teamnames = get_team_names(soup, l)
        if teamnames == None:
            no_data = no_data + 1
        else:
            homeaway, teamnames = run_teamnames(soup, hostname, teamnames)
            
            mw = menwomen(soup)
            
            print(hostname, teamnames, homeaway, mw)
            
            (starters, soup) = get_starters(soup, homeaway, l)
            
            arg = 2
            pbp = get_pbp(soup, homeaway, mw)
            if pbp == None:
                print("No pbp data for this game\n\n")
                no_data = no_data + 1
            else:
                play_table = le2.copy_table(pbp, starters, arg)
                le2.lineup_table(play_table, teamnames, filename, get_date(soup), arg)

        
        #ADD GAME URL TO READ_ALREADY FILE
        with open(filename+"DONE.txt",'a') as file:
            file.write(l + "\n")
        
    le2.dataframe(hostname)
    print("\nGames without data:", no_data)
    

def main(soup,sch_url,hostname,year):
    run(soup,hostname,sch_url,year)


'''#111
if __name__ == '__main__':
    start_time = time.time()
    
    main('soup_placeholder', 'xxx', "PEPPERDINE", 2017)
    
    print "\n*done* --- %.4s seconds ---" % (time.time() - start_time)
'''