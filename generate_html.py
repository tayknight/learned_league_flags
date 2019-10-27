import configparser
import math
import os
import pickle
import re
import requests
import shutil
import sys
import textwrap

from html.parser import HTMLParser
from multiprocessing.pool import ThreadPool
from pathlib import Path
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError
from time import time, sleep

import numpy as np

LLHEADER = 'https://www.learnedleague.com'
LLALLCSV = 'https://www.learnedleague.com/lgwide.php?{SEASON_NUM}'
LOGINFILE = LLHEADER + '/ucp.php?mode=login'
INPUTDATA = 'logindata.ini'

# Fetch the playerdata.js file from learnedleague.com.
# This is list from which the html is built.
# The piece of code below that pays attention to this
# switch runs quickly.
FETCH_PLAYERDATA = True

# As of October 2019 the playerdata.js file does not contain
# the source for flag images. These URLs can't be determined
# from the member's name. This switch controls whether the
# code will
# 1. Load each member's page.
# 2. Parse that page looking for the member's flag.
# This process takes some time since it has to load each member's
# member page.
FETCH_FLAGDATA = True

# If the FETCH_FLAGDATA switch is True then this swich controls
# how many sets of member data will be loaded before the code
# pauses.
FETCH_BATCH = 1000

# How many seconds to pause after each batch.
FETCH_SLEEP = 3

# If LIMIT_FETCH is true then only LIMIT_FETCH_COUNT number of member
# data will be fetched. This is primarily used for testing instead
# of loading the X0,000 member records.
LIMIT_FETCH = False
LIMIT_FETCH_COUNT = 163

# How many pages of member sets should be output in the HTML menus and pages.
NUMBER_OF_PAGES = 20

