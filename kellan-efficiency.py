import pandas as pd
import csv

'''
Take data from all-lineups CSV file created by scraper portion of lineup
efficiency tool and find advanced stats for a team on the whole season
with and without a given player on the floor

INSTRUCTIONS:
- run lineups.py to get all_lineups_TEAMNAME.csv to have data to work with
- edit PARAMETERS global variables to start
'''

#############
## PARAMETERS
#############
PLAYER_FIRST = "depaul-gage" #for creating temporary filenames
PLAYER_FULL = "gage.devin".upper() #as it appears in all-linups file
TEAMNAME = "depaul" #as it appears in all_lineups filename

FILENAME = PLAYER_FIRST + "-efficiencies.csv"

HEADERS = ["index","DATE","TEAM","OPPONENT","TIME IN","TIME OUT","TOTAL_TIME",\
            "SCORE IN","SCORE OUT","+/-","TEAM A","TEAM B","TEAM C",\
            "TEAM D","TEAM E",\
            "POSS","FGM","FGA","2ptFGM","2ptFGA","3ptFGM","3ptFGA","FTM",\
            "FTA","AST","TO","OREB","DREB","STL","BLK","FOULS","Opp_POSS.",\
            "Opp_FGM","Opp_FGA","Opp_2ptFGM","Opp_2ptFGA","Opp_3ptFGM",\
            "Opp_3ptFGA","Opp_FTM","Opp_FTA","Opp_AST","Opp_TO","Opp_OREB",\
            "Opp_DREB","Opp_STL","Opp_BLK","Opp_FOULS"]


'''
'''
def create_kellan_csvs():
    yes_kellan_list = []
    no_kellan_list = []

    df = pd.read_csv(TEAMNAME.lower() + "_all_lineups.csv", header=None)

    for i in df.index:
        if pd.isnull(df.iloc[i][10]) or pd.isnull(df.iloc[i][11]) \
            or pd.isnull(df.iloc[i][12]) or pd.isnull(df.iloc[i][13]) \
            or pd.isnull(df.iloc[i][14]):
            continue

        if PLAYER_FULL == df.iloc[i][11] or PLAYER_FULL == df.iloc[i][12] \
            or PLAYER_FULL == df.iloc[i][13] or PLAYER_FULL == df.iloc[i][14] \
            or PLAYER_FULL == df.iloc[i][10]:
            yes_kellan_list.append(df.loc[i].tolist())
        else:
            no_kellan_list.append(df.loc[i].tolist())

    yes_kellan = pd.DataFrame(data=yes_kellan_list,columns=HEADERS)
    no_kellan = pd.DataFrame(data=no_kellan_list,columns=HEADERS)

    # print yes_kellan.shape
    # print no_kellan.shape

    # yes_kellan.to_csv(PLAYER_FIRST + "-yes.csv",index=False)
    # no_kellan.to_csv(PLAYER_FIRST + "-no.csv",index=False)

    return yes_kellan, no_kellan


