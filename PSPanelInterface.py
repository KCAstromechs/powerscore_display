from abc import abstractmethod
import curses
from curses import panel


class PSPanelInterface():

    #
    # All windows/panels will get the events, teams, matches
    #
    def __init__(self, y, x, height, width):

        self.window = curses.newwin(y,x,height,width)
        self.panel = curses.panel.new_panel(self.window)
        self.panel.top()

    def setVisible(self, v):
        if v:
            self.panel.show()
        else:
            self.panel.hide()
            
        self.window.touchwin()
        #self.window.refresh()

    def isVisible(self):
        return (not self.panel.hidden())