class GetPersonalFlag(HTMLParser):
    """
    Parse rundle page to get player's flag.
    This code is based on the llama_slobber parsing functions.
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

    Returns: logged in requests session to be used in later operations.
    This code is based on llama_slobber session get_function().
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
    """
    Gets and parse an HTML page.
    """
    main_data = session.get(url)
    # Good response?
    if main_data.status_code == 200:
        parser1 = parser
        parser1.feed(main_data.text)
        return parser1.result
    else:
        r = main_data.response
        print(f'Problem parsing {url}.')
        return None

def log_result(retval):
    results.append(retval)
    print('{}'.format(retval))

def fetch_player(session=get_session(), player=None, header=LLHEADER):
    '''
    Fetch a player's member page and the URL for the XL flag.
    '''
    link = player['player_link']
    page = f'{header}{link}'
    flag = get_page_data(page, GetPersonalFlag(), session=session)
    if 'flag_src' in flag:
        player['player_flag'] = flag['flag_src']

    return player

if __name__ == "__main__":
    session = get_session()

    # Do we need to fetch the playerdata.js file from learnedleague.com?
    if FETCH_PLAYERDATA == True:
        # Get and parse scripts/playerdata.js
        try:
            playerdata = session.get(f'{LLHEADER}/scripts/playerdata.js')
        except ConnectionError as ce:
            print(ce)
        if playerdata.status_code == 200:
            playerdata.encoding = 'utf-8'
            sections = playerdata.text

            # playerdata.js file is javascript that powers the search functionality
            # when logged into learnedleague.com. As of the end of LL82 the file
            # three javascript objects of identical length. We need to conver these to
            # python objects.
            # Match starts on the 'var' line in the javascript...
            # var playerNames = new Array(
            # ...
            # "ZylaR");
            # example row we're looing for
            # PlayerNames:
            # # 'WyattW',
            # PlayerLinks:
            # # '/profiles.php?34333',
            # PlayerDescriptions',
            # # "Abilene, Texas",
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

        # Clean up the elements matched.
        # TODO: Clean these up in the regex.
        for player_name in raw_player_names:
            players.append(player_name.replace('"', '').replace(',', '').replace('\'', ''))

        for player_link in raw_player_links:
            player_links.append(player_link.replace('"', '').replace(',', '').replace('\'', ''))

        for player_description in raw_player_descriptions:
            player_descriptions.append(player_description.replace('"', '').replace(',', '').replace('\'', ''))

        player_count = len(players)

        # Create an object we'll use to consolidate the 3 javascript objects
        # into one list of dictionaries.
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

        # Pickle the player_list.
        with open(Path('pickles', 'raw_members.pkl'), 'wb') as f:
            pickle.dump(player_list, f)

    # The list of users will get loaded from the picked file. Thus the
    # point of the FETCH_PLAYERDATA swtich. If FETCH_PLAYERDATA is false
    # we can still work with the data without having to fetch and parse the
    # playerdata.js file (even though this process is quick.)

    # FETCH_PLAYERDATA must be run as True at least once to create the pickle'd object.
    if Path('pickles', 'raw_members.pkl').is_file():
        with open('pickles/raw_members.pkl', 'rb') as f:
            player_list = (pickle.load(f))
    else:
        print('pickles/raw_members.pkl not found. Change FETCH_PLAYERDATA to True.')
        sys.exit(0)

    # If the LIMIT_FETCH switch is set then we only need the first LIMIT_FETCH_COUNT
    # players.
    if LIMIT_FETCH:
        player_list = player_list[0:LIMIT_FETCH_COUNT]

    # As of the end of LL82 the playerdata.js file does not contain the URL of the member's
    # flag (although there is a placeholder for it.)
    # Do we need to fetch the flag URL for each member?
    if FETCH_FLAGDATA == True:
        # results will hold the URL for each member where a flag is found.
        results = []

        # small_results will hold the results for an individual batch.
        small_results = []

        # When did the first batch start?
        ts = time()

        i = 0
        small_list = []

        # for logging
        batch_count = 1

        # How many members in each batch?
        total_batches = math.floor((len(player_list) / FETCH_BATCH))

        # Run through all the players loaded from the pickled user object.
        while i < len(player_list):
            # add this player to the small_list.
            small_list.append(player_list[i])

            # If the progress into the small_list == the number to fetch in a batch
            if len(small_list) % FETCH_BATCH == 0:

                # Set up a python multiprocessing threadpool.
                pool = ThreadPool(5)

                # For each player in the small batch
                # pass in the player object to fetch and parse the member page.
                # The member flag URL, if found, will be populated in the player object.
                for player in small_list:
                    small_results.append(pool.apply_async(fetch_player, args=(session, player, LLHEADER )))

                pool.close()
                pool.join()

                # for all players in the small_results append that player into the larger list.
                for r in small_results:
                    results.append(r.get())

                # How long did this batch take?
                this_batch = (time() - ts)
                print(f'Batch: {batch_count} of {total_batches}. Fetching {FETCH_BATCH} image URLs in: {this_batch}')
                # Try to play nice...
                sleep(FETCH_SLEEP)

                # Ready for next batch.
                ts = time()
                batch_count += 1
                small_list = []
                small_results = []
            i += 1

        # Fetch and parse any left over after last small_list.
        # TODO DRY this code.
        pool = ThreadPool(5)
        for player in small_list:
            small_results.append(pool.apply_async(fetch_player, args=(session, player, LLHEADER )))
        pool.close()
        pool.join()
        for r in small_results:
            results.append(r.get())

        this_batch = (time() - ts)
        print(f'Batch: {batch_count} of {total_batches}. Fetching {FETCH_BATCH} image URLs in: {this_batch}')

        print('fetched'.format(len(results)))

        # Pickle these complete player objects.
        with open(Path('pickles', 'members.pkl'), 'wb') as f:
            pickle.dump(results, f)

    # load member data
    if Path('pickles', 'members.pkl').is_file():
        with open(f'pickles/members.pkl', 'rb') as f:
            member_data = pickle.load(f)
    else:
        print('pickes/members.pkl not found. Change FETCH_FLAGDATA to True.')

    # Generate players.js file.
    print('Generating js/players.js file.')
    player_js_output = 'var members = [];\n'
    page_counter = 1
    members_per_page = math.floor(len(member_data)/NUMBER_OF_PAGES)
    i = 0
    member_counter = 1
    for member in member_data:
        memberName = member['player_name']
        memberProfile = LLHEADER + member['player_link']
        if member['player_flag'] == None:
            flagUrl = ''
        else:
            flagUrl = LLHEADER + member['player_flag']
        if i > members_per_page:
            page_counter += 1
            i = 0
        else:
            i += 1
        player_js_output += f"members.push({{'memberCounter': {member_counter}, 'page': {page_counter}, 'memberLink': '{memberProfile}', 'memberName': '{memberName}', 'flagUrl': '{flagUrl}'}});\n"
        member_counter += 1

    # Write the completd player.js file.
    with open(Path('ll', 'js', 'players.js'), 'w', encoding="utf-8") as f:
        f.write(player_js_output)

    print('Done.')
