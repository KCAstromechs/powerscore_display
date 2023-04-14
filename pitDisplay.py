#! /usr/bin/env python3

'''
PowerScore Display - V5.0

This is primarily intended to run on a Raspberry Pi connected to an HDMI Screen.  This *should* work on any terminal based system where
python with ncurses is supported.  Python3 is required.  Note that this is a command line utility... you will need to run it from the
command line.

For current Raspberry Pi OS installations, you'll need to install libraries (right now only curses).  Use the pip or pip3 tool as appropriate.

    pip3 install -r requirements.txt

If you're on another operating system (Windows, OSX, Ubuntu, etc), you're a little on your own.  If you can get python3 installed,
along with the required python libraries, you should be able to get this working.

As of this version, pulling scores from https://ftc-events.firstinspires.org/ is the only supported system.

----------

This version requires setting an API key in a file called "auth.key".  That file should have a single
line with the basic auth string to use.  You can get your own auth key at https://ftc-events.firstinspires.org/services/API.

----------

Sample Usages:

(1) Single divsion

     python3 pitDisplay.py 2022 USMOKSCMP 
     
(2) Multiple divisions.  Up to 4 divisions are supported.

    python3 pitDisplay.py 2022 USMOKSCMP USMOKSSTLNLT USMOKSKCWLT USMOKSKCELT

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
from datetime import datetime
import time
from ExternalScoring import *
from PSEventNamePanel import *
from PSLoadingPanel import PSLoadingPanel
from PSScoresPanel import PSScoresPanel
from PSSelectEventPanel import PSSelectEventPanel
from PSStatusBarPanel import PSStatusBarPanel
from PSTeamSchedulePanel import PSTeamSchedulePanel

minstdscrHeight = 30
minstdscrWidth = 132

secBetweenAutoUpdates = 300   # in seconds

class stdscrSizeException(Exception):

    def __init__(self, stdscrWidth, stdscrHeight):
        self.message = f"stdscr is not big enough.  It must be at least ({minstdscrWidth},{minstdscrHeight}), but is ({stdscrWidth},{stdscrHeight})"
        super().__init__(self.message)

def setup_curses(stdscr: curses.window):

    # cursor off
    curses.curs_set(0)

    # really reduce the esc delay
    curses.set_escdelay(10)

    # Redefine yellow to be closer to the safety green for the Astromechs
    curses.init_color(curses.COLOR_YELLOW, 680,1000,0)

    # Start colors in curses, set up color pairs
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Inverted
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Yellow
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Red
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Green

    # Nodelay mode ... getch won't block
    stdscr.nodelay(1)

    pass


def drawBaseScreen(stdscr: curses.window):

    screenHeight, screenWidth = stdscr.getmaxyx()

    rightHeadingStartColumn = screenWidth - 96
    leftStartColumn = 2

    bigHeadLine1 = "  _____   _____  _  _  _ _______  ______ _______ _______  _____   ______ _______"
    bigHeadLine2 = " |_____] |     | |  |  | |______ |_____/ |______ |       |     | |_____/ |______"
    bigHeadLine3 = " |       |_____| |__|__| |______ |    \_ ______| |_____  |_____| |    \_ |______ v5"                                    

    descrLine1 = "Developed by The Astromechs - FTC Team 3409   http://www.kcastromechs.org"
    # descrLine2 = ""
    # descrLine3 = "PowerScore is a scouting tool that statistically measures the offensive performance of"
    # descrLine4 = "FTC Teams at Tournaments.  PowerScore is based on team scoring.  It differs from the FTC"
    # descrLine5 = "Qualification/Rating points in that it measures teams by their scoring only, not wins/losses."

    stdscr.attron(curses.color_pair(2))
    stdscr.addstr(0, leftStartColumn, bigHeadLine1.encode("utf-8"))
    stdscr.addstr(1, leftStartColumn, bigHeadLine2.encode("utf-8"))
    stdscr.addstr(2, leftStartColumn, bigHeadLine3.encode("utf-8"))
    stdscr.attroff(curses.color_pair(2))

    stdscr.addstr(0, rightHeadingStartColumn, descrLine1)
    # stdscr.addstr(1, rightHeadingStartColumn, descrLine2)
    # stdscr.addstr(2, rightHeadingStartColumn, descrLine3)
    # stdscr.addstr(3, rightHeadingStartColumn, descrLine4)
    # stdscr.addstr(4, rightHeadingStartColumn, descrLine5)

    pass


def ui_main(stdscr: curses.window, scoringSystems: list[ExternalScoring]):

    scoringSystemIndex = 0

    screenHeight, screenWidth = stdscr.getmaxyx()
    if screenHeight < minstdscrHeight or screenWidth < minstdscrWidth:
        raise stdscrSizeException(screenWidth,screenHeight)
    
    # set all of the curses settings to our liking
    setup_curses(stdscr)

    # draw the base screen
    drawBaseScreen(stdscr)

    eventNamePanel = PSEventNamePanel(stdscr)
    eventNamePanel.redraw(scoringSystems[scoringSystemIndex])

    statusBar = PSStatusBarPanel(stdscr)

    psScoresPanel = PSScoresPanel(stdscr)
    # psScoresPanel.redraw(scoringSystems[scoringSystemIndex])

    psLoadingPanel = PSLoadingPanel(stdscr)
    psLoadingPanel.setVisible(True)

    psSelectEventPanel = PSSelectEventPanel(stdscr, scoringSystems)
    psSelectEventPanel.setVisible(False)

    psTeamSchedulePanel = PSTeamSchedulePanel(stdscr)

    curses.panel.update_panels()
    curses.doupdate()
    
    # Set updateRequested to true to force an immediate update
    updateRequested = True

    nextUpdateTimeSec = int(time.time()) + secBetweenAutoUpdates

    # Main run loop
    while 1:
        # Non-blocking (becuase of nodelay)
        keyevent = stdscr.getch()

        # q to quit
        if keyevent == ord("q"):
            # quit and break out of the main loop
            break

        # r to force a data refresh
        if keyevent == ord("r"):
            updateRequested = True

        # esc key to pop back and select a different event
        if keyevent == 27:
            if ( (not psSelectEventPanel.isVisible()) and (not psTeamSchedulePanel.isVisible()) ):
                # not showing the select event or the team schedule ... show the select event
                psSelectEventPanel.setVisible(True)
                psSelectEventPanel.setSelectedIndex(scoringSystemIndex)
                psSelectEventPanel.redraw()
                psScoresPanel.setVisible(False)
                pass
            elif(psSelectEventPanel.isVisible()):
                 # the user hit escape when the seletion panel was visible (meaning they're not changing the event)
                 psSelectEventPanel.setVisible(False)
                 psScoresPanel.setVisible(True)
                 pass
            elif(psTeamSchedulePanel.isVisible()):
                psTeamSchedulePanel.hide()

            curses.panel.update_panels()
            curses.doupdate()


        # enter key pressed ... decide what if anything to do
        if keyevent == 10:

            if psSelectEventPanel.isVisible():
                # Select event is visible ... change to the selected event
                psSelectEventPanel.setVisible(False)
                scoringSystemIndex = psSelectEventPanel.getSelectedIndex()
                eventNamePanel.redraw(scoringSystems[scoringSystemIndex])
                psScoresPanel.clear()
                psScoresPanel.setVisible(True)
                updateRequested = True
            elif ( (not psLoadingPanel.isVisible()) and (not psTeamSchedulePanel.isVisible()) ):
                # OK to show the team schedule
                if (psScoresPanel.getHighlightTeamNum() != 0):
                    # but only if a team is really selected
                    psTeamSchedulePanel.show(psScoresPanel.getHighlightTeamNum(),scoringSystems[scoringSystemIndex])
                    pass

                pass

            curses.panel.update_panels()
            curses.doupdate()

        # super secret way to see a team display with prediction turned on
        if keyevent == ord('p'):

            if ( (not psLoadingPanel.isVisible()) and (not psTeamSchedulePanel.isVisible()) ):
                # OK to show the team schedule
                if (psScoresPanel.getHighlightTeamNum() != 0):
                    # but only if a team is really selected
                    psTeamSchedulePanel.show(psScoresPanel.getHighlightTeamNum(),scoringSystems[scoringSystemIndex], True)
                    pass

                pass

            curses.panel.update_panels()
            curses.doupdate()

        # down arrow
        if keyevent == 258:
            if psScoresPanel.isVisible():
                psScoresPanel.changeHighlightTeamRow(1)
                psScoresPanel.redraw(scoringSystems[scoringSystemIndex])
            if psSelectEventPanel.isVisible():
                psSelectEventPanel.changeSelectedIndex(1)
                psSelectEventPanel.redraw()
            curses.panel.update_panels()
            curses.doupdate()

        # up arrow
        if keyevent == 259:
            if psScoresPanel.isVisible():
                psScoresPanel.changeHighlightTeamRow(-1)
                psScoresPanel.redraw(scoringSystems[scoringSystemIndex])
            if psSelectEventPanel.isVisible():
                psSelectEventPanel.changeSelectedIndex(-1)
                psSelectEventPanel.redraw()
            curses.panel.update_panels()
            curses.doupdate()

        # left arrow
        if keyevent == 260:
            if psScoresPanel.isVisible():
                psScoresPanel.changeSortColumn(-1)
                psScoresPanel.redraw(scoringSystems[scoringSystemIndex])
            curses.panel.update_panels()
            curses.doupdate()

        # right arrow
        if keyevent == 261:
            if psScoresPanel.isVisible():
                psScoresPanel.changeSortColumn(1)
                psScoresPanel.redraw(scoringSystems[scoringSystemIndex])
            curses.panel.update_panels()
            curses.doupdate()

        # Has the timer run out?  If so, do an update of the data
        if int(time.time() >= nextUpdateTimeSec):
            updateRequested=True

         # Do we need to do an update?  Only update if the psScoresPanel is visible.  Might not be if we're
         #   selecting a different event
        if updateRequested and psScoresPanel.isVisible():



            # Tell the user we're updating
            psLoadingPanel.setVisible(True)

            # Tell the screen it is now ok to refresh
            curses.panel.update_panels()
            curses.doupdate()

            try:
                # Get the external data and calculate PowerScore
                scoringSystems[scoringSystemIndex].updateTeamsMatches()

                # Update the data on the page
                psScoresPanel.redraw(scoringSystems[scoringSystemIndex])

                statusBar.redraw("Last Update: "+datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))

            except requests.exceptions.Timeout:
                # Handle a timeout on the URL
                statusBar.redraw("Timeout at "+datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))

            except requests.exceptions.ConnectionError:
                # Handle any other generic connection error
                statusBar.redraw("ConnectionError at "+datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))

            psLoadingPanel.setVisible(False)

            updateRequested = False
            nextUpdateTimeSec= time.time() + secBetweenAutoUpdates

            # Tell the screen it is now ok to refresh
            curses.panel.update_panels()
            curses.doupdate()

        # Wait for 0.1 seconds before the next time through the loop
        time.sleep(.1)

    pass

# check for an internet connection
def network_up():
    try:
        r=requests.get('https://ftc-events.firstinspires.org/',  timeout=15)
        return True
    except: 
        return False

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

    # read the api key from the expected file.
    try:
        f = open("auth.key", "r")
        auth_key = f.readline()
    except Exception as x:
        print("Error reading expected auth.key file")
        exit()

    # wait for a network connection
    while(not network_up()):
        print("Network is unavailable ... will try again in 10 seconds")
        time.sleep(10)

    try:
        # check and set up the scoring system objects.  
        scoringSystems = []
        scoringSystems.append(ExternalScoring(args.season, args.event, auth_key))
        if (args.event2!=""):
            scoringSystems.append(ExternalScoring(args.season, args.event2, auth_key))
        if (args.event3!=""):
            scoringSystems.append(ExternalScoring(args.season, args.event3, auth_key))
        if (args.event4!=""):
            scoringSystems.append(ExternalScoring(args.season, args.event4, auth_key))

        # ready to try and set up the main UI
        curses.wrapper(ui_main, scoringSystems)
    except stdscrSizeException as s:
        print()
        print(s)
        print()

    except ExternalScoringException as s:
        print()
        print(s)
        print()


# Kick everything off in a nice way
if __name__ == "__main__":
    main()
