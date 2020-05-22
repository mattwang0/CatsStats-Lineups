import time
import sys
import lineupefficiency2 as le2
import lineupefficiency3 as le3
import lineupefficiency5 as le5


'''
Driver for the lineup efficiency tool

Author: Matt Wang
'''

'''
Determine which lineup efficiency helper to run and run it

Args:
sch_url
hostname
year - for le5 helper only
'''
def run(sch_url, hostname, year):
    soup = le2.get_site(sch_url)
    text = soup.text.upper()
    if 'SIDEARM' in text:
        print("\nSIDEARM SPORTS\n")
        
        le2.main(soup, sch_url, hostname)
        
    elif "CBSI" in text or "NEULION" in text:
        print("\nCBSi/NEULION\n")

        #error handling
        if year == -1:
            #print "ERRORMESSAGE: Given website is in CBSi format and needs " \
                  #"year argument to run.\n", sch_url
            #sys.exit(1)
            print(sch_url)
            raise UserWarning("ERRORMESSAGE: Given website is in CBSi format "\
                              "and needs year argument to run.")
            
        
        le5.main(soup, sch_url, hostname, year)
        
    else:
        print("\nPRESTO SPORTS\n")
        
        le3.main(soup, sch_url, hostname) 
    
def main():
    #read file with info on which teams to analyze
    filename = 'todo.txt'
    try:
        with open(filename,'r') as file:
            todo = file.read().splitlines()
    except:
        print("ERROR: todo.txt file with information on which sites to read " \
              "data from not found in cwd.")
        raise UserWarning("ERROR: todo.txt file with information on which "\
                          "sites to read data from not found in cwd")

    #TEST
    #todo = ["2017 http://www.pepperdinewaves.com/sports/m-baskbl/sched/pepp-m-baskbl-sched.html pepperdine"] #111
    
    for line in todo:
        #check if 'arg1' is a year (le5 format)...
        year = -1 #arg for if we run le5.main
        if line[0].isdigit():
            year = int(line[:4])
            line = line[5:]
        
        loc = line.find(' ')
        if loc == -1:
            print(line)
            raise UserWarning("ERROR with argument lines in todo.txt")
        sch_url = line[:loc]
        hostname = line[loc+1:].upper()
        
        print()
        print(hostname)
        print(sch_url)
        print("year:", year)
        
        #try:
            #run(sch_url, hostname, year)
        #except Exception as e:
            #with open('error.txt','a') as file:
                #file.write('Error with ' + hostname + ': ' + str(e) + '\n')
        run(sch_url, hostname, year) #111
        
    
if __name__ == '__main__':
    print("*starting...*")
    
    start_time = time.time()
    
    main()

    print("\n*done* --- %s seconds ---" % (time.time() - start_time))