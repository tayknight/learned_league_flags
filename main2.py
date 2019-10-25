import configparser
import math
import os
import pickle
import re
import requests
import shutil
import textwrap 
import multiprocessing as mp

from html.parser import HTMLParser
from pathlib import Path
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError

import numpy as np
import pandas as pd

LLHEADER = 'https://www.learnedleague.com'
LLALLCSV = 'https://www.learnedleague.com/lgwide.php?{SEASON_NUM}'
LOGINFILE = LLHEADER + '/ucp.php?mode=login'
INPUTDATA = 'logindata.ini'
DOWNLOAD_CSV = False

USE_PLAYERDATA_PICKLES = True
MAX_SEASON = 82

USE_FLAGDATA_PICKLES = True

# If LIMIT_FETCH is try then only LIMIT_FETCH_COUNT number of member
# data will be fetched.
LIMIT_FETCH = True
LIMIT_FETCH_COUNT = 100

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

def get_page_data(url, parser, session=get_session()):
    main_data = session.get(url)
    # Good response?
    if main_data.status_code == 200:
        parser1 = parser
        parser1.feed(main_data.text)
        return parser1.result
    else:
        r = main_data.response
        print(f'{r} for {player}')
        return None

def log_result(retval):
    results.append(retval)
    print('{}'.format(retval))

def fetch_player(session=get_session(), player=None, header=LLHEADER):
    # go fetch their page and get the flag url
    link = player['player_link']
    page = f'{header}{link}'
    flag = get_page_data(page, GetPersonalFlag(), session=session)
    if 'flag_src' in flag:
        player['player_flag'] = flag['flag_src']
    
    return player

if __name__ == "__main__":
    #ll_adapter = HTTPAdapter(max_retries=3)
    session = get_session()
    #session.mount(LLHEADER, ll_adapter)

    # Get and parse scripts/playerdata.js
    try:
        playerdata = session.get(f'{LLHEADER}/scripts/playerdata.js')
    except ConnectionError as ce:
        print(ce)

    if not USE_PLAYERDATA_PICKLES:
        if playerdata.status_code == 200:
            sections = playerdata.text

            regex = r"\(\n(.+?\)+);"
            matches = re.finditer(regex, sections, re.DOTALL)
            match_parse = {
                1: 'playerNames'
                , 2: 'playerLinks'
                , 3: 'playerDescriptions'
                , 4: 'playerFlags'
            }
            
            for match_num, match in enumerate(matches, start=1):
                # 1 group per match (hope this doesn't change):
                for group_num in range(0, len(match.groups())):
                    group_num = group_num + 1
                    if match_parse[match_num] == 'playerNames':
                        raw_player_names = match.group(group_num).split('\n')
                    elif match_parse[match_num] == 'playerLinks':
                        raw_player_links = match.group(group_num).split('\n')
                    elif match_parse[match_num] == 'playerDescriptions':
                        raw_player_descriptions = match.group(group_num).split('\n')
                    elif match_parse[match_num] == 'playerFlags':
                        # as of the end of LL82 this is empty
                        raw_player_flags = match.group(group_num).split('\n')
                    else:
                        print('Couldn\'t find data structures in scripts/playerdata.js')

        players = []
        player_links = []
        player_descriptions = []
        player_flags = []

        for player_name in raw_player_names:
            players.append(player_name.strip('"').strip(',').strip('\''))

        for player_link in raw_player_links:
            player_links.append(player_link.strip('"').strip(',').strip('\''))

        for player_description in raw_player_descriptions:
            player_descriptions.append(player_description.strip('"').strip(',').strip('\''))

        # for player_flag in raw_player_flags:
        #    player_flags.append(player_flag.strip('"').strip(','))

        player_count = len(players)
        player_list = []
        i = 0
        while i < player_count:
            this_player = {}
            player_list.append(
                {
                    'player_name': players[i]
                    , 'player_link': player_links[i]
                    , 'player_description': player_descriptions[i]
                    , 'player_flag': None
                }
            )
            i += 1
        
        with open(f'raw_members.pkl', 'wb') as f:
            pickle.dump(player_list, f)

    with open(f'pickles/raw_members.pkl', 'rb') as f:
        player_list = (pickle.load(f))

    # for each parsed player in playerdata.js...
    if LIMIT_FETCH:
        player_list = player_list[0:LIMIT_FETCH_COUNT]

    if not USE_FLAGDATA_PICKLES:
        results = []
        pool = mp.Pool(processes=4)
        for player in player_list:
            pool.apply_async(fetch_player, args=(session, player, LLHEADER ), callback=log_result)
        pool.close()    
        pool.join()

        # Pickle these objects
        with open(f'pickles/members.pkl', 'wb') as f:
            pickle.dump(results, f)
    
    # load member data
    with open(f'pickles/members.pkl', 'rb') as f:
        member_data = pickle.load(f)

    print('done')