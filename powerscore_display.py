#! /usr/bin/env python3

'''
PowerScore Display - V4.0

This is primarily intended to run on a Raspberry Pi connected to an HDMI Screen.  This *should* work on any terminal based system where
python with ncurses is supported.  Python3 is required.  Note that this is a command line utility... you will need to run it from the
command line.

For current raspbian installations, you'll need to install a few libraries.  Use the pip3 tool (you may have to install pip3).
These commands should get the required libraries installed on a current raspberry pi using raspbian:

    sudo apt-get install python3-pip
    pip3 install requests
    pip3 install beautifulsoup4

If you're on another operating system (Windows, OSX, Ubuntu, etc), you're a little on your own.  If you can get python3 installed,
along with the required python libraries, you should be able to get this working.

----------

Sample Usages:

(1) Data coming from the FTC scoring system web pages ... Single division sample using moftcscores.com

    ./powerscore_display.py http://moftcscores.net/relic-recovery/event/q4

(2) Data coming from from ftcscores.com ... Dual division Sample

    ./powerscore_display.py https://ftcscores.com/event/huD_6Ue9 https://ftcscores.com/event/uy2ep0E1

(3) Data coming from theorangealliance.org ...  Note - you must request your own unique API key from theorangealliance.org

    ./powerscore_display.py -k enter-your-api-key-here https://theorangealliance.org/events/1718-MO-MSU

----------

MIT License

Copyright (c) 2018 The Astromechs - FTC Team 3409

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
from bs4 import BeautifulSoup
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
    def __init__(self,division1URI,division2URI,apiKey):
        self.division1URI = ""
        self.division2URI = ""
        self.setAPIKey(apiKey)
        self.numDivisions = 0
        self.currentDivision = 0
        self.setURIs(division1URI,division2URI)

    def setAPIKey(self, apiKey):
        self.apiKey = apiKey

    # Set the URI's
    def setURIs(self, division1URI, division2URI):
        self.division1URI=division1URI
        self.division2URI=division2URI

        # Do a replacement if the url seems to be for ftcscores.com
        #    https://ftcscores.com/event/huD_6Ue9 is an example ftcscores URL
        #    https://api.ftcscores.com/api/events/huD_6Ue9 is the corresponding api URL
        # Note: no effect if the api url was used, or if the url is not for ftcscores.com
        self.division1URI = self.division1URI.replace("https://ftcscores.com/event/", "https://api.ftcscores.com/api/events/")
        self.division2URI = self.division2URI.replace("https://ftcscores.com/event/", "https://api.ftcscores.com/api/events/")

        # Do a replacement if the url seems to be for theorangealliance.org
        #    https://theorangealliance.org/events/1718-MO-CAPS is an example ftcscores URL
        #    https://theorangealliance.org/apiv2/event/1718-MO-CAPS is the corresponding event api URL
        # Note: no effect if the api url was used, or if the url is not for ftcscores.com
        self.division1URI = self.division1URI.replace("https://theorangealliance.org/events/", "https://theorangealliance.org/apiv2/event/")
        self.division2URI = self.division2URI.replace("https://theorangealliance.org/events/", "https://theorangealliance.org/apiv2/event/")

        if (self.division2URI == ""):
            self.numDivisions=1
            self.currentDivision=1

        else:
            self.numDivisions=2
            self.currentDivision=1

    # get the URI for the current division
    def getCurrentDivisionURI(self):
        if (self.currentDivision==1):
            return self.division1URI
        else:
            return self.division2URI

    # change the division
    def changeDivisions(self):
        if (self.currentDivision==1 and self.numDivisions==2):
            self.currentDivision=2
        else:
            self.currentDivision=1

    # Get the data from the extenral system ... includes calculating powerscores
    def getEventTeamsMatches(self):

        event = {}
        teams = {}
        matches = {}

        requestURI = self.getCurrentDivisionURI()

        if "api.ftcscores.com" in requestURI:
            # Specific logic for ftcscores.com
            event, teams, matches = self.getEventTeamsMatches_ftcscores()

        elif "theorangealliance.org/apiv2" in requestURI:
            # Specific logic for theorangealliance
            event, teams, matches = self.getEventTeamsMatches_toa()

        elif "worlds.pennfirst.org/cache/TeamInfo" in requestURI:
            # Specific logic for worlds ... works for 2018 at least
            event, teams, matches = self.getEventTeamsMatches_pennfirst()

        else:
            # Default logic - ftc scoring system
            event, teams, matches = self.getEventTeamsMatches_default()

        # Now update powerscores
        self.__calculatePowerScore(teams, matches)

        return (event, teams, matches)


    # Get data from ftcscores
    def getEventTeamsMatches_ftcscores(self):

        requestURI = self.getCurrentDivisionURI()

        event = {}
        teams = {}
        matches = {}

        r=requests.get(requestURI, timeout=5)
        jsonResult = r.json()

        # Just a couple of event things
        event['title'] = jsonResult['fullName']
        event['subtitle'] = ""
        if "subtitle" in jsonResult:
            event['subtitle'] = jsonResult['subtitle']

        # Assemble all the team info from the teams and rankings sections
        if "teams" in jsonResult:
            for team in jsonResult["teams"]:
                teamNum = jsonResult["teams"][team]["number"]
                teams[teamNum] = {}
                teams[teamNum]['number'] = teamNum
                teams[teamNum]['name'] = jsonResult["teams"][team]["name"]
                teams[teamNum]['school'] = jsonResult["teams"][team]["school"]
                teams[teamNum]['city'] = jsonResult["teams"][team]["city"]
                teams[teamNum]['state'] = jsonResult["teams"][team]["state"]
                teams[teamNum]['country'] = jsonResult["teams"][team]["country"]
        if "rankings" in jsonResult:
            for ranking in jsonResult["rankings"]:
                teamNum = ranking["number"]
                teams[teamNum]['rank'] = ranking["rank"]
                teams[teamNum]['qp'] = ranking["current"]["qp"]
                teams[teamNum]['rp'] = ranking["current"]["rp"]
                teams[teamNum]['highest'] = ranking["current"]["highest"]
                teams[teamNum]['matches'] = ranking["current"]["matches"]
                teams[teamNum]['real_matches'] = 0
                teams[teamNum]['allianceScore'] = 0
                teams[teamNum]['powerScore'] = 0


        # Now grab the matches, we want completed qualifier matches only
        if "rankings" in jsonResult:
            for match in jsonResult["matches"]:
                if ((match["number"].startswith("Q")) and (match["status"]=="done")):
                    matches[match["number"]] = {}
                    matches[match["number"]]['matchid'] = match["number"]
                    matches[match["number"]]['alliances'] = {}

                    matches[match["number"]]['alliances']['red'] = {}
                    matches[match["number"]]['alliances']['red']['team1'] = match["teams"]['red'][0]['number']
                    matches[match["number"]]['alliances']['red']['team2'] = match["teams"]['red'][1]['number']
                    matches[match["number"]]['alliances']['red']['total'] = match["scores"]['red']
                    matches[match["number"]]['alliances']['red']['auto'] = match["subscoresRed"]['auto']
                    matches[match["number"]]['alliances']['red']['teleop'] = match["subscoresRed"]['tele']
                    matches[match["number"]]['alliances']['red']['endg'] = match["subscoresRed"]['endg']
                    matches[match["number"]]['alliances']['red']['pen'] = match["subscoresRed"]['pen']
                    #also... udpate the "real matches"... to account for surrogates in powerscore
                    teams[match["teams"]['red'][0]['number']]['real_matches']+=1
                    teams[match["teams"]['red'][1]['number']]['real_matches']+=1

                    matches[match["number"]]['alliances']['blue'] = {}
                    matches[match["number"]]['alliances']['blue']['team1'] = match["teams"]['blue'][0]['number']
                    matches[match["number"]]['alliances']['blue']['team2'] = match["teams"]['blue'][1]['number']
                    matches[match["number"]]['alliances']['blue']['total'] = match["scores"]['blue']
                    matches[match["number"]]['alliances']['blue']['auto'] = match["subscoresBlue"]['auto']
                    matches[match["number"]]['alliances']['blue']['teleop'] = match["subscoresBlue"]['tele']
                    matches[match["number"]]['alliances']['blue']['endg'] = match["subscoresBlue"]['endg']
                    matches[match["number"]]['alliances']['blue']['pen'] = match["subscoresBlue"]['pen']
                    #also... udpate the "real matches"... to account for surrogates in powerscore
                    teams[match["teams"]['blue'][0]['number']]['real_matches']+=1
                    teams[match["teams"]['blue'][1]['number']]['real_matches']+=1

        return (event, teams, matches)

    # Get data from theorangealliance
    def getEventTeamsMatches_toa(self):

        requestURI = self.getCurrentDivisionURI()

        event = {}
        teams = {}
        matches = {}

        # why, oh why, does toa make getting the event details so hard.  5 requests are necessary to get the data we need :(
        r=requests.get(requestURI, headers={'X-Application-Origin': 'PowerScore', 'X-TOA-Key': self.apiKey},  timeout=5)
        eventJsonResult = r.json()

        r=requests.get(requestURI+"/matches", headers={'X-Application-Origin': 'PowerScore', 'X-TOA-Key': self.apiKey},  timeout=5)
        matchesJsonResult = r.json()

        r=requests.get(requestURI+"/matches/stations", headers={'X-Application-Origin': 'PowerScore', 'X-TOA-Key': self.apiKey},  timeout=5)
        stationsJsonResult = r.json()

        r=requests.get(requestURI+"/teams", headers={'X-Application-Origin': 'PowerScore', 'X-TOA-Key': self.apiKey},  timeout=5)
        teamsJsonResult = r.json()

        r=requests.get(requestURI+"/rankings", headers={'X-Application-Origin': 'PowerScore', 'X-TOA-Key': self.apiKey},  timeout=5)
        rankingsJsonResult = r.json()


        # Just a couple of event things
        event['title'] = eventJsonResult[0]['event_name']
        event['subtitle'] = ""
        if "division_name" in eventJsonResult:
            event['subtitle'] = eventJsonResult[0]['division_name']

        # Assemble all the team info from the teams request
        for team in teamsJsonResult:
            teamNum = int(team["team_key"])
            teams[teamNum] = {}
            teams[teamNum]['number'] = teamNum
            teams[teamNum]['name'] = team["team_name_short"]
            teams[teamNum]['school'] = ''
            teams[teamNum]['city'] = team["city"]
            teams[teamNum]['state'] = team["state_prov"]
            teams[teamNum]['country'] = team["country"]

        # Add in the ranking information
        for ranking in rankingsJsonResult:
            teamNum = int(ranking["team_key"])
            teams[teamNum]['rank'] = ranking["rank"]
            teams[teamNum]['qp'] = ranking["qualifying_points"]
            teams[teamNum]['rp'] = ranking["ranking_points"]
            teams[teamNum]['highest'] = ranking["highest_qual_score"]
            teams[teamNum]['matches'] = ranking["played"]
            teams[teamNum]['real_matches'] = 0
            teams[teamNum]['allianceScore'] = 0
            teams[teamNum]['powerScore'] = 0


        # Now build up the qualifier matches
        for match in matchesJsonResult:

            # This seems to mark a qualifier match, but they haven't documented it
            # Still have no idea how an upcoming match is delineated... so making best guess
            if ((match["tournament_level"]==1) and (match["blue_score"]!=None)):
                matches[match["match_key"]] = {}
                matches[match["match_key"]]['matchid'] = match["match_key"]
                matches[match["match_key"]]['alliances'] = {}

                matches[match["match_key"]]['alliances']['red'] = {}
                matches[match["match_key"]]['alliances']['red']['total'] = match["red_score"]
                matches[match["match_key"]]['alliances']['red']['auto'] = match["red_auto_score"]
                matches[match["match_key"]]['alliances']['red']['teleop'] = match["red_tele_score"]
                matches[match["match_key"]]['alliances']['red']['endg'] = match["red_end_score"]
                matches[match["match_key"]]['alliances']['red']['pen'] = match["blue_penalty"]


                matches[match["match_key"]]['alliances']['blue'] = {}
                matches[match["match_key"]]['alliances']['blue']['total'] = match["blue_score"]
                matches[match["match_key"]]['alliances']['blue']['auto'] = match["blue_auto_score"]
                matches[match["match_key"]]['alliances']['blue']['teleop'] = match["blue_tele_score"]
                matches[match["match_key"]]['alliances']['blue']['endg'] = match["blue_end_score"]
                matches[match["match_key"]]['alliances']['blue']['pen'] = match["red_penalty"]

        # Now, going through the "stations" to pick up the teams for the match.
        # Would have been nice it could have been included in the matches reponse...  oh well
        for station in stationsJsonResult:
            if (station["match_key"] in matches):

                # red teams
                matches[station["match_key"]]['alliances']['red']['team1'] = int(station["teams"].split(",")[0])
                matches[station["match_key"]]['alliances']['red']['team2'] = int(station["teams"].split(",")[1])
                #also... udpate the "real matches"... to account for surrogates in powerscore
                teams[int(station["teams"].split(",")[0])]['real_matches']+=1
                teams[int(station["teams"].split(",")[1])]['real_matches']+=1

                # blue teams
                matches[station["match_key"]]['alliances']['blue']['team1'] = int(station["teams"].split(",")[2])
                matches[station["match_key"]]['alliances']['blue']['team2'] = int(station["teams"].split(",")[3])
                #also... udpate the "real matches"... to account for surrogates in powerscore
                teams[int(station["teams"].split(",")[2])]['real_matches']+=1
                teams[int(station["teams"].split(",")[3])]['real_matches']+=1

        return (event, teams, matches)

    # Get the data the default way ... e.g. from the socring software
    def getEventTeamsMatches_default(self):
        requestURI = self.getCurrentDivisionURI()
        return self.getEventTeamsMatches_ScoringURLs(requestURI+"/TeamList", requestURI+"/Rankings", requestURI+"/MatchDetails")

    # Special case for worlds, or an event that follows the worlds/pennfirst pattern
    def getEventTeamsMatches_pennfirst(self):
        # The expectation here is that the url is pointing at the TeamInfo page
        #http://houston.worlds.pennfirst.org/cache/TeamInfo_2018_World_Championship_Franklin.html?_=1524026469419
        requestURI = self.getCurrentDivisionURI()
        p = re.compile('(http://.*/cache/)TeamInfo(.*\.html).*')
        m = p.match(requestURI)

        teamListURL = m.group(1)+'TeamInfo'+m.group(2)
        rankingsURL = m.group(1)+'Rankings'+m.group(2)
        matchDetailsURL = m.group(1)+'MatchResultsDetails'+m.group(2)   # why was this renamed from MatchDetails on pennfirst???

        return self.getEventTeamsMatches_ScoringURLs(teamListURL,rankingsURL,matchDetailsURL)

    # commoon method to handle the ftc scoring system urls ... helps becuase of events that do goofy things with URLs
    def getEventTeamsMatches_ScoringURLs(self,teamListURL, rankingsURL, matchDetailsURL):

        event = {}
        teams = {}
        matches = {}

        # Not one of the specific known use cases ... so try as though it's the scoring software
        r=requests.get(teamListURL, timeout=3)
        teamListHTML = r.text
        teamList = BeautifulSoup(teamListHTML, "html.parser")

        r=requests.get(rankingsURL, timeout=3)
        rankingsHTML = r.text
        rankings = BeautifulSoup(rankingsHTML,"html.parser")

        r=requests.get(matchDetailsURL, timeout=3)
        matchDetailsHTML = r.text
        matchDetails = BeautifulSoup(matchDetailsHTML,"html.parser")

        # If we got here without failing, then we probably have a good set of data

        h2 = teamList.html.center.h2
        # Just a couple of event things
        event['title'] = h2.contents[0]
        event['subtitle'] = ""
        if (len(h2.contents)>3):
            event['subtitle'] = h2.contents[2].lstrip()

        # Get teams from the team list
        i=0
        for tr in  teamList.html.div.table.find_all("tr"):
            i+=1
            if i>1:
                teamNum = int(tr.contents[0].string)
                teams[teamNum] = {}
                teams[teamNum]['number'] = teamNum
                teams[teamNum]['name'] = tr.contents[1].string
                teams[teamNum]['school'] = tr.contents[2].string
                teams[teamNum]['city'] = tr.contents[3].string
                teams[teamNum]['state'] = tr.contents[4].string
                teams[teamNum]['country'] = tr.contents[5].string
        # Add in the Ranking info
        i=0
        for tr in  rankings.html.div.table.find_all("tr"):
            i+=1
            if i>1:
                teamNum = int(tr.contents[1].string)
                teams[teamNum]['rank'] = int(tr.contents[0].string)
                teams[teamNum]['qp'] = int(tr.contents[3].string)
                teams[teamNum]['rp'] = int(tr.contents[4].string)
                teams[teamNum]['highest'] = int(tr.contents[5].string)
                teams[teamNum]['matches'] = int(tr.contents[6].string)
                teams[teamNum]['real_matches'] = 0
                teams[teamNum]['allianceScore'] = 0
                teams[teamNum]['powerScore'] = 0

        # Now grab the matches, we want completed qualifier matches only
        i=0
        for tr in  matchDetails.html.div.table.find_all("tr"):
            i+=1
            if i>2:
                if (("-" in tr.contents[1].string) and ("Q" in tr.contents[0].string)):
                    # A dash in the score column means we have a score, so the match has been played
                    # A Q in the first column means it's a qualifier match
                    matchNum = int(tr.contents[0].string.split("-")[1])
                    matches[matchNum] = {}
                    matches[matchNum]['matchid'] = matchNum
                    matches[matchNum]['alliances'] = {}

                    matches[matchNum]['alliances']['red'] = {}
                    matches[matchNum]['alliances']['red']['team1'] = int(tr.contents[2].string.split()[0].replace("*",""))
                    matches[matchNum]['alliances']['red']['team2'] = int(tr.contents[2].string.split()[1].replace("*",""))
                    matches[matchNum]['alliances']['red']['total'] = int(tr.contents[4].string)
                    matches[matchNum]['alliances']['red']['auto'] = int(tr.contents[5].string)
                    matches[matchNum]['alliances']['red']['teleop'] = int(tr.contents[7].string)
                    matches[matchNum]['alliances']['red']['endg'] = int(tr.contents[8].string)
                    matches[matchNum]['alliances']['red']['pen'] = int(tr.contents[9].string)
                    #also... udpate the "real matches"... to account for surrogates in powerscore
                    teams[int(tr.contents[2].string.split()[0].replace("*",""))]['real_matches']+=1
                    teams[int(tr.contents[2].string.split()[1].replace("*",""))]['real_matches']+=1

                    matches[matchNum]['alliances']['blue'] = {}
                    matches[matchNum]['alliances']['blue']['team1'] = int(tr.contents[3].string.split()[0].replace("*",""))
                    matches[matchNum]['alliances']['blue']['team2'] = int(tr.contents[3].string.split()[1].replace("*",""))
                    matches[matchNum]['alliances']['blue']['total'] = int(tr.contents[10].string)
                    matches[matchNum]['alliances']['blue']['auto'] = int(tr.contents[11].string)
                    matches[matchNum]['alliances']['blue']['teleop'] = int(tr.contents[13].string)
                    matches[matchNum]['alliances']['blue']['endg'] = int(tr.contents[14].string)
                    matches[matchNum]['alliances']['blue']['pen'] = int(tr.contents[15].string)
                    #also... udpate the "real matches"... to account for surrogates in powerscore
                    teams[int(tr.contents[3].string.split()[0].replace("*",""))]['real_matches']+=1
                    teams[int(tr.contents[3].string.split()[1].replace("*",""))]['real_matches']+=1

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

        # Now do the allianceScores total
        for matchid in matches:
            match = matches[matchid]

            adjBlueScore = match["alliances"]["blue"]["total"]-match["alliances"]["blue"]["pen"]
            adjRedScore = match["alliances"]["red"]["total"]-match["alliances"]["red"]["pen"]

            # The math here takes care of the 50-50 split - each team in an alliance get credit for 50% of the scoring (we'll fix that later)
            # There's also a division by the number of matches for each team ... this has the effect of normalizing to the number of matches played
            teams[match["alliances"]["blue"]["team1"]]['allianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team1"]]['real_matches'])
            teams[match["alliances"]["blue"]["team2"]]['allianceScore'] += adjBlueScore/(2.*teams[match["alliances"]["blue"]["team2"]]['real_matches'])
            teams[match["alliances"]["red"]["team1"]]['allianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team1"]]['real_matches'])
            teams[match["alliances"]["red"]["team2"]]['allianceScore'] += adjRedScore/(2.*teams[match["alliances"]["red"]["team2"]]['real_matches'])

        # OK... now on to powerScores
        for matchid in matches:
            match = matches[matchid]

            adjBlueScore = match["alliances"]["blue"]["total"]-match["alliances"]["blue"]["pen"]
            adjRedScore = match["alliances"]["red"]["total"]-match["alliances"]["red"]["pen"]

            # Now, split up the scores, not on a 50-50 split like we did the first time, but based on the alliance scores for each team that we just calculated
            # Again, we're doing the division by the number of matches to normalize to the number of matches played
            if (teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + teams[match["alliances"]["blue"]["team2"]]['allianceScore']) >0:
                teams[match["alliances"]["blue"]["team1"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team1"]]['allianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + teams[match["alliances"]["blue"]["team2"]]['allianceScore'])* teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                teams[match["alliances"]["blue"]["team2"]]['powerScore'] += adjBlueScore * teams[match["alliances"]["blue"]["team2"]]['allianceScore']/ ((teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + teams[match["alliances"]["blue"]["team2"]]['allianceScore'])* teams[match["alliances"]["blue"]["team2"]]['real_matches'])
            if (teams[match["alliances"]["red"]["team1"]]['allianceScore'] + teams[match["alliances"]["red"]["team2"]]['allianceScore']) >0:
                teams[match["alliances"]["red"]["team1"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team1"]]['allianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['allianceScore'] + teams[match["alliances"]["red"]["team2"]]['allianceScore'])* teams[match["alliances"]["red"]["team1"]]['real_matches'])
                teams[match["alliances"]["red"]["team2"]]['powerScore'] += adjRedScore * teams[match["alliances"]["red"]["team2"]]['allianceScore']/ ((teams[match["alliances"]["red"]["team1"]]['allianceScore'] + teams[match["alliances"]["red"]["team2"]]['allianceScore'])* teams[match["alliances"]["red"]["team2"]]['real_matches'])

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

        self.showDualDiv=False
        self.showMultiPage=False
        self.pageNum=1

        self.remeasure()
        screen.clear()
        self.drawOverlay()
        screen.refresh()

    # refresh the screeen (wrapper for the curses refresh)
    def refresh(self):
        self.screen.refresh()

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
        bigHeadLine5 = "|_|   \___/ \_/\_/ \___|_|  |____/ \___\___/|_|  \___| v4.0 "

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
        screen.addstr(12,self.rightQPStartColumn,"QP")
        screen.addstr(12,self.rightRPSstartColumn,"RP")
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
        statusbarstr +=" (c) 2018 Astromechs Team 3409 "
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
                    screen.addstr(i,self.rightQPStartColumn,"{:>2}".format(str(team["qp"])))
                    screen.addstr(i,self.rightRPSstartColumn,"{:>4}".format(str(team["rp"])))
                    screen.addstr(i,self.rightHighestStartCoulumn,"{:>7}".format(str(team["highest"])))
                    screen.addstr(i,self.rightMatchesStartColumn,"{:>7}".format(str(team["matches"])))

        # event and division info
        screen.addstr(8,self.centerSepColumn-4-int(len(event['title'])/2),">>> {} <<<".format(event['title']))
        if event["subtitle"] != "":
            screen.addstr(9,self.centerSepColumn-4-int(len(event['subtitle'])/2),">>> {} <<<".format(event['subtitle']))

        # redraw the center separator
        for i in range(12,self.dataRows+14):
            screen.addstr(i,self.centerSepColumn,"||")



#
# UI Main  ... This is where the main loop actually is
#
def ui_main(screen, externalScoring):

    # Start up the display, and set for dual div if applicable
    psScreen = PowerScoreScreen(screen)
    psScreen.setDualDiv(externalScoring.numDivisions==2)

    # Nodelay mode ... the main loop will handle updates
    screen.nodelay(1)

    # Set updateRequested to true to force an immediate update
    updateRequested = True

    updateTimer=0

    # Main run loop
    while 1:
        # Non-blocking (becuase of nodelay)
        event = screen.getch()

        # it's 0.1 seconds later
        updateTimer+=0.1

        # known keyboard input
        if event == ord("q"):
            # quit and break out of the main loop
            break

        if (event == ord("d") and externalScoring.numDivisions==2):
            # change divisions
            externalScoring.changeDivisions()
            updateRequested=True;

        if (event == ord("p") and psScreen.isMultiPage()):
            # show next page of data
            psScreen.changePage()
            updateRequested=True

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
    parser.add_argument('-k','--key', default='', help='API key - currently supported for theorangealliance.org urls only')
    parser.add_argument('url1', help='URL for retrieving scoring information.')
    parser.add_argument('url2', nargs="?", default='', help='optional URL for retrieving scoring information for a second division.  Used for dual division events only.')

    args = parser.parse_args()

    externalScoring = ExternalScoring(args.url1,args.url2,args.key)

    #   Check to see if we can get data from the external system.  Any failure on this initial connection
    #   and we'll give the user an error.
    #try:
    event, teams, matches = externalScoring.getEventTeamsMatches()

    #except:
    #    print("ERROR: Initial contact of the scoring system failed.")
    #    print()
    #    exit()

     # Connection looks ok.  Let's start up the UI
    curses.wrapper(ui_main, externalScoring)

# Kick everything off in a nice way
if __name__ == "__main__":
    main()
