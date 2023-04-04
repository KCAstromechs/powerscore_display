import curses
from PSPanelInterface import *

from ExternalScoring import ExternalScoring


# 
# This is the small panel that shows the event name.  Should be always visible.
#
class PSEventNamePanel(PSPanelInterface):

    def __init__(self, baseWindow: curses.window):
        self.baseWindow = baseWindow

        screenHeight, screenWidth = baseWindow.getmaxyx()

        # This goes on lines 3-5, 96 chars in from the left side
        super().__init__(3, 96, 3, screenWidth - 96)

        self.setVisible(True)
    

    def redraw(self, scoringSystem: ExternalScoring):
        
        self.window.addstr(1, 0, scoringSystem.event['name'])

