#! /usr/bin/env python3

'''
PowerScore Display - V5.0

This is primarily intended to run on a Raspberry Pi connected to an HDMI Screen.  This *should* work on any terminal based system where
python with ncurses is supported.  Python3 is required.  Note that this is a command line utility... you will need to run it from the
command line.

For current raspbian installations, you'll need to install a few libraries.  Use the pip3 tool (you may have to install pip3).
These commands should get the required libraries installed on a current raspberry pi using raspbian:

    sudo apt-get install python3-pip
    pip3 install requests
    TODO this is probably not needed anymore ==> pip3 install beautifulsoup4

If you're on another operating system (Windows, OSX, Ubuntu, etc), you're a little on your own.  If you can get python3 installed,
along with the required python libraries, you should be able to get this working.

As of this version, pulling scores from https://ftc-events.firstinspires.org/ is the only supported system.

----------

This version requires setting an API key in a file called "ftc-events-auth.key".  That file should have a single
line with the basic auth string to use.  You can get your own auth key at https://ftc-events.firstinspires.org/services/API.

----------

Sample Usages:

(1) Single divsion

    ./powerscore_display.py 2022 USMOKSCMP

(2) Multiple divisions.  Up to 4 divisions are supported.

    ./powerscore_display.py 2021 FTCCMP1FRNK FTCCMP1JEMI

----------

MIT License

Copyright (c) 2018-2023 The Astromechs - FTC Team 3409

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

import argparse
import curses
import time
import requests
import sys
import os.path
#from bs4 import BeautifulSoup
import re

'''
IMPORTANT NOTE

There are three dictionary objects that will be used throughout the code: event, teams, matches
Ideally these three objects would be well defined in class definitions, but that's something to
do in the future.  For now, we'll just document what they look like.

Here are short examples of each, with indentation for clarity.  Note that matches will ONLY include qualification matches, so
only two teams are supported.  We exclude elim matches because we can't know for sure which teams actually played.

event = {'title': 'Southeast Missouri State University Qualifier', 'subtitle': ''}

