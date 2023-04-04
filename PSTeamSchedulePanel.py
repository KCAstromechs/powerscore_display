import curses
from ExternalScoring import ExternalScoring
from PSPanelInterface import *


# 
# Panel to show the schedule (and results or predicted results) for a team.
#
class PSTeamSchedulePanel:

    def __init__(self, baseWindow: curses.window):
        self.baseWindow = baseWindow

        self.window = None
        self.panel = None

        self.visible = False

    def isVisible(self):
        return self.visible


    def show(self, teamNumber: int, scoringSystem: ExternalScoring):

        teams = scoringSystem.getTeams()
        matches = scoringSystem.getMatches()

        screenHeight, screenWidth = self.baseWindow.getmaxyx()

        # How many matches do we have to show for this team
        # This way of finding matches will bring the entire set of matches to display, whether they have been
        #   played or not
        matchesToShow = {}
        for matchid in matches:
            match = matches[matchid]
            redAlliance = match['alliances']['red']
            blueAlliance = match['alliances']['blue']
            if (redAlliance['team1'] == teamNumber or redAlliance['team2'] == teamNumber or blueAlliance['team1'] == teamNumber or blueAlliance['team2'] == teamNumber ):
                matchesToShow[matchid] = match
                
        # calculate a bunch of dimentions and positionss
        windowHeight = 7 + 3 * len(matchesToShow)
        windowWidth = 136
        windowTop = screenHeight // 2 - windowHeight // 2
        windowLeft = screenWidth // 2 - windowWidth // 2
        
        teamNameNum_y = 1
        teamName_Num_x = 3

        STATS_y = 1
        STATS_x = 60

        TABLE_HEADING_ROW = 4
        MATCH_x = 2
        MATCH_width = 2
        REDALLIANCE_x = 6
        REDALLIANCE_width = 50
        BLUEALLIANCE_x = 58
        BLUEALLIANCE_width = 50
        SCORE_x = 110
        SCORE_width = 23

        MATCHLIST_START_ROW = 6

        #raise Exception(f"{windowHeight} {windowWidth} {windowTop} {windowLeft}")

        # set up the window
        self.window = curses.newwin(windowHeight,windowWidth,windowTop,windowLeft)
        self.panel = curses.panel.new_panel(self.window)
        self.panel.top()

        # draw the outlines
        self.window.box()
        self.window.addch(2,0,curses.ACS_LTEE)
        self.window.hline(2,1,curses.ACS_HLINE,windowWidth-2)
        self.window.addch(2,windowWidth-1,curses.ACS_RTEE)

        # Team number and name
        self.window.addstr(teamNameNum_y, teamName_Num_x, f"{teamNumber} {teams[teamNumber]['name']}")

        # Team stats
        statsText = "RP: {:<4.2f}  TBP: {:<5.1f}  R: {:<2d}  |  PS: {:<5.1f}  A: {:<5.1f}  T: {:<5.1f}  E: {:<5.1f}".format(teams[teamNumber]['rp'],teams[teamNumber]['tbp'],teams[teamNumber]['rank'],teams[teamNumber]['powerScore'],scoringSystem.getTeams()[teamNumber]['autoPowerScore'],scoringSystem.getTeams()[teamNumber]['telePowerScore'],scoringSystem.getTeams()[teamNumber]['endgPowerScore'])
        self.window.addstr(STATS_y,STATS_x,statsText)

        # column headers
        self.window.addstr(TABLE_HEADING_ROW,MATCH_x," M")
        self.window.addstr(TABLE_HEADING_ROW+1,MATCH_x,"-"*MATCH_width)
        self.window.addstr(TABLE_HEADING_ROW,REDALLIANCE_x,"Red Alliance")
        self.window.addstr(TABLE_HEADING_ROW+1,REDALLIANCE_x,"-"*REDALLIANCE_width)
        self.window.addstr(TABLE_HEADING_ROW,BLUEALLIANCE_x,"Blue Alliance")
        self.window.addstr(TABLE_HEADING_ROW+1,BLUEALLIANCE_x,"-"*BLUEALLIANCE_width)
        self.window.addstr(TABLE_HEADING_ROW,SCORE_x,"Score")
        self.window.addstr(TABLE_HEADING_ROW+1,SCORE_x,"-"*SCORE_width)

        matchRow = 0
        # the matchid's in matchesToShow are the same as the matchid's in the matches object
        for matchid in matchesToShow:
            match = matches[matchid]
            redAlliance = match['alliances']['red']
            blueAlliance = match['alliances']['blue']
            if (redAlliance['team1'] == teamNumber or redAlliance['team2'] == teamNumber or blueAlliance['team1'] == teamNumber or blueAlliance['team2'] == teamNumber ):
                self.window.addstr(MATCHLIST_START_ROW+3*matchRow,MATCH_x,"{:>2d}".format(matchid))
                psDisp = "{:.1f}".format(teams[redAlliance['team1']]['powerScore'])
                self.window.addstr(MATCHLIST_START_ROW+3*matchRow,REDALLIANCE_x,f"{redAlliance['team1']} {teams[redAlliance['team1']]['name']} ({psDisp})"[:REDALLIANCE_width])
                psDisp = "{:.1f}".format(teams[blueAlliance['team1']]['powerScore'])
                self.window.addstr(MATCHLIST_START_ROW+3*matchRow,BLUEALLIANCE_x,f"{blueAlliance['team1']} {teams[blueAlliance['team1']]['name']} ({psDisp})"[:BLUEALLIANCE_width])

                psDisp = "{:.1f}".format(teams[redAlliance['team2']]['powerScore'])
                self.window.addstr(MATCHLIST_START_ROW+3*matchRow+1,REDALLIANCE_x,f"{redAlliance['team2']} {teams[redAlliance['team2']]['name']} ({psDisp})"[:REDALLIANCE_width])
                psDisp = "{:.1f}".format(teams[blueAlliance['team2']]['powerScore'])
                self.window.addstr(MATCHLIST_START_ROW+3*matchRow+1,BLUEALLIANCE_x,f"{blueAlliance['team2']} {teams[blueAlliance['team2']]['name']} ({psDisp})"[:BLUEALLIANCE_width])

                if match['played']:
                    redScore = match["alliances"]["red"]["total"]
                    blueScore = match["alliances"]["blue"]["total"]
                    self.window.addstr(MATCHLIST_START_ROW+3*matchRow,SCORE_x,"{:d} - {:d}".format(redScore,blueScore))
                else:
                    # redScore = int(teams[redAlliance['team1']]['powerScore'] + teams[redAlliance['team2']]['powerScore'] + .5)
                    # blueScore = int(teams[blueAlliance['team1']]['powerScore'] + teams[blueAlliance['team2']]['powerScore'] + .5)
                    # self.window.addstr(MATCHLIST_START_ROW+3*matchRow,SCORE_x,"{:d} - {:d} (predicted)".format(redScore,blueScore))
                    pass

                matchRow = matchRow + 1

        self.visible = True



    def hide(self):
        self.panel.hide()
        self.panel = None
        self.window = None
        self.visible = False
    
