#
# ExternalScoring
#
# This encapsulates the logic for retrieving data from the remote server, as well as the calculation of the current PowerScores
#
# event, teams, and matches dictionary objects are constructed from remote data in these methods
#

from math import sqrt
import traceback
import requests

class ExternalScoringException(Exception):

    def __init__(self, message):
        self.message = f"{message}"
        super().__init__(self.message)


class ExternalScoring:
    
    # Constructor
    def __init__(self,season, eventCode, auth):
        self.event = {}
        self.teams = {}
        self.matches = {}
        self.season = season
        self.eventCode = eventCode
        self.auth = auth
        self.requestURI = "http://ftc-api.firstinspires.org/v2.0/"

        self.updateEvent()

        self.updateCount = 0
        self.updateStatusMsg = ""
        self.isUpdating = False

    def getEvent(self):
        return self.event
    
    def getTeams(self):
        return self.teams
    
    def getMatches(self):
        return self.matches
    
    def getUpdateCount(self):
        return self.updateCount
    
    def getUpdateStatusMsg(self):
        return self.updateStatusMsg
    

    def ayncUpdateTeamsMatches(self):

        if not self.isUpdating:

            self.isUpdating = True
            self.updateStatusMsg = "Receiving Data ..."

            try:
                # Get the external data and calculate PowerScore
                self.updateTeamsMatches()
                self.updateStatusMsg = ""
                self.updateCount = self.updateCount + 1


            except requests.exceptions.Timeout:
                # Handle a timeout on the URL
                self.updateStatusMsg = "Timeout: will retry in 15 seconds ..."

            except requests.exceptions.ConnectionError:
                # Handle any other generic connection error
                self.updateStatusMsg = "ConnectionError: will retry in 15 seconds ..."

            self.isUpdating = False




    # Get the data from the extenral system ... includes calculating powerscores
    def updateTeamsMatches(self):

        self.updateTeamsMatchesFromFTC()

        # Now update powerscores
        self.__calculatePowerScore()

        #return (event, teams, matches)
        return
    
    # get event info (this won't change over the course of an event)
    def updateEvent(self):

        r=requests.get(self.requestURI+self.season+'/events?eventCode='+self.eventCode, headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)

        if r.status_code!=200:
            raise ExternalScoringException(f"Could not find event {self.eventCode}.  Request returned {r.status_code}")
        eventJsonResult = r.json()

        self.event['name'] = eventJsonResult['events'][0]['name']
        self.event['divisionCode'] = eventJsonResult['events'][0]['divisionCode']

    # Get data from theorangealliance <== USING THIS AS A TEMPLATE FOR CHANGING TO FTC-EVENTS
    def updateTeamsMatchesFromFTC(self):

        r=requests.get(self.requestURI+self.season+'/schedule/'+self.eventCode+"/qual/hybrid", headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
        matchesJsonResult = r.json()

        r=requests.get(self.requestURI+self.season+'/scores/'+self.eventCode+"/qual", headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
        scoresJsonResult = r.json()

        r=requests.get(self.requestURI+self.season+'/rankings/'+self.eventCode, headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
        rankingsJsonResult = r.json()

        r=requests.get(self.requestURI+self.season+'/teams?eventCode='+self.eventCode, headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
        teamsJsonResult = r.json()

        # there could be 2 pages of teams.  There's a better way to do this, but whatever
        if teamsJsonResult['pageTotal'] > 1:
            r=requests.get(self.requestURI+self.season+'/teams?page=2&eventCode='+self.eventCode, headers={'Content-Type': 'application/json', 'X-Application-Origin': 'PowerScore', 'Authorization': 'Basic '+self.auth},  timeout=5)
            teamsJsonResult2 = r.json()

        # Assemble all the team info from the teams request
        for team in teamsJsonResult['teams']:
            teamNum = team["teamNumber"]
            self.teams[teamNum] = {}
            self.teams[teamNum]['number'] = teamNum
            self.teams[teamNum]['name'] = team["nameShort"]
            self.teams[teamNum]['school'] = ''
            self.teams[teamNum]['city'] = team["city"]
            self.teams[teamNum]['state'] = team["stateProv"]
            self.teams[teamNum]['country'] = team["country"]
            self.teams[teamNum]['rank'] = 1000    # this forces any non-competing teams to the bottom
            self.teams[teamNum]['rp'] = 0
            self.teams[teamNum]['tbp'] = 0
            self.teams[teamNum]['highest'] = 0
            self.teams[teamNum]['matches'] = 0
            self.teams[teamNum]['real_matches'] = 0
            self.teams[teamNum]['allianceScore'] = 0
            self.teams[teamNum]['autoAllianceScore'] = 0
            self.teams[teamNum]['teleAllianceScore'] = 0
            self.teams[teamNum]['endgAllianceScore'] = 0
            self.teams[teamNum]['powerScore'] = 0
            self.teams[teamNum]['autoPowerScore'] = 0
            self.teams[teamNum]['telePowerScore'] = 0
            self.teams[teamNum]['endgPowerScore'] = 0
            self.teams[teamNum]['overallX'] = 0
            self.teams[teamNum]['autoX'] = 0
            self.teams[teamNum]['teleX'] = 0
            self.teams[teamNum]['endgX'] = 0

            if self.teams[teamNum]['name'] == None:
                self.teams[teamNum]['name'] = ""

        # and if there is a second page of teams ...
        if teamsJsonResult['pageTotal'] > 1:
            for team in teamsJsonResult2['teams']:
                teamNum = team["teamNumber"]
                self.teams[teamNum] = {}
                self.teams[teamNum]['number'] = teamNum
                self.teams[teamNum]['name'] = team["nameShort"]
                self.teams[teamNum]['school'] = ''
                self.teams[teamNum]['city'] = team["city"]
                self.teams[teamNum]['state'] = team["stateProv"]
                self.teams[teamNum]['country'] = team["country"]
                self.teams[teamNum]['rank'] = 1000    # this forces any non-competing teams to the bottom
                self.teams[teamNum]['rp'] = 0
                self.teams[teamNum]['tbp'] = 0
                self.teams[teamNum]['highest'] = 0
                self.teams[teamNum]['matches'] = 0
                self.teams[teamNum]['real_matches'] = 0
                self.teams[teamNum]['allianceScore'] = 0
                self.teams[teamNum]['autoAllianceScore'] = 0
                self.teams[teamNum]['teleAllianceScore'] = 0
                self.teams[teamNum]['endgAllianceScore'] = 0
                self.teams[teamNum]['powerScore'] = 0
                self.teams[teamNum]['autoPowerScore'] = 0
                self.teams[teamNum]['telePowerScore'] = 0
                self.teams[teamNum]['endgPowerScore'] = 0
                self.teams[teamNum]['overallX'] = 0
                self.teams[teamNum]['autoX'] = 0
                self.teams[teamNum]['teleX'] = 0
                self.teams[teamNum]['endgX'] = 0

                if self.teams[teamNum]['name'] == None:
                    self.teams[teamNum]['name'] = ""

        # Add in the ranking information
        # ... note that it is possible that a team could show up in rankings, but not in the 
        #     teams for the event.  I think this is when a team doesn't come to a league tournament
        for ranking in rankingsJsonResult['Rankings']:
            teamNum = ranking["teamNumber"]
            if (teamNum in self.teams.keys()):
                self.teams[teamNum]['rank'] = ranking["rank"]
                self.teams[teamNum]['rp'] = ranking["sortOrder1"]
                self.teams[teamNum]['tbp'] = ranking["sortOrder2"]
                self.teams[teamNum]['highest'] = ranking["sortOrder4"]
                self.teams[teamNum]['matches'] = ranking["matchesPlayed"]

        # Now build up the qualifier matches
        #for match in matchesJsonResult['matches']:
        for match in matchesJsonResult['schedule']:

            # Stuff to be verified here.  Is the penalty listed for the correct team?  Should there be a filter
            #  for only played matches?
            if (match["tournamentLevel"]=="QUALIFICATION"):

                matchNumber = match['matchNumber']

                # we have the match, we need to get the scoring object as well
                # If the scoring object isn't found, that means the match hasn't been played
                #
                # NOTE ... this code relies on the sketchy behavior in python that variables in the loop decaration are
                #   scoped to the outer namespace.  So after this loop, the score object will still be in scope once
                #   we break out of the loop
                scoreFound = False
                for score in scoresJsonResult['MatchScores']:
                    if score['matchNumber'] == matchNumber:
                        # matchScore = score;
                        scoreFound = True
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

                # Set up the match and the teams in the match.  Do this whether or not the match as been played.  
                #   For now, assume it has not been played.
                self.matches[matchNumber] = {}
                self.matches[matchNumber]['matchid'] = matchNumber
                self.matches[matchNumber]['played'] = False
                
                self.matches[matchNumber]['alliances'] = {}
                self.matches[matchNumber]['alliances']['red'] = {}
                self.matches[matchNumber]['alliances']['red']['team1'] = red1
                self.matches[matchNumber]['alliances']['red']['team2'] = red2
                self.matches[matchNumber]['alliances']['blue'] = {}
                self.matches[matchNumber]['alliances']['blue']['team1'] = blue1
                self.matches[matchNumber]['alliances']['blue']['team2'] = blue2


                if (scoreFound):
                #if (scoreFound) and matchNumber<18:  # Cute simple hack to simulate an event in progress
                    
                    # Looks like the match has been played (becuase we have a score for it)
                    self.matches[matchNumber]['played'] = True

                    # now find the red scores vs the blue scores
                    redScore = [];
                    blueScore = [];
                    for j in score['alliances']:
                        if j['alliance'] == "Red":
                            redScore = j;
                        elif j['alliance'] == "Blue":
                            blueScore = j;

                    # Assign the points to each team
                    self.matches[matchNumber]['alliances']['red']['total'] = redScore['totalPoints']
                    self.matches[matchNumber]['alliances']['red']['auto'] = redScore['autoPoints']
                    self.matches[matchNumber]['alliances']['red']['teleop'] = redScore['dcPoints']
                    self.matches[matchNumber]['alliances']['red']['endg'] = redScore['endgamePoints']
                    self.matches[matchNumber]['alliances']['red']['pen'] = blueScore['penaltyPointsCommitted']
                    self.matches[matchNumber]['alliances']['blue']['total'] = blueScore['totalPoints']
                    self.matches[matchNumber]['alliances']['blue']['auto'] = blueScore['autoPoints']
                    self.matches[matchNumber]['alliances']['blue']['teleop'] = blueScore['dcPoints']
                    self.matches[matchNumber]['alliances']['blue']['endg'] = blueScore['endgamePoints']
                    self.matches[matchNumber]['alliances']['blue']['pen'] = redScore['penaltyPointsCommitted']

                    # and add to the number of matches we've found
                    self.teams[red1]['real_matches'] += 1
                    self.teams[red2]['real_matches'] += 1
                    self.teams[blue1]['real_matches'] += 1
                    self.teams[blue2]['real_matches'] += 1

        

        ## all done.  We now have fully populated event, teams, and matches objects

        return



    # update the PowerScore data for the teams dict object
    def __calculatePowerScore(self):
        #
        # FINALLY - THIS IS IT!  This is the PowerScore Calculation.  Short and sweet.
        #
        # Does not explicitly return anything.  This updates each teams dictionary object with PowerScores.
        #   This code is separated out only for clarity.
        #

        # Get the alliance scores set up
        allianceScores = {}
        for teamNum in self.teams:
            allianceScores[teamNum] = 0.;
        
        #print("powerscore ...")

        # Now do the allianceScores ... this is needed to "kick off" the calculation
        for matchid in self.matches:

            match = self.matches[matchid]
            if self.matches[matchid]['played']:

                # The math here takes care of the 50-50 split - each team in an alliance get credit for 50% of the scoring (we'll fix that later)
                # There's also a division by the number of matches for each team ... this has the effect of normalizing to the number of matches played

                # overall powerscore
                adjBlueScore = match["alliances"]["blue"]["total"]-match["alliances"]["blue"]["pen"]
                adjRedScore = match["alliances"]["red"]["total"]-match["alliances"]["red"]["pen"]
                self.teams[match["alliances"]["blue"]["team1"]]['allianceScore'] += adjBlueScore/(2.*self.teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                self.teams[match["alliances"]["blue"]["team2"]]['allianceScore'] += adjBlueScore/(2.*self.teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                self.teams[match["alliances"]["red"]["team1"]]['allianceScore'] += adjRedScore/(2.*self.teams[match["alliances"]["red"]["team1"]]['real_matches'])
                self.teams[match["alliances"]["red"]["team2"]]['allianceScore'] += adjRedScore/(2.*self.teams[match["alliances"]["red"]["team2"]]['real_matches'])

                # auto powerscore
                adjBlueScore = match["alliances"]["blue"]["auto"]
                adjRedScore = match["alliances"]["red"]["auto"]
                self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] += adjBlueScore/(2.*self.teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore'] += adjBlueScore/(2.*self.teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] += adjRedScore/(2.*self.teams[match["alliances"]["red"]["team1"]]['real_matches'])
                self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore'] += adjRedScore/(2.*self.teams[match["alliances"]["red"]["team2"]]['real_matches'])

                # teleop powerscore
                adjBlueScore = match["alliances"]["blue"]["teleop"]
                adjRedScore = match["alliances"]["red"]["teleop"]
                self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] += adjBlueScore/(2.*self.teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore'] += adjBlueScore/(2.*self.teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] += adjRedScore/(2.*self.teams[match["alliances"]["red"]["team1"]]['real_matches'])
                self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore'] += adjRedScore/(2.*self.teams[match["alliances"]["red"]["team2"]]['real_matches'])

                # endgame powerscore
                adjBlueScore = match["alliances"]["blue"]["endg"]
                adjRedScore = match["alliances"]["red"]["endg"]
                self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] += adjBlueScore/(2.*self.teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore'] += adjBlueScore/(2.*self.teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] += adjRedScore/(2.*self.teams[match["alliances"]["red"]["team1"]]['real_matches'])
                self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore'] += adjRedScore/(2.*self.teams[match["alliances"]["red"]["team2"]]['real_matches'])

        # Now on to powerScores ...
        # We'll do a 10 round calculation (tends to work fairly well)
        for i in range(1, 10):
    
            # we build up the powerscore for each team, starting from 0
            for teamid in self.teams:
                self.teams[teamid]['powerScore'] = 0
                self.teams[teamid]['autoPowerScore'] = 0
                self.teams[teamid]['telePowerScore'] = 0
                self.teams[teamid]['endgPowerScore'] = 0
                self.teams[teamid]['overallX'] = 0
                self.teams[teamid]['autoX'] = 0
                self.teams[teamid]['teleX'] = 0
                self.teams[teamid]['endgX'] = 0

            # now we loop through each match, and break up the score based on relative scoring performance.
            for matchid in self.matches:
                match = self.matches[matchid]

                if self.matches[matchid]['played']:

                    # Now, split up the scores, not on a 50-50 split like we did the first time, but based on the alliance scores for each team that we just calculated
                    # Again, we're doing the division by the number of matches to normalize to the number of matches played

                    # overall powerscore
                    adjBlueScore = match["alliances"]["blue"]["total"]-match["alliances"]["blue"]["pen"]
                    adjRedScore = match["alliances"]["red"]["total"]-match["alliances"]["red"]["pen"]
                    # if (self.teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['allianceScore']) >0:
                    #     self.teams[match["alliances"]["blue"]["team1"]]['powerScore'] += adjBlueScore * self.teams[match["alliances"]["blue"]["team1"]]['allianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['allianceScore'])* self.teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                    #     self.teams[match["alliances"]["blue"]["team2"]]['powerScore'] += adjBlueScore * self.teams[match["alliances"]["blue"]["team2"]]['allianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['allianceScore'])* self.teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                    # if (self.teams[match["alliances"]["red"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['allianceScore']) >0:
                    #     self.teams[match["alliances"]["red"]["team1"]]['powerScore'] += adjRedScore * self.teams[match["alliances"]["red"]["team1"]]['allianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['allianceScore'])* self.teams[match["alliances"]["red"]["team1"]]['real_matches'])
                    #     self.teams[match["alliances"]["red"]["team2"]]['powerScore'] += adjRedScore * self.teams[match["alliances"]["red"]["team2"]]['allianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['allianceScore'])* self.teams[match["alliances"]["red"]["team2"]]['real_matches'])
                    if (self.teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['allianceScore']) >0:
                        blue1PS = adjBlueScore * self.teams[match["alliances"]["blue"]["team1"]]['allianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['allianceScore']))
                        blue2PS = adjBlueScore * self.teams[match["alliances"]["blue"]["team2"]]['allianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['allianceScore']))
                        self.teams[match["alliances"]["blue"]["team1"]]['powerScore'] += blue1PS
                        self.teams[match["alliances"]["blue"]["team2"]]['powerScore'] += blue2PS
                        if self.teams[match["alliances"]["blue"]["team1"]]['allianceScore'] >0:
                            self.teams[match["alliances"]["blue"]["team1"]]['overallX'] += ((blue1PS - self.teams[match["alliances"]["blue"]["team1"]]['allianceScore']) / self.teams[match["alliances"]["blue"]["team1"]]['allianceScore']) ** 2
                        if self.teams[match["alliances"]["blue"]["team2"]]['allianceScore'] >0:
                            self.teams[match["alliances"]["blue"]["team2"]]['overallX'] += ((blue2PS - self.teams[match["alliances"]["blue"]["team2"]]['allianceScore']) / self.teams[match["alliances"]["blue"]["team2"]]['allianceScore']) ** 2
                    
                    if (self.teams[match["alliances"]["red"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['allianceScore']) >0:
                        red1PS = adjRedScore * self.teams[match["alliances"]["red"]["team1"]]['allianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['allianceScore']))
                        red2PS = adjRedScore * self.teams[match["alliances"]["red"]["team2"]]['allianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['allianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['allianceScore']))
                        self.teams[match["alliances"]["red"]["team1"]]['powerScore'] += red1PS
                        self.teams[match["alliances"]["red"]["team2"]]['powerScore'] += red2PS
                        if self.teams[match["alliances"]["red"]["team1"]]['allianceScore'] >0:
                            self.teams[match["alliances"]["red"]["team1"]]['overallX'] += ((red1PS - self.teams[match["alliances"]["red"]["team1"]]['allianceScore']) / self.teams[match["alliances"]["red"]["team1"]]['allianceScore']) ** 2
                        if self.teams[match["alliances"]["red"]["team2"]]['allianceScore'] >0:
                            self.teams[match["alliances"]["red"]["team2"]]['overallX'] += ((red2PS - self.teams[match["alliances"]["red"]["team2"]]['allianceScore']) / self.teams[match["alliances"]["red"]["team2"]]['allianceScore']) ** 2
                    
                    # auto powerscore
                    adjBlueScore = match["alliances"]["blue"]["auto"]
                    adjRedScore = match["alliances"]["red"]["auto"]
                    # if (self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']) >0:
                    #     self.teams[match["alliances"]["blue"]["team1"]]['autoPowerScore'] += adjBlueScore * self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore'])* self.teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                    #     self.teams[match["alliances"]["blue"]["team2"]]['autoPowerScore'] += adjBlueScore * self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore'])* self.teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                    # if (self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']) >0:
                    #     self.teams[match["alliances"]["red"]["team1"]]['autoPowerScore'] += adjRedScore * self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore'])* self.teams[match["alliances"]["red"]["team1"]]['real_matches'])
                    #     self.teams[match["alliances"]["red"]["team2"]]['autoPowerScore'] += adjRedScore * self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore'])* self.teams[match["alliances"]["red"]["team2"]]['real_matches'])
                    if (self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']) >0:
                        blue1PS = adjBlueScore * self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']))
                        blue2PS = adjBlueScore * self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']))
                        self.teams[match["alliances"]["blue"]["team1"]]['autoPowerScore'] += blue1PS
                        self.teams[match["alliances"]["blue"]["team2"]]['autoPowerScore'] += blue2PS
                        if self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore'] >0:
                            self.teams[match["alliances"]["blue"]["team1"]]['autoX'] += ((blue1PS - self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore']) / self.teams[match["alliances"]["blue"]["team1"]]['autoAllianceScore']) ** 2
                        if self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore'] >0:
                            self.teams[match["alliances"]["blue"]["team2"]]['autoX'] += ((blue2PS - self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']) / self.teams[match["alliances"]["blue"]["team2"]]['autoAllianceScore']) ** 2
                    
                    if (self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']) >0:
                        red1PS = adjRedScore * self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']))
                        red2PS = adjRedScore * self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']))
                        self.teams[match["alliances"]["red"]["team1"]]['autoPowerScore'] += red1PS
                        self.teams[match["alliances"]["red"]["team2"]]['autoPowerScore'] += red2PS
                        if self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore'] >0:
                            self.teams[match["alliances"]["red"]["team1"]]['autoX'] += ((red1PS - self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore']) / self.teams[match["alliances"]["red"]["team1"]]['autoAllianceScore']) ** 2
                        if self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore'] >0:
                            self.teams[match["alliances"]["red"]["team2"]]['autoX'] += ((red2PS - self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']) / self.teams[match["alliances"]["red"]["team2"]]['autoAllianceScore']) ** 2
                    
                    # teleop powerscore
                    adjBlueScore = match["alliances"]["blue"]["teleop"]
                    adjRedScore = match["alliances"]["red"]["teleop"]
                    # if (self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']) >0:
                    #     self.teams[match["alliances"]["blue"]["team1"]]['telePowerScore'] += adjBlueScore * self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore'])* self.teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                    #     self.teams[match["alliances"]["blue"]["team2"]]['telePowerScore'] += adjBlueScore * self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore'])* self.teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                    # if (self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']) >0:
                    #     self.teams[match["alliances"]["red"]["team1"]]['telePowerScore'] += adjRedScore * self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore'])* self.teams[match["alliances"]["red"]["team1"]]['real_matches'])
                    #     self.teams[match["alliances"]["red"]["team2"]]['telePowerScore'] += adjRedScore * self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore'])* self.teams[match["alliances"]["red"]["team2"]]['real_matches'])
                    if (self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']) >0:
                        blue1PS = adjBlueScore * self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']))
                        blue2PS = adjBlueScore * self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']))
                        self.teams[match["alliances"]["blue"]["team1"]]['telePowerScore'] += blue1PS
                        self.teams[match["alliances"]["blue"]["team2"]]['telePowerScore'] += blue2PS
                        if self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore'] >0:
                            self.teams[match["alliances"]["blue"]["team1"]]['teleX'] += ((blue1PS - self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore']) / self.teams[match["alliances"]["blue"]["team1"]]['teleAllianceScore']) ** 2
                        if self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore'] >0:
                            self.teams[match["alliances"]["blue"]["team2"]]['teleX'] += ((blue2PS - self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']) / self.teams[match["alliances"]["blue"]["team2"]]['teleAllianceScore']) ** 2
                    
                    if (self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']) >0:
                        red1PS = adjRedScore * self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']))
                        red2PS = adjRedScore * self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']))
                        self.teams[match["alliances"]["red"]["team1"]]['telePowerScore'] += red1PS
                        self.teams[match["alliances"]["red"]["team2"]]['telePowerScore'] += red2PS
                        if self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore'] >0:
                            self.teams[match["alliances"]["red"]["team1"]]['teleX'] += ((red1PS - self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore']) / self.teams[match["alliances"]["red"]["team1"]]['teleAllianceScore']) ** 2
                        if self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore'] >0:
                            self.teams[match["alliances"]["red"]["team2"]]['teleX'] += ((red2PS - self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']) / self.teams[match["alliances"]["red"]["team2"]]['teleAllianceScore']) ** 2
                    
                    # endgame powerscore
                    adjBlueScore = match["alliances"]["blue"]["endg"]
                    adjRedScore = match["alliances"]["red"]["endg"]
                    # if (self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']) >0:
                    #     self.teams[match["alliances"]["blue"]["team1"]]['endgPowerScore'] += adjBlueScore * self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore'])* self.teams[match["alliances"]["blue"]["team1"]]['real_matches'])
                    #     self.teams[match["alliances"]["blue"]["team2"]]['endgPowerScore'] += adjBlueScore * self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore'])* self.teams[match["alliances"]["blue"]["team2"]]['real_matches'])
                    # if (self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']) >0:
                    #     self.teams[match["alliances"]["red"]["team1"]]['endgPowerScore'] += adjRedScore * self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore'])* self.teams[match["alliances"]["red"]["team1"]]['real_matches'])
                    #     self.teams[match["alliances"]["red"]["team2"]]['endgPowerScore'] += adjRedScore * self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore'])* self.teams[match["alliances"]["red"]["team2"]]['real_matches'])
                    if (self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']) >0:
                        blue1PS = adjBlueScore * self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']))
                        blue2PS = adjBlueScore * self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']/ ((self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']))
                        self.teams[match["alliances"]["blue"]["team1"]]['endgPowerScore'] += blue1PS
                        self.teams[match["alliances"]["blue"]["team2"]]['endgPowerScore'] += blue2PS
                        if self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore'] >0:
                            self.teams[match["alliances"]["blue"]["team1"]]['endgX'] += ((blue1PS - self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore']) / self.teams[match["alliances"]["blue"]["team1"]]['endgAllianceScore']) ** 2
                        if self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore'] >0:
                            self.teams[match["alliances"]["blue"]["team2"]]['endgX'] += ((blue2PS - self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']) / self.teams[match["alliances"]["blue"]["team2"]]['endgAllianceScore']) ** 2
                    
                    if (self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']) >0:
                        red1PS = adjRedScore * self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']))
                        red2PS = adjRedScore * self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']/ ((self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] + self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']))
                        self.teams[match["alliances"]["red"]["team1"]]['endgPowerScore'] += red1PS
                        self.teams[match["alliances"]["red"]["team2"]]['endgPowerScore'] += red2PS
                        if self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore'] >0:
                            self.teams[match["alliances"]["red"]["team1"]]['endgX'] += ((red1PS - self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore']) / self.teams[match["alliances"]["red"]["team1"]]['endgAllianceScore']) ** 2
                        if self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore'] >0:
                            self.teams[match["alliances"]["red"]["team2"]]['endgX'] += ((red2PS - self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']) / self.teams[match["alliances"]["red"]["team2"]]['endgAllianceScore']) ** 2


            # now save the current powerScore as the allianceScore - for use in the next round of calculation if necessary
            for teamid in self.teams:
                if self.teams[teamid]['real_matches'] > 0:
                    self.teams[teamid]['powerScore'] = self.teams[teamid]['powerScore'] / self.teams[teamid]['real_matches']
                    self.teams[teamid]['allianceScore'] = self.teams[teamid]['powerScore']  
                    self.teams[teamid]['autoPowerScore'] = self.teams[teamid]['autoPowerScore'] / self.teams[teamid]['real_matches']
                    self.teams[teamid]['autoAllianceScore'] = self.teams[teamid]['autoPowerScore'] 
                    self.teams[teamid]['telePowerScore'] = self.teams[teamid]['telePowerScore'] / self.teams[teamid]['real_matches']
                    self.teams[teamid]['teleAllianceScore'] = self.teams[teamid]['telePowerScore'] 
                    self.teams[teamid]['endgPowerScore'] = self.teams[teamid]['endgPowerScore'] / self.teams[teamid]['real_matches']
                    self.teams[teamid]['endgAllianceScore'] = self.teams[teamid]['endgPowerScore']    

                    # on the last time only, finish the X calc  
                    if i==9:       
                        self.teams[teamid]['overallX'] = int(100 - (0.5 + 100*sqrt(self.teams[teamid]['overallX'] / self.teams[teamid]['real_matches'])))
                        self.teams[teamid]['autoX'] = int(100 - (0.5 + 100*sqrt(self.teams[teamid]['autoX'] / self.teams[teamid]['real_matches'])))
                        self.teams[teamid]['teleX'] = int(100 - (0.5 + 100*sqrt(self.teams[teamid]['teleX'] / self.teams[teamid]['real_matches'])))
                        self.teams[teamid]['endgX'] = int(100 - (0.5 + 100*sqrt(self.teams[teamid]['endgX'] / self.teams[teamid]['real_matches'])))

            
                
    # all done with the PowerScore calc
    pass
            
