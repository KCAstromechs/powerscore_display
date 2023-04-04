import curses
from PSPanelInterface import *


# 
# This is the small panel that shows the event name.  Should be always visible.
#
class PSStatusBarPanel(PSPanelInterface):

    def __init__(self, baseWindow: curses.window):
        self.baseWindow = baseWindow

        screenHeight, screenWidth = baseWindow.getmaxyx()

        # this goes on the bottom line of the page
        #super().__init__(2, 100, 10, 10)
        super().__init__(2, screenWidth, screenHeight - 2, 0)

        self.setVisible(True)
    

    def redraw(self, message):
        
        self.window.addstr(1, 0, message)
        self.window.refresh()