'''
read in the stats from one of the dataframes (either yes_kellan or no_kellan
after they've been summed) and return a dictionary with all stats calculated
'''
def stats(summed_series):
    threept_fgm = summed_series['3ptFGM']; fgm = summed_series['FGM']
    fga = summed_series['FGA']; poss = summed_series['POSS']
    points = summed_series['2ptFGM']*2 + threept_fgm*3 + summed_series['FTM']
    oreb = summed_series['OREB']; opp_dreb = summed_series['Opp_DREB']
    
    opp_threept_fgm = summed_series['Opp_3ptFGM']; dreb = summed_series['DREB']
    opp_points = summed_series['Opp_2ptFGM']*2 + opp_threept_fgm*3 + \
                        summed_series['Opp_FTM']
    opp_fgm = summed_series['Opp_FGM']; opp_fga = summed_series['Opp_FGA']
    opp_poss = summed_series[ 'Opp_POSS.']; opp_oreb = summed_series['Opp_OREB']

    ## OE, TORATE, EFG%, FTRATE, 3PTRATE, OREB%, DE, OP_TORATE, OPP_EFG%, 
    ## OPP_FTRATE, OPP_3PTRATE, OPP_OREB%, NET, PACE

    #offensive efficiency, turnover rate, plus/minus over possession
    if poss == 0:
        OE = 0.0
        TORATE = 0.0
    else:
        OE = (points/poss)
        TORATE = float(summed_series['TO']) / poss

    #effective field goal percentage, free throw rate, three point rate, fg%
    #FTrate = fta / fga ??? what if fta is nonzero but fga is?
    if fga == 0:
        EFGPCT = 0.0
        FTRATE = 0.0
        THREEPTRATE = 0.0
    else:
        EFGPCT = (fgm + (0.5*threept_fgm)) / float(fga)
        FTRATE = float(summed_series['FTA']) / float(fga)
        THREEPTRATE = float(summed_series['3ptFGA']) / float(fga)
    
    #offensive rebounding percentage
    #oreb / (oreb + opp-dreb) ?
    if oreb+opp_dreb == 0:
        OREBPCT = 0.0
    else:
        OREBPCT = float(oreb) / float(oreb+opp_dreb)
    
    #defensive efficiency and opponent turnover rate
    if opp_poss == 0:
        DE = 0.0
        OPP_TORATE = 0.0
    else:
        DE = (opp_points/opp_poss)
        OPP_TORATE = (float(summed_series['Opp_TO']) / opp_poss)
        
    #opponent effective field goal percentage, opponent free throw rate,
    #...opponent three point rate, opponent field goal percentage
    if opp_fga == 0:
        OPP_EFGPCT = 0.0
        OPP_FTRATE = 0.0
        OPP_3PTRATE = 0.0
    else:
        OPP_EFGPCT = (opp_fgm + (0.5*opp_threept_fgm)) / float(opp_fga)
        OPP_FTRATE = float(summed_series['Opp_FTA']) / float(opp_fga)
        OPP_3PTRATE = float(summed_series['Opp_3ptFGA']) / float(opp_fga)
        
    #opponent offensive rebounding percentage
    #oreb / (oreb + opp-dreb) ?
    if dreb+opp_oreb == 0:
        OPP_OREBPCT = 0.0
    else:
        OPP_OREBPCT = float(opp_oreb) / float(opp_oreb+dreb)
        
    #total efficiency
    NET = OE - DE
    
    #pace 
    GAME_MINUTES = 40
    PACE = GAME_MINUTES * ((poss + opp_poss) / (2*(summed_series['TOTAL_TIME']/60)))

    return [summed_series['TOTAL_TIME'],poss,PACE,NET,OE,TORATE,EFGPCT,FTRATE,THREEPTRATE,
            OREBPCT,DE,OPP_TORATE,OPP_EFGPCT,OPP_FTRATE,OPP_3PTRATE,OPP_OREBPCT]



'''
'''
def main():
    print "CREATING NEW CSVS FOR", PLAYER_FULL
    print
    
    yes_kellan, no_kellan = create_kellan_csvs()

    # yes_kellan = pd.read_csv(PLAYER_FIRST + "-yes.csv")
    # no_kellan = pd.read_csv(PLAYER_FIRST + "-no.csv")
    all_lineups = pd.read_csv(TEAMNAME + "_all_lineups.csv",names=HEADERS)
    
    yes_kellan = yes_kellan.drop(columns=["index","DATE","TEAM","OPPONENT","TIME IN",
                 "TIME OUT","SCORE IN","SCORE OUT","TEAM A","TEAM B","TEAM C","TEAM D","TEAM E"])
    no_kellan = no_kellan.drop(columns=["index","DATE","TEAM","OPPONENT","TIME IN",
                 "TIME OUT","SCORE IN","SCORE OUT","TEAM A","TEAM B","TEAM C","TEAM D","TEAM E"])
    all_lineups = all_lineups.drop(columns=["index","DATE","TEAM","OPPONENT","TIME IN",
                 "TIME OUT","SCORE IN","SCORE OUT","TEAM A","TEAM B","TEAM C","TEAM D","TEAM E"])    
    
    #print yes_kellan.sum(axis=0).tolist()
    #print no_kellan.sum(axis=0).tolist()

    yes_sums = yes_kellan.sum(axis=0)
    no_sums = no_kellan.sum(axis=0)
    all_sums = all_lineups.sum(axis=0)
    
    print "YES"
    print yes_sums
    print
    print "NO"
    print no_sums
    print
    print "ALL"
    print all_sums


    yes_stats_list = ['WITH'] + stats(yes_sums)
    no_stats_list = ['WITHOUT'] + stats(no_sums)
    all_stats_list = ['ALL'] + stats(all_sums)

    #[summed_series['TOTAL_TIME'],poss,PACE,NET,OE,TORATE,EFGPCT,FTRATE,3PTRATE,
            #OREBPCT,DE,OPP_TORATE,OPP_EFGPCT,OPP_FTRATE,OPP_3PTRATE,OPP_OREBPCT]

    final_headers = ["WITH/WITHOUT","SECONDS","POSS","PACE","NET","OE","TORATE","EFGPCT","FTRATE","3PTRATE","OREBPCT",
                     "DE","OPP_TORATE","OPP_EFTPCT","OPP_FTRATE","OPP_3PTRATE","OPP_OREBPCT"]

    final_csv = pd.DataFrame(data=[yes_stats_list,no_stats_list,all_stats_list],columns=final_headers)
    final_csv.to_csv(PLAYER_FIRST+ "-efficiencies.csv",index=False)

    



if __name__ == '__main__':
    main()

    print "\n*done*\n"