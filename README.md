# PowerScore Display
## tldr;
PowerScore Display is a python based terminal program that retrieves FTC scoring data from remote sources, calculates the current PowerScore for each team, and displays it a *ncurses* based text display.

## Credit
PowerScore was developed by The Astromechs - FTC Team 3409.  

Contact us: http://www.kcastromechs.org or on twitter at @KCAstromechs



## Installation
Python 3 is required.  You will need to install the required libraries.

```shell
pip install -r requirements.txt
```
or
```shell
pip3 install -r requirements.txt
```

VERY IMPORTANT:  This version requires setting an API key in a file called "auth.key" in the same directory as these files.  You'll have to make your won auth.key file.  That file must have a single line with the basic auth string to use.  You can get your own auth key at https://ftc-events.firstinspires.org/services/API.  


## Usage

Single divsio or single event
```shell
python3 pitDisplay.py 2022 USMOKSCMP
```

(2) Multiple divisions.  Up to 4 divisions are supported.

```shell
python3 pitDisplay.py 2022 USMOKSCMP USMOKSSTLNLT USMOKSKCWLT USMOKSKCELT
```




**************************************************************************************
# Release Information
**************************************************************************************

Version 5.0
 * Tons of changes (maybe for the good)
    - There is now only support for ftc-events.firstinspires.org
    - There is now support for up to 4 events
    - ... many more changes ...
 
Version 4.0 (Initial public release)

 * Supported scoring data includes
    - The FTC Scoring System web pages
    - ftcscores.com
    - theorangealliance.net (Note, at the current time theorangealliance has some data challenges)
