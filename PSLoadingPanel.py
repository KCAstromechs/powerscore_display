import curses
from PSPanelInterface import *


# 
# This is the small panel that shows the event name.  Should be always visible.
#
class PSLoadingPanel(PSPanelInterface):

    def __init__(self, baseWindow: curses.window):
        self.baseWindow = baseWindow

        screenHeight, screenWidth = baseWindow.getmaxyx()

        # this goes at the middle of the page
        #super().__init__(2, 100, 10, 10)
        top = screenHeight // 2 - 3
        left = screenWidth // 2 - 50
        width = 100
        super().__init__(5, width, top, left)
        self.window.box()

        msg = "Loading Data ..."


        self.window.addstr(2, width // 2 - len(msg) // 2, msg)

        self.panel.top()

        self.setVisible(True)
    

    def redraw(self):
        self.window.touchwin()
        self.window.refresh()