teams = {   406:
                {'number': 406, 'name': "Richard's Fine Men", 'school': 'Parkway South High', 'city': 'Manchester',
                 'state': 'MO', 'country': '', 'rank': 8, 'qp': 6, 'rp': 451, 'highest': 289, 'matches': 5,
                 'real_matches': 5, 'allianceScore': 87.1, 'powerScore': 113.59381059999865},
            3620: {'number': 3620, 'name': 'Furious George', ...
            ...
        }

matches =   {   1:
                {'matchid': 1,
                    'alliances': {  'red': {'team1': 7469, 'team2': 406, 'total': 203, 'auto': 55, 'teleop': 128, 'endg': 20, 'pen': 0},
                                    'blue': {'team1': 13616, 'team2': 9905, 'total': 116, 'auto': 60, 'teleop': 36, 'endg': 20, 'pen': 0}
                                 }
                },
                2: {'matchid': 2, 'alliances': ...
                ...
            }

'''

#
# ExternalScoring
#
# This encapsulates the logic for retrieving data from the remote server, as well as the calculation of the current PowerScores
#
# event, teams, and matches dictionary objects are constructed from remote data in these methods
#


class ExternalScoring:
    # Constructor
    def __init__(self,season,division1,division2,division3,division4,auth):
        self.season = season
        self.division1 = division1
        self.division2 = division2
        self.division3 = division3
        self.division4 = division4
        self.auth = auth

        self.numDivisions = 1
        if (self.division4 != ""):
            self.numDivisions=4
        elif (self.division3 != ""):
            self.numDivisions=3
        elif (self.division2 != ""):
            self.numDivisions=2

        self.currentDivision = 0

    # get the URI for the current division
    def getCurrentDivision(self):
        if (self.currentDivision==0):
            return self.division1
        elif (self.currentDivision==1):
            return self.division2
        elif (self.currentDivision==2):
            return self.division3
        elif (self.currentDivision==3):
            return self.division4

    # change the division, wrap around at the maximum number of divisions
    def changeDivisions(self):
        self.currentDivision = self.currentDivision + 1
        self.currentDivision = self.currentDivision % self.numDivisions

    # Get the data from the extenral system ... includes calculating powerscores
    def getEventTeamsMatches(self):

        event = {}
        teams = {}
        matches = {}

        event, teams, matches = self.getEventTeamsMatchesFromFTC()

        # Now update powerscores
        self.__calculatePowerScore(teams, matches)

        return (event, teams, matches)

    # Get data from theorangealliance <== USING THIS AS A TEMPLATE FOR CHANGING TO FTC-EVENTS
    def getEventTeamsMatchesFromFTC(self):

        requestDivision = self.getCurrentDivision()

        requestURI = "http://ftc-api.firstinspires.org/v2.0/"

        event = {}
        teams = {}
        matches = {}

        # print("attempting request ...")

        # why, oh why, does toa make getting the event details so hard.  5 requests are necessary to get the data we need :(
        r=requests.get(requestURI+self.season+'/events?eventCode='+requestDivision, headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
        eventJsonResult = r.json()

        r=requests.get(requestURI+self.season+'/matches/'+requestDivision, headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
        matchesJsonResult = r.json()

        r=requests.get(requestURI+self.season+'/scores/'+requestDivision+"/qual", headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
        scoresJsonResult = r.json()

        r=requests.get(requestURI+self.season+'/teams?eventCode='+requestDivision, headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
        teamsJsonResult = r.json()

        r=requests.get(requestURI+self.season+'/rankings/'+requestDivision, headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
        rankingsJsonResult = r.json()

        # print(eventJsonResult)
        # print("\n======================\n")
        # print(matchesJsonResult)
        # print("\n======================\n")
        # print(teamsJsonResult)
        # print("\n======================\n")
        # print(rankingsJsonResult)
        # print("\n======================\n")

        # print(scoresJsonResult)
        # print("\n======================\n")
        


        # Just a couple of event things
        event['title'] = eventJsonResult['events'][0]['name']
        #event['subtitle'] = ""
        #if "division_name" in eventJsonResult:
        #    event['subtitle'] = eventJsonResult[0]['division_name']

        # print("Event Name: "+ event['title'])

        # Assemble all the team info from the teams request
        for team in teamsJsonResult['teams']:
            teamNum = team["teamNumber"]
            teams[teamNum] = {}
            teams[teamNum]['number'] = teamNum
            teams[teamNum]['name'] = team["nameShort"]
            teams[teamNum]['school'] = ''
            teams[teamNum]['city'] = team["city"]
            teams[teamNum]['state'] = team["stateProv"]
            teams[teamNum]['country'] = team["country"]
            teams[teamNum]['rank'] = 1000    # this forces any non-competing teams to the bottom
            teams[teamNum]['rp'] = 0
            teams[teamNum]['tbp'] = 0
            teams[teamNum]['highest'] = 0
            teams[teamNum]['matches'] = 0
            teams[teamNum]['real_matches'] = 0
            teams[teamNum]['allianceScore'] = 0
            teams[teamNum]['autoAllianceScore'] = 0
            teams[teamNum]['teleAllianceScore'] = 0
            teams[teamNum]['endgAllianceScore'] = 0
            teams[teamNum]['powerScore'] = 0
            teams[teamNum]['autoPowerScore'] = 0
            teams[teamNum]['telePowerScore'] = 0
            teams[teamNum]['endgPowerScore'] = 0

            if teams[teamNum]['name'] == None:
                teams[teamNum]['name'] = ""



        # Add in the ranking information
        for ranking in rankingsJsonResult['Rankings']:
            teamNum = ranking["teamNumber"]
            teams[teamNum]['rank'] = ranking["rank"]
            teams[teamNum]['rp'] = ranking["sortOrder1"]
            teams[teamNum]['tbp'] = ranking["sortOrder2"]
            teams[teamNum]['highest'] = ranking["sortOrder4"]
            teams[teamNum]['matches'] = ranking["matchesPlayed"]
            # teams[teamNum]['allianceScore'] = 0
            # teams[teamNum]['autoAllianceScore'] = 0
            # teams[teamNum]['teleAllianceScore'] = 0
            # teams[teamNum]['endgAllianceScore'] = 0
            # teams[teamNum]['powerScore'] = 100
            # teams[teamNum]['autoPowerScore'] = 100
            # teams[teamNum]['telePowerScore'] = 100
            # teams[teamNum]['endgPowerScore'] = 100





        # Now build up the qualifier matches
        for match in matchesJsonResult['matches']:

            # Stuff to be verified here.  Is the penalty listed for the correct team?  Should there be a filter
            #  for only played matches?
            if (match["tournamentLevel"]=="QUALIFICATION"):

                matchScore = []
                # we have the match, we need to get the scoring object as well
                for score in scoresJsonResult['MatchScores']:
                    if score['matchNumber'] == match['matchNumber']:
                        matchScore = score;
                        break;
                
                # Now figure out the teams in the match
                red1 = 0;
                red2 = 0;
                blue1 = 0;
                blue2 = 0;
                for j in match['teams']:
                    if j['station'] == "Red1":
                        red1 = j['teamNumber']
                    elif j['station'] == "Red2":
                        red2 = j['teamNumber']
                    elif j['station'] == "Blue1":
                        blue1 = j['teamNumber']
                    elif j['station'] == "Blue2":
                        blue2 = j['teamNumber']

                # now find the red scores vs the blue scores
                redScore = [];
                blueScore = [];
                for j in score['alliances']:
                    if j['alliance'] == "Red":
                        redScore = j;
                    elif j['alliance'] == "Blue":
                        blueScore = j;

                matches[match["matchNumber"]] = {}
                matches[match["matchNumber"]]['matchid'] = match["matchNumber"]
                matches[match["matchNumber"]]['alliances'] = {}

                matches[match["matchNumber"]]['alliances']['red'] = {}
                matches[match["matchNumber"]]['alliances']['red']['total'] = redScore['totalPoints']
                matches[match["matchNumber"]]['alliances']['red']['auto'] = redScore['autoPoints']
                matches[match["matchNumber"]]['alliances']['red']['teleop'] = redScore['dcPoints']
                matches[match["matchNumber"]]['alliances']['red']['endg'] = redScore['endgamePoints']
                matches[match["matchNumber"]]['alliances']['red']['pen'] = blueScore['penaltyPointsCommitted']

                matches[match["matchNumber"]]['alliances']['blue'] = {}
                matches[match["matchNumber"]]['alliances']['blue']['total'] = blueScore['totalPoints']
                matches[match["matchNumber"]]['alliances']['blue']['auto'] = blueScore['autoPoints']
                matches[match["matchNumber"]]['alliances']['blue']['teleop'] = blueScore['dcPoints']
                matches[match["matchNumber"]]['alliances']['blue']['endg'] = blueScore['endgamePoints']
                matches[match["matchNumber"]]['alliances']['blue']['pen'] = redScore['penaltyPointsCommitted']

                matches[match['matchNumber']]['alliances']['red']['team1'] = red1
                matches[match['matchNumber']]['alliances']['red']['team2'] = red2
                teams[red1]['real_matches'] += 1
                teams[red2]['real_matches'] += 1

                matches[match['matchNumber']]['alliances']['blue']['team1'] = blue1
                matches[match['matchNumber']]['alliances']['blue']['team2'] = blue2
                teams[blue1]['real_matches'] += 1
                teams[blue2]['real_matches'] += 1

        # Now, going through the "stations" to pick up the teams for the match.
        # Would have been nice it could have been included in the matches response...  oh well

        # print(teams)
        #print(matches)

        return (event, teams, matches)



    # update the PowerScore data for the teams dict object
    def __calculatePowerScore(self,teams, matches):
        #
        # FINALLY - THIS IS IT!  This is the PowerScore Calculation.  Short and sweet.
        #
        # Does not explicitly return anything.  This updates each teams dictionary object with PowerScores.
        #   This code is separated out only for clarity.
        #

        # Get the alliance scores set up
        allianceScores = {}
        for teamNum in teams:
            allianceScores[teamNum] = 0.;
        
        #print("powerscore ...")

        # Now do the allianceScores ... this is needed to "kick off" the calculation
        for matchid in matches:
            match = matches[matchid]

            # The math here takes care of the 50-50 split - each team in an alliance get credit for 50% of the scoring (we'll fix that later)
            # There's also a division by the number of matches for each team ... this has the effect of normalizing to the number of matches played

            # overall powerscore
            adjBlueScore = match["alliances"]["blue"]["total"]-match["alliances"]["blue"]["pen"]
            adjRedScore = match["alliances"]["red"]["total"]-match["alliances"]["red"]["pen"]
            teams[match["alliances"]["blue"]["team1"]]['allianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team1"]]['real_matches'])
            teams[match["alliances"]["blue"]["team2"]]['allianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team2"]]['real_matches'])
            teams[match["alliances"]["red"]["team1"]]['allianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team1"]]['real_matches'])
            teams[match["alliances"]["red"]["team2"]]['allianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team2"]]['real_matches'])

            # auto powerscore
            adjBlueScore = match["alliances"]["blue"]["auto"]
            adjRedScore = match["alliances"]["red"]["auto"]
            teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team1"]]['real_matches'])
            teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team2"]]['real_matches'])
            teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team1"]]['real_matches'])
            teams[match["alliances"]["red"]["team2"]]['autoAllianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team2"]]['real_matches'])

            # teleop powerscore
            adjBlueScore = match["alliances"]["blue"]["teleop"]
            adjRedScore = match["alliances"]["red"]["teleop"]
            teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team1"]]['real_matches'])
            teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team2"]]['real_matches'])
            teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team1"]]['real_matches'])
            teams[match["alliances"]["red"]["team2"]]['teleAllianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team2"]]['real_matches'])

            # teleop powerscore
            adjBlueScore = match["alliances"]["blue"]["endg"]
            adjRedScore = match["alliances"]["red"]["endg"]
            teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team1"]]['real_matches'])
            teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team2"]]['real_matches'])
            teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team1"]]['real_matches'])
            teams[match["alliances"]["red"]["team2"]]['endgAllianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team2"]]['real_matches'])

        # Now on to powerScores ...
        # We'll do a 10 round calculation (tends to work fairly well)
        for i in range(1, 10):
    
            # we build up the powerscore for each team, starting from 0
            for teamid in teams:
                teams[teamid]['powerScore'] = 0
                teams[teamid]['autoPowerScore'] = 0
                teams[teamid]['telePowerScore'] = 0
                teams[teamid]['endgPowerScore'] = 0

            # now we loop through each match, and break up the score based on relative scoring performance.
            for matchid in matches:
                match = matches[matchid]

                # Now, split up the scores, not on a 50-50 split like we did the first time, but based on the alliance scores for each team that we just calculated
                # Again, we're doing the division by the number of matches to normalize to the number of matches played

                # overall powerscore
                adjBlueScore = match["alliances"]["blue"]["total"]-match["alliances"]["blue"]["pen"]
                adjRedScore = match["alliances"]["red"]["total"]-match["alliances"]["red"]["pen"]
                if (teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + teams[match["alliances"]["blue"]["team2"]]['allianceScore']) >0:
                    teams[match["alliances"]["blue"]["team1"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team1"]]['allianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + teams[match["alliances"]["blue"]["team2"]]['allianceScore'])* teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                    teams[match["alliances"]["blue"]["team2"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team2"]]['allianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + teams[match["alliances"]["blue"]["team2"]]['allianceScore'])* teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                if (teams[match["alliances"]["red"]["team1"]]['allianceScore'] + teams[match["alliances"]["red"]["team2"]]['allianceScore']) >0:
                    teams[match["alliances"]["red"]["team1"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team1"]]['allianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['allianceScore'] + teams[match["alliances"]["red"]["team2"]]['allianceScore'])* teams[match["alliances"]["red"]["team1"]]['real_matches'])
                    teams[match["alliances"]["red"]["team2"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team2"]]['allianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['allianceScore'] + teams[match["alliances"]["red"]["team2"]]['allianceScore'])* teams[match["alliances"]["red"]["team2"]]['real_matches'])

                # overall powerscore
                adjBlueScore = match["alliances"]["blue"]["auto"]
                adjRedScore = match["alliances"]["red"]["auto"]
                if (teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] + teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']) >0:
                    teams[match["alliances"]["blue"]["team1"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] + teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore'])* teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                    teams[match["alliances"]["blue"]["team2"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] + teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore'])* teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                if (teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] + teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']) >0:
                    teams[match["alliances"]["red"]["team1"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team1"]]['autoAllianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] + teams[match["alliances"]["red"]["team2"]]['autoAllianceScore'])* teams[match["alliances"]["red"]["team1"]]['real_matches'])
                    teams[match["alliances"]["red"]["team2"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] + teams[match["alliances"]["red"]["team2"]]['autoAllianceScore'])* teams[match["alliances"]["red"]["team2"]]['real_matches'])

                # overall powerscore
                adjBlueScore = match["alliances"]["blue"]["teleop"]
                adjRedScore = match["alliances"]["red"]["teleop"]
                if (teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] + teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']) >0:
                    teams[match["alliances"]["blue"]["team1"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] + teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore'])* teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                    teams[match["alliances"]["blue"]["team2"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] + teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore'])* teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                if (teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] + teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']) >0:
                    teams[match["alliances"]["red"]["team1"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team1"]]['teleAllianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] + teams[match["alliances"]["red"]["team2"]]['teleAllianceScore'])* teams[match["alliances"]["red"]["team1"]]['real_matches'])
                    teams[match["alliances"]["red"]["team2"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] + teams[match["alliances"]["red"]["team2"]]['teleAllianceScore'])* teams[match["alliances"]["red"]["team2"]]['real_matches'])

                # overall powerscore
                adjBlueScore = match["alliances"]["blue"]["endg"]
                adjRedScore = match["alliances"]["red"]["endg"]
                if (teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] + teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']) >0:
                    teams[match["alliances"]["blue"]["team1"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] + teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore'])* teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                    teams[match["alliances"]["blue"]["team2"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] + teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore'])* teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                if (teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] + teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']) >0:
                    teams[match["alliances"]["red"]["team1"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team1"]]['endgAllianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] + teams[match["alliances"]["red"]["team2"]]['endgAllianceScore'])* teams[match["alliances"]["red"]["team1"]]['real_matches'])
                    teams[match["alliances"]["red"]["team2"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] + teams[match["alliances"]["red"]["team2"]]['endgAllianceScore'])* teams[match["alliances"]["red"]["team2"]]['real_matches'])


            # now save the current powerScore as the allianceScore - for use in the next round of calculation if necessary
            for teamid in teams:
                teams[teamid]['allianceScore'] = teams[teamid]['powerScore'] 
                teams[teamid]['autoAllianceScore'] = teams[teamid]['autoPowerScore'] 
                teams[teamid]['teleAllianceScore'] = teams[teamid]['telePowerScore'] 
                teams[teamid]['endgAllianceScore'] = teams[teamid]['endgPowerScore'] 
                
    # all done with the PowerScore calc
            

        
#
# PowerScoreScreen
#
# This represents the actual display.  It relies on curses being already started.  The logic here takes care of the screen dimensions as well
#   the actual displaying of data on the terminal screen.
#
# This code assumes we have the correct structure for the event and teams dict objects (see examples above above)
#
class PowerScoreScreen:

    # Constructor
    def __init__(self, screen):
        self.screen = screen

        # Redefine yellow to be closer to the safety green for the Astromechs
        curses.init_color(curses.COLOR_YELLOW, 680,1000,0)

        curses.curs_set(0)

        self.showDualDiv=False
        self.showMultiPage=False
        self.pageNum=1
        self.demoWinVisible = False

        self.remeasure()
        screen.clear()
        self.drawOverlay()
        screen.refresh()

    # refresh the screeen (wrapper for the curses refresh)
    def refresh(self):
        self.screen.refresh()

        if self.demoWinVisible:
            self.drawDemoWin()

    # recalculate all the key positions on the page
    def remeasure(self):

        # Calculate the key dimensions
        self.screenHeight, self.screenWidth = self.screen.getmaxyx()
        self.screenWidth = 2*(int( self.screenWidth/2))             # Make sure we're working on an even number of character columns

        self.centerSepColumn = int( self.screenWidth / 2) - 1       # Leftmost column for the || separator between columns
        self.dataSpaceWidth =  self.screenWidth - 4                 # Total space for data ... two columns on both the left and right
        self.attributeStartColumn =  self.screenWidth - 96          # Location for the leftmost part of the attribution

        self.powerScoreTitleStart = int( self.dataSpaceWidth/4)-4   # Start of the POWERSCORES title
        self.rankingsTitleStart = int(3* self.dataSpaceWidth/4)-6   # Start of the CURRENT RANKINGS title

        self.leftStartColumn = 2                                            # Leftmost column for data on the left side
        self.leftTeamNameColumn = 8
        self.teamNameWidth =  self.centerSepColumn-45
        self.leftCityStartColumn =  self.centerSepColumn-35
        self.leftCityWidth = 12
        self.leftStateStartColumn =  self.centerSepColumn-21
        self.leftStateWidth = 8
        self.leftPowerScoreStartColumn =  self.centerSepColumn-12

        self.rightStartColumn = int( self.screenWidth / 2) + 3      # Leftmost column for data on the right side
        self.rightTeamNameColumn =  self.rightStartColumn + 6
        self.rightQPStartColumn =  self.rightStartColumn+ self.teamNameWidth+8
        self.rightRPSstartColumn =  self.rightQPStartColumn+9
        self.rightHighestStartCoulumn =  self.rightQPStartColumn+15
        self.rightMatchesStartColumn =  self.rightQPStartColumn+26

        self.sideWidth = int(( self.dataSpaceWidth - 4)/2)

        self.dataRows =  self.screenHeight - 16

    # set the display for dual division
    def setDualDiv(self,isDualDiv):
        self.showDualDiv = isDualDiv

    # set the display for MultiPage (in otherwords, the number of teams exceeds the rows available)
    def setMultiPage(self,isMultiPage):
        self.showMultiPage = isMultiPage

    # is MultiPage on?
    def isMultiPage(self):
        return self.showMultiPage

    # change to the next page (if MultiPage is on)
    def changePage(self):
        if (self.showMultiPage):
            self.pageNum+=1

    def showDemoWin(self, shouldShow):
        self.demoWinVisible = shouldShow

    def drawDemoWin(self):

        # THIS IS WRONG!  Don't lose the reference to the window!

        # just a demo window
        # w = curses.newwin(20,30,10,10)
        # w.border( '|', '|', '-', '-', '+', '+', '+', '+')
        # w.refresh();
        pass

    # draw the Overlay - the part of the page that doesn't change
    def drawOverlay(self):

        screen = self.screen

        # Start colors in curses
        curses.start_color()
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

        bigHeadLine1 = " ____                        ____"
        bigHeadLine2 = "|  _ \ _____      _____ _ __/ ___|  ___ ___  _ __ ___"
        bigHeadLine3 = "| |_) / _ \ \ /\ / / _ \ '__\___ \ / __/ _ \| '__/ _ \ "
        bigHeadLine4 = "|  __/ (_) \ V  V /  __/ |   ___) | (_| (_) | | |  __/  "
        bigHeadLine5 = "|_|   \___/ \_/\_/ \___|_|  |____/ \___\___/|_|  \___| v5 "

        descrLine1 = "Developed by The Astromechs - FTC Team 3409   http://www.kcastromechs.org"
        descrLine2 = ""
        descrLine3 = "PowerScore is a scouting tool that statistically measures the offensive performance of"
        descrLine4 = "FTC Teams at Tournaments.  PowerScore is based on team scoring.  It differs from the FTC"
        descrLine5 = "Qualification/Rating points in that it measures teams by their scoring only, not wins/losses."

        screen.attron(curses.color_pair(1))
        screen.addstr(1, self.leftStartColumn, bigHeadLine1.encode("utf-8"))
        screen.addstr(2, self.leftStartColumn, bigHeadLine2.encode("utf-8"))
        screen.addstr(3, self.leftStartColumn, bigHeadLine3.encode("utf-8"))
        screen.addstr(4, self.leftStartColumn, bigHeadLine4.encode("utf-8"))
        screen.addstr(5, self.leftStartColumn, bigHeadLine5.encode("utf-8"))
        screen.attroff(curses.color_pair(1))

        screen.addstr(1, self.attributeStartColumn, descrLine1)
        screen.addstr(2, self.attributeStartColumn, descrLine2)
        screen.addstr(3, self.attributeStartColumn, descrLine3)
        screen.addstr(4, self.attributeStartColumn, descrLine4)
        screen.addstr(5, self.attributeStartColumn, descrLine5)

        screen.addstr(7, self.leftStartColumn, "=" * self.dataSpaceWidth)

        for i in range(12,self.dataRows+14):
            screen.addstr(i,self.centerSepColumn,"||")

        screen.addstr(10,self.powerScoreTitleStart,"POWERSCORES")
        screen.addstr(10,self.rankingsTitleStart,"CURRENT RANKINGS")

        screen.addstr(12,self.leftStartColumn,"TEAM")
        screen.addstr(12,self.leftCityStartColumn,"City")
        screen.addstr(12,self.leftStateStartColumn,"State")
        screen.addstr(12,self.leftPowerScoreStartColumn,"PowerScore")
        screen.addstr(12,self.rightStartColumn,"TEAM")
        screen.addstr(12,self.rightQPStartColumn,"RP")
        screen.addstr(12,self.rightRPSstartColumn,"TBP")
        screen.addstr(12,self.rightHighestStartCoulumn,"Highest")
        screen.addstr(12,self.rightMatchesStartColumn,"Matches")

        screen.addstr(13,self.leftStartColumn,"-" * self.teamNameWidth )
        screen.addstr(13,self.leftCityStartColumn,"-" * self.leftCityWidth)
        screen.addstr(13,self.leftStateStartColumn,"-" * self.leftStateWidth)
        screen.addstr(13,self.leftPowerScoreStartColumn,"----------")
        screen.addstr(13,self.rightStartColumn,"-" * self.teamNameWidth)
        screen.addstr(13,self.rightQPStartColumn,"--")
        screen.addstr(13,self.rightRPSstartColumn,"----")
        screen.addstr(13,self.rightHighestStartCoulumn,"-------")
        screen.addstr(13,self.rightMatchesStartColumn,"-------")

        return

    # draw the status bar
    def updateStatusBar(self, statusMsg):

        statusbarstr = " 'q' to exit |"
        if (self.showDualDiv):
            statusbarstr += " 'd' to change divisions |"
        if (self.showMultiPage):
            statusbarstr += " 'p' to change pages |"
        statusbarstr +=" (c) 2023 Astromechs Team 3409 "
        if (statusMsg!=""):
            statusbarstr += "| " + str(statusMsg)

        screen = self.screen

        screen.addstr(self.screenHeight-1, 0, " "*self.dataSpaceWidth)    # ensure previous text is cleared fully
        screen.attron(curses.color_pair(3))
        screen.addstr(self.screenHeight-1, 0, statusbarstr)
        screen.attroff(curses.color_pair(3))

        screen.move(self.screenHeight-1, 0)

        return

    # update the team data on the page.  Assumes that the event an teams objects will have the correct structure (see above)
    def updateData(self, event, teams):

        # First ... figure out what the starting position is (based on the current page number)
        # Note... might need to reset the page number if it's now too big
        #
        # For reference, all pages after page 1 have 3 fewer rows (to account for the pageNum display)
        startingPos=0

        if (self.pageNum==1):
            startingPos=0

        else:
            # trying to show a page other than page 1
            if (len(teams)<=self.dataRows):
                # don't need multi page - just force to 1 page and start at the first team
                self.pageNum=1
                startingPos=0

            else:
                # we can do multi page ...
                excess = len(teams)-self.dataRows
                maxPage = 2 + int (excess/(self.dataRows-3))

                if (self.pageNum>maxPage):
                    # went over the max ... loop back to page 1
                    self.pageNum=1
                    startingPos=0
                else:
                    startingPos = self.dataRows + ((self.dataRows - 3) * (self.pageNum-2))

        # Check and set multiPage
        if (len(teams)>self.dataRows):
            self.setMultiPage(True)
        else:
            self.setMultiPage(False)

        screen = self.screen

        # Ensure that we've cleared out any possible old data
        for i in range(14,14+self.dataRows):
            screen.addstr(i,self.leftStartColumn," "*self.dataSpaceWidth)
        screen.addstr(8,self.leftStartColumn," "*self.dataSpaceWidth)
        screen.addstr(9,self.leftStartColumn," "*self.dataSpaceWidth)

        # PowerScores
        pos=0
        if(startingPos==0):
            i=13
        else:
            i=16
            screen.addstr(15,int(self.sideWidth/2)-2,"[ Page "+str(self.pageNum)+" ]")  # This is 2 + (sidewidth/2) - 4
        for teamNum in sorted(teams, key = lambda r: teams[r]["powerScore"], reverse=True):
            team = teams[teamNum]
            pos+=1
            if (pos>startingPos):
                i+=1
                if (i<14+self.dataRows):
                    screen.addstr(i,self.leftStartColumn,"{:>5}".format(teamNum))
                    screen.addstr(i,self.leftTeamNameColumn,team["name"][0:self.teamNameWidth])
                    screen.addstr(i,self.leftCityStartColumn,team["city"][0:self.leftCityWidth])
                    screen.addstr(i,self.leftStateStartColumn,team["state"][0:self.leftStateWidth])
                    screen.addstr(i,self.leftPowerScoreStartColumn,"{:10.2f}".format(team["powerScore"]))

        # Rankings
        pos=0
        if(startingPos==0):
            i=13
        else:
            i=16
            screen.addstr(15,self.rightStartColumn + int(self.sideWidth/2) - 4,"[ Page "+str(self.pageNum)+" ]")
        for teamNum in sorted(teams, key = lambda r: teams[r]["rank"]):
            team = teams[teamNum]
            pos+=1
            if(pos>startingPos):
                i+=1
                if (i<14+self.dataRows):
                    screen.addstr(i,self.rightStartColumn,"{:>5}".format(teamNum))
                    screen.addstr(i,self.rightTeamNameColumn,team["name"][0:self.teamNameWidth])
                    screen.addstr(i,self.rightQPStartColumn,"{:>2}".format(str(team["rp"])))
                    screen.addstr(i,self.rightRPSstartColumn,"{:>4}".format(str(team["tbp"])))
                    screen.addstr(i,self.rightHighestStartCoulumn,"{:>7}".format(str(team["highest"])))
                    screen.addstr(i,self.rightMatchesStartColumn,"{:>7}".format(str(team["matches"])))

        # event and division info
        screen.addstr(8,self.centerSepColumn-4-int(len(event['title'])/2),">>> {} <<<".format(event['title']))

        p = re.compile('^\s?$')
        #if event["subtitle"] != "":
        # if not p.match(event["subtitle"]):
        #     screen.addstr(9,self.centerSepColumn-4-int(len(event['subtitle'])/2),">>> {} <<<".format(event['subtitle']))

        # redraw the center separator
        for i in range(12,self.dataRows+14):
            screen.addstr(i,self.centerSepColumn,"||")



        



#
# UI Main  ... This is where the main loop actually is
#
def ui_main(screen, externalScoring):

    event = []
    teams = []
    matches = []

    # Start up the display, and set for dual div if applicable
    psScreen = PowerScoreScreen(screen)
    psScreen.setDualDiv(externalScoring.numDivisions==2)

    # Nodelay mode ... the main loop will handle updates
    screen.nodelay(1)

    # Set updateRequested to true to force an immediate update
    updateRequested = True

    updateTimer=0

    okToHandle_key_p = True

    # Main run loop
    while 1:
        # Non-blocking (becuase of nodelay)
        keyevent = screen.getch()

        # it's 0.1 seconds later
        updateTimer+=0.1

        # known keyboard input
        if keyevent == ord("q"):
            # quit and break out of the main loop
            break

        if (keyevent == ord("d") and externalScoring.numDivisions==2):
            # change divisions
            externalScoring.changeDivisions()
            updateRequested=True;

        if (keyevent == ord("p") and psScreen.isMultiPage() and okToHandle_key_p):
            # show next page of data
            psScreen.changePage()
            psScreen.updateData(event,teams)
            psScreen.updateStatusBar("")
            psScreen.refresh()
            okToHandle_key_p = False

        if (not okToHandle_key_p) and keyevent != ord("p"):
            okToHandle_key_p = True

        if (keyevent == ord("w")):
            psScreen.showDemoWin(True)
            psScreen.refresh()

        if (keyevent == ord("e")):
            psScreen.showDemoWin(False)
            psScreen.refresh()

        # Has the timer run out?  If so, do an update of the data
        if updateTimer>15:
            updateTimer=0
            updateRequested=True

        # Do we need to do an update?
        if updateRequested:

            updateRequested = False

            # Tell the user we're updating
            psScreen.updateStatusBar("Retrieving data ...")
            screen.refresh()

            try:
                # Get the external data and calculate PowerScore
                event, teams, matches = externalScoring.getEventTeamsMatches()

                # Update the data on the page
                psScreen.updateData(event,teams)
                psScreen.updateStatusBar("")

            except requests.exceptions.Timeout:
                # Handle a timeout on the URL
                psScreen.updateStatusBar("Timeout: will retry in 15 seconds ...")

            except requests.exceptions.ConnectionError:
                # Handle any other generic connection error
                psScreen.updateStatusBar("ConnectionError: will retry in 15 seconds ...")

            # Tell the screen it is now ok to refresh
            psScreen.refresh()

            
        
       

        # Wait for 0.1 seconds before the next time through the loop
        time.sleep(.1)

# Main function ... reads the command line parms and starts up the UI if things look OK
def main():

    parser = argparse.ArgumentParser(
        description='PowerScore Display.  Displays PowerScores based upon event data.',
        epilog='Note: Additional python3 libraries are required.'
        )
    parser.add_argument('season', help='Event season, for example 2022.  Events in Jan-Apr will be the previous year')
    parser.add_argument('event', help='Event identifier, for example USMOKSCMP')
    parser.add_argument('event2', nargs="?", default='', help='optional second event identifier for a multi-division event')
    parser.add_argument('event3', nargs="?", default='', help='optional third event identifier for a multi-division event')
    parser.add_argument('event4', nargs="?", default='', help='optional fourth event identifier for a multi-division event')

    args = parser.parse_args()

    externalScoring = ExternalScoring(args.season, args.event, args.event2, args.event2, args.event4, 'bW9mdGNzY29yZXM6RDdERjdBMDQtNTc3MS00MEU2LTg2RjUtODY2NTQ1NzQ2QUYz')

    # for testing only ... remove this later
    #event, teams, matches = externalScoring.getEventTeamsMatches()

    # Connection looks ok.  Let's start up the UI
    curses.wrapper(ui_main, externalScoring)

# Kick everything off in a nice way
if __name__ == "__main__":
    main()
