import configparser
import math
import os
import pickle
import requests
import shutil
import textwrap 
import multiprocessing as mp

from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import pandas as pd

LLHEADER = 'https://www.learnedleague.com'
LLALLCSV = 'https://www.learnedleague.com/lgwide.php?{SEASON_NUM}'
LOGINFILE = LLHEADER + '/ucp.php?mode=login'
INPUTDATA = 'logindata.ini'
DOWNLOAD_CSV = False
MAX_SEASON = 82

class GetPersonalFlag(HTMLParser):
    """
    Parse rundle page to get player's flag
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.result = {}
        self.inhref = False
        self.temp_member_id = ''
        self.found_person = False

    def handle_starttag(self, tag, attrs):
        """
        Find player reference
        """

        # Stop processing tags if person's flag info found
        if self.found_person:
            return

        if tag == 'a':
            for apt in attrs:
                if apt[0] == 'href':
                    if apt[1].startswith('/profiles.php'):
                        tindx = apt[1].find('?') + 1
                        # Temporarily store this member_name.
                        self.temp_member_id = apt[1][tindx:]

                        # Remember that we are processing within a href tag.
                        self.inhref = True
        
        if tag == 'img':
            # If we are processing with the href tag that has already been processed.
            if self.inhref:
                if attrs[0][0] == 'src':
                    if attrs[1][0] == 'width':
                        # If the flag image is XL sized... The user's own flag should
                        # be the only XL flag on their own page.
                        if attrs[1][1] == '154':
                            if attrs[4][0] == 'class':
                                if attrs[4][1] == 'flagimg':
                                    # Set the output member_name to the temp member_name set above.
                                    self.result['member_id'] = self.temp_member_id
                                    self.result['member_name'] = attrs[3][1]

                                    # Set the output flag source.
                                    self.result['flag_src'] = attrs[0][1]

                                    # Set the found person so no more tags are processed.
                                    self.found_person = True

def get_session():
    """
    Read an ini file, establish a login session

    Input:
        inifile -- name of local ini file with control information

    Returns: logged in requests session to be used in later operations
    """
    config = configparser.ConfigParser()
    config.read(INPUTDATA)
    payload = {'login': 'Login'}
    for attrib in ['username', 'password']:
        payload[attrib] = config['DEFAULT'][attrib]
    ses1 = requests.Session()
    try:
        loginfile = config['DEFAULT']['loginfile']
    except KeyError:
        loginfile = LOGINFILE
    ses1.post(loginfile, data=payload)
    return ses1

def get_season_csv(session=get_session(), season=MAX_SEASON):
    """
    Read a csv file pointed to by a url.  Return a list of lines.  Each
    line is a list of fields.
    """
    main_data = session.get(LLALLCSV.format(SEASON_NUM=season))
    retval = main_data.content
    #flines = main_data.text.strip().split('\n')
    #retval = []
    #for peep in flines[1:]:
    #    newpeep = peep.split(',')
    #    retval.append(newpeep[1:])

    if retval[0:16] != b'<b>[phpBB Debug]':
        with open(Path('csv', 'season_{}.csv'.format(season)), 'wb') as f:
            f.write(retval)

    return 'season_{}.csv'.format(season)

def read_csv(season=MAX_SEASON):
    players_df = pd.read_csv(Path('csv', 'season_{}.csv'.format(season))
        , sep=','
        , encoding = "ISO-8859-1"
    )
    return players_df

def get_page_data(url, parser, session=get_session()):
    main_data = session.get(url)
    # Good response?
    if main_data.status_code == 200:
        parser1 = parser
        parser1.feed(main_data.text)
        parser1.result
    else:
        r = main_data.response
        print(f'{r} for {player}')

session = get_session()

# The past season's CSV shouldn't change. After they've been downloaded
# there should be any reason to download them again.
if DOWNLOAD_CSV:
    season_num = 1
    while season_num <= MAX_SEASON:
        csv = get_season_csv(session=session, season=season_num)
        season_num += 1

# Process the player from the CSV files.
# create empty dataframe to hold the list of players from the CSV files.
all_players = []

# reset season_num
season_num = 1
while season_num <= MAX_SEASON:
    # Not every season has a CSV file.
    if Path('csv', 'season_{}.csv'.format(season_num)).exists():
        df = read_csv(season=season_num)
        if 'Player' in df.columns:
            # Extract only the Player column from the dataframe and append
            # it to the list created above.
            all_players.extend(df['Player'].tolist())
    season_num += 1

# Get a unique list of player names.
unique_players = np.unique(np.array(all_players))

# for each player in unique players...
limit = 100
i = 0
for player in unique_players:
    if i < 100:
        # go fetch the player's profile page.
        page = "%s/profiles.php?%s" % (LLHEADER, player.lower())
        person = GetPersonalFlag(person)
        i += 1

print(len(unique_players))