import curses
from ExternalScoring import ExternalScoring
from PSPanelInterface import *


# 
# This is the small panel that shows the event name.  Should be always visible.
#
class PSSelectEventPanel(PSPanelInterface):

    def __init__(self, baseWindow: curses.window, scoringSystems: list[ExternalScoring]):
        self.baseWindow = baseWindow

        screenHeight, screenWidth = baseWindow.getmaxyx()

        self.scoringSystems = scoringSystems

        self.selectedIndex = 0

        # this goes on the middle of the page
        numEvents = len(self.scoringSystems)
        
        top = screenHeight // 2 - numEvents // 2 - 2
        left = screenWidth // 2 - 50
        width = 120
        super().__init__(8, width, top, left)
        #self.window.box()
        #self.window.addstr(0,width // 2 - 8, " Select Event ")
        self.clearBox()

        self.panel.top()

        self.setVisible(True)

    def changeSelectedIndex(self, delta):
        numEvents = len(self.scoringSystems)
        self.selectedIndex = (delta + self.selectedIndex) % numEvents

    def setSelectedIndex(self,idx):
        self.selectedIndex = idx

    def getSelectedIndex(self):
        return self.selectedIndex
    
    def clearBox(self):
        height, width = self.window.getmaxyx()
        self.window.erase()
        self.window.box()
        self.window.addstr(0,width // 2 - 8, " Select Event ")

    def redraw(self):

        self.clearBox()

        numEvents = len(self.scoringSystems)

        teamIndex = 0
        for scoringSystem in self.scoringSystems:
            line = teamIndex + 2

            if teamIndex == self.selectedIndex:
                self.window.attron(curses.color_pair(2))
            self.window.addstr(line, 10, scoringSystem.event['name'])
            self.window.attroff(curses.color_pair(2))

            teamIndex = teamIndex + 1


        #self.window.touchwin()
        #self.window.refresh()