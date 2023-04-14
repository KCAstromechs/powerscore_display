import curses
from PSPanelInterface import *

from ExternalScoring import ExternalScoring


# 
# This is the main powerscore panel.  Should always be visible
#
class PSScoresPanel(PSPanelInterface):

    def __init__(self, baseWindow: curses.window):
        self.baseWindow = baseWindow

        screenHeight, screenWidth = baseWindow.getmaxyx()

        # This starts on line 6, height to leave one row for status at the bottom, full width
        self.windowHeight = screenHeight - 5
        self.windowWidth = screenWidth
        
        super().__init__(self.windowHeight, self.windowWidth, 4, 0)
        self.setVisible(True)

        # Calculating all the important positions

        # Team position is measured from the left side, fixed columns.  The team name is the stretch column
        self.teamNumber_col = 2    
        self.teamNumber_width = 5                                       
        self.teamName_col = 8
        self.teamName_width = self.windowWidth - 141 - 2 - 8
        self.teamUnderline_width = self.teamName_width + self.teamNumber_width + 1

        self.city_col = self.windowWidth - 141
        self.city_width = 141 - 123 - 2

        self.state_col = self.windowWidth - 123
        self.state_width = 123 - 111 - 2

        self.country_col = self.windowWidth - 111
        self.country_width = 111 - 93 - 2

        self.overallPS_col = self.windowWidth - 93
        self.overallPS_width = 7

        self.autoPS_col = self.windowWidth - 82
        self.autoPS_width = 7

        self.teleopPS_col = self.windowWidth - 71
        self.teleopPS_width = 7

        self.endgamePS_col = self.windowWidth - 60
        self.endgamePS_width = 7

        self.x_col = self.windowWidth - 49
        self.x_width = 11

        self.rank_col = self.windowWidth - 35
        self.rank_width = 3
        self.rankUnderline_width = 24

        self.rp_col = self.windowWidth - 30
        self.rp_width = 4

        self.tbp_col = self.windowWidth - 25
        self.tbp_width = 5

        self.highest_col = self.windowWidth - 18
        self.highest_width = 7

        self.matches_col = self.windowWidth - 9
        self.matches_width = 7

        self.sortColumn = 1
        self.sortColumn_count = 6

        self.highlightTeamRow = 0
        self.highlightTeamNumber = 0
        self.maxTeamRows = self.windowHeight - 2


    def clear(self):
        self.window.clear()

    def changeSortColumn(self, delta):
        self.sortColumn = (self.sortColumn + delta) % self.sortColumn_count

    def changeHighlightTeamRow(self, delta):
        self.highlightTeamRow = (self.highlightTeamRow + delta) % self.maxTeamRows

    def getHighlightTeamNum(self):
        return self.highlightTeamNumber
            
    def redraw(self, scoringSystem: ExternalScoring):
        
        self.drawColumnTitles()
        self.drawSortUnderline()
        self.drawTable(scoringSystem)


    def drawSortUnderline(self):

        self.window.addstr(1,0, " " * self.windowWidth)
        if self.sortColumn == 0:
            self.window.addstr(1,self.teamNumber_col, "+" * self.teamUnderline_width)
        elif self.sortColumn == 1:
            self.window.addstr(1,self.overallPS_col, "+" * self.overallPS_width)
        elif self.sortColumn == 2:
            self.window.addstr(1,self.autoPS_col, "+" * self.autoPS_width)
        elif self.sortColumn == 3:
            self.window.addstr(1,self.teleopPS_col, "+" * self.teleopPS_width)
        elif self.sortColumn == 4:
            self.window.addstr(1,self.endgamePS_col, "+" * self.endgamePS_width)
        elif self.sortColumn == 5:
            self.window.addstr(1,self.rank_col, "+" * self.rankUnderline_width)


    def drawColumnTitles(self):
        self.window.addstr(0,self.teamNumber_col,"TEAM")
        self.window.addstr(0,self.city_col,"City")
        self.window.addstr(0,self.state_col,"State/Prov")
        self.window.addstr(0,self.country_col,"Country")
        self.window.addstr(0,self.overallPS_col,"Overall")
        self.window.addstr(0,self.autoPS_col,"   Auto")
        self.window.addstr(0,self.teleopPS_col," Teleop")
        self.window.addstr(0,self.endgamePS_col,"Endgame")
        self.window.addstr(0,self.x_col,"Ox/Ax/Tx/Ex")
        self.window.addstr(0,self.rank_col,"Rank")
        self.window.addstr(0,self.rp_col,"RP")
        self.window.addstr(0,self.tbp_col,"TBP")
        self.window.addstr(0,self.highest_col,"Highest")
        self.window.addstr(0,self.matches_col,"Matches")


    def drawTable(self, scoringSystem: ExternalScoring):

        teams = scoringSystem.getTeams()
        self.highlightTeamNumber = 0

        # Ensure that we've cleared out any possible old data
        for i in range(2,self.windowHeight-2):
            self.window.addstr(i,0," "*(self.windowWidth-1))
        
        line = 1

        #construct the sorted list
        s = []
        if self.sortColumn == 0:
            s = sorted(teams, key = lambda r: teams[r]["number"], reverse=False)
        elif self.sortColumn == 1:
            s = sorted(teams, key = lambda r: teams[r]["powerScore"], reverse=True)
        elif self.sortColumn == 2:
            s = sorted(teams, key = lambda r: teams[r]["autoPowerScore"], reverse=True)
        elif self.sortColumn == 3:
            s = sorted(teams, key = lambda r: teams[r]["telePowerScore"], reverse=True)
        elif self.sortColumn == 4:
            s = sorted(teams, key = lambda r: teams[r]["endgPowerScore"], reverse=True)
        elif self.sortColumn == 5:
            s = sorted(teams, key = lambda r: teams[r]["rank"], reverse=False)

        if self.highlightTeamRow > len(teams):
            self.highlightTeamRow = 0

        for teamNum in s:
            team = teams[teamNum]
            line+=1

            if line < self.windowHeight:

                if (line - 1) == self.highlightTeamRow:
                    self.window.attron(curses.color_pair(2))
                    self.highlightTeamNumber = teamNum

                self.window.addstr(line,self.teamNumber_col,"{:>5}".format(teamNum))
                self.window.addstr(line,self.teamName_col,team["name"][0:self.teamName_width])
                self.window.addstr(line,self.city_col,team["city"][0:self.city_width])
                self.window.addstr(line,self.state_col,team["state"][0:self.state_width])
                self.window.addstr(line,self.country_col,team["country"][0:self.country_width])
                self.window.addstr(line,self.overallPS_col,"{:7.2f}".format(team["powerScore"]))
                self.window.addstr(line,self.autoPS_col,"{:7.2f}".format(team["autoPowerScore"]))
                self.window.addstr(line,self.teleopPS_col,"{:7.2f}".format(team["telePowerScore"]))
                self.window.addstr(line,self.endgamePS_col,"{:7.2f}".format(team["endgPowerScore"]))
                self.window.addstr(line,self.x_col,"{:>2d}/{:>2d}/{:>2d}/{:>2d}".format(team["overallX"],team["autoX"],team["teleX"],team["endgX"]))
                self.window.addstr(line,self.rank_col,"{:>3}".format(team["rank"]))
                self.window.addstr(line,self.rp_col,"{:5.2f}".format(team["rp"]))
                self.window.addstr(line,self.tbp_col,"{:6.2f}".format(team["tbp"]))
                self.window.addstr(line,self.highest_col,"{:>7d}".format(int(team["highest"])))
                self.window.addstr(line,self.matches_col,"{:>7}".format(team["real_matches"]))

                self.window.attroff(curses.color_pair(2))




