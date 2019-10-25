import math
import os
import pickle
import shutil
import textwrap 

import multiprocessing as mp

from pathlib import Path

from llama_slobber import get_session
from llama_slobber import get_season
from llama_slobber import get_leagues
from llama_slobber import get_rundles
from llama_slobber import get_rundle_members

from llama_slobber import get_personal_flag
from llama_slobber import get_raw_file

def chunks(l, n):
    """Yield n number of sequential chunks from l."""
    d, r = divmod(len(l), n)
    for i in range(n):
        si = (d+1)*(i if i < r else r) + d*(0 if i < r else i - r)
        yield l[si:si+(d+1 if i < r else d)]

def process_league(session, season, league):
    download_members = False
    download_flags = False
    rundle_count = 0
    members = []
    i = 0

    if download_members:
        # print(league)
        
        rundles = get_rundles(session=session, season=season, league=league)
        for rundle in rundles:
            #print(rundle)
            people = get_rundle_members(session=session, season=season, rundle=rundle)
            for person in people:
                person_info = {}
            
                person_info['league'] = league
                person_info['season'] = season
                person_info['rundle'] = rundle
                person_info['member_id'] = person
                person = get_personal_flag(person)
                if person:
                    person_info['member_name'] = person['member_name'][9:]
                    flag_extension = person['flag_src'][-3:]
                    if flag_extension == 'gif':
                        person_info['image_src'] = person['flag_src']
                        remote_url = person['flag_src']
                        local_folder_path = Path(person['flag_src'][1:]).parent
                        local_file_path = Path(person['flag_src'][1:])

                        # Create directories if the they don't exist
                        local_folder_path.mkdir(parents=True, exist_ok=True)

                        if download_flags:
                            img_file = get_raw_file(remote_url)
                            with open(local_file_path, 'wb') as f:
                                f.write(img_file.content)
                    # print(person_info)
                    members.append(person_info)
            i += 1
        with open(f'{league}.pkl', 'wb') as f:
            pickle.dump(members, f)
    print('{}: {}'.format(league, i))
    return {'league': league, 'count': i}

def log_result(retval):
    results.append(retval)
    print('{}\n'.format(retval))

if __name__ == "__main__":
    s = get_session()
    this_season = get_season(session=s)
    leagues = get_leagues(session=s, season=this_season)    
            
    download_user_data = False

    if download_user_data:
        results = []
        pool = mp.Pool(processes=4)
        for league in leagues:
            pool.apply_async(process_league, args=(s, this_season, league, ), callback=log_result)
        pool.close()
        pool.join()
        print(results)

    generate_html = True
    page_size = 50000

    if generate_html:
        members = []
        for league in leagues:
            with open(f'pickles/{league}.pkl', 'rb') as f:
                m = (pickle.load(f))
            for this_m in m:
                members.append(this_m)
        
        sorted_members = sorted(members, key = lambda i: i['member_name'].lower().replace(' ', ''))
        
        n = 20
        #split the list into n chunks.
        these_chunks = chunks(sorted_members, n)
        
        page_list = []
        for this_chunk in these_chunks:
            page_list.append(this_chunk)

        i = 1

        # each page needs a table of contents.
        toc_list = []
        for toc in page_list:
            toc_count = len(toc)
            toc_list.append({                
                'member_begin': toc[0]['member_name']
                , 'member_end': toc[toc_count-1]['member_name']
                , 'page_num': i
            })
            i += 1

        i = 1
        for page in page_list:
            member_count = len(this_chunk)

            page_string = '<div class="container">\n'
            page_string += '\t<div class="row">\n'
            page_string += '\t\t<div class="col-sm bg-white align-items-end m-2 p-2"><span id="page_number">Page {}</span></div>\n'.format(i)
            page_string += '\t</div>\n'
            page_string += '</div>\n'

            flags = []
            col_counter = 1
            flags_string = '\t<div class="row">\n'
            for member in page:
                flags_string += '\t\t<div class="col-sm bg-white align-items-end m-2 p-2 border border-secondary">'
                flags_string += ('<a href="{TARGET}" class="flag">'
                        '<img src="data:image/gif;base64,R0lGODdhAQABAPAAAMPDwwAAACwAAAAAAQABAAACAkQBADs=" data-src="{IMAGE_SOURCE}" class="flagimg" width="154" height="87" title="{MEMBER_NAME}" alt="{MEMBER_NAME}">'
                    '</a><br />{MEMBER_NAME}').format(
                    TARGET='https://learnedleague.com/profiles.php?' + member['member_id']
                    , IMAGE_SOURCE='https://learnedleague.com' + member['image_src']
                    , MEMBER_NAME=member['member_name']
                )
                flags_string += '\t</div>\n'
                if col_counter == 4:
                    flags_string += '\t</div>\n\t<div class="row">\n'
                    col_counter = 1
                else:
                    col_counter += 1
            flags_string += '</div>\n</div>\n'

            # reset the column counter
            col_counter = 1
            toc_string = ''
            for toc_entry in toc_list:
                page_num = toc_entry['page_num']
                member_begin = toc_entry['member_begin']
                member_end = toc_entry['member_end']
                toc_string += f'\t\t\t\t<a class="dropdown-item" href="/ll/flag/{page_num}" id="page_nav_{page_num}">Page {page_num}: {member_begin} through {member_end}</a>\n'
            toc_string += '\n'

            member_begin = toc_list[i-1]['member_begin']
            member_end = toc_list[i-1]['member_end']

            output_html = textwrap.dedent(f'''<!DOCTYPE html>
            <html lang="en">
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
                    <meta name="description" content="">
                    <meta name="author" content="WyattW, @tayknight, llama-slobber">
                    <title>LL 82 Flags! {member_begin} - {member_end}</title>
                    <link rel="stylesheet" href="/ll/css/bootstrap.min.css">
                    <link rel="stylesheet" href="/ll/css/navbar.css">
                    <script src="/ll/js/jquery-3.3.1.slim.min.js"></script>
                    <script src="/ll/js/popper.min.js"></script>
                    <script src="/ll/js/bootstrap.min.js"></script>
                    <script src="/ll/js/lazyload.js"></script>
                </head>
                <body>
                    <nav class="fixed-top navbar navbar-expand-xl navbar-dark bg-dark">
                    <div class="container">
                        <a class="navbar-brand" href="#">Learned League 82 member flags</a>
                        <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarsExample03" aria-controls="navbarsExample03" aria-expanded="false" aria-label="Toggle navigation">
                            <span class="navbar-toggler-icon"></span>
                        </button>

                        <div class="collapse navbar-collapse" id="navbarsExample03">
                            <ul class="navbar-nav mr-auto">
                                <li class="nav-item dropdown">
                                    <a class="nav-link dropdown-toggle" href="#" id="dropdown03" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">Click here to choose page of member flags...</a>
                                    <div class="dropdown-menu" aria-labelledby="dropdown03">
                                        {toc_string}
                                    </div>
                                </li>
                            </ul>
                            <ul class="navbar-nav mr-auto">
                                <li class="nav-item dropdown">
                                    <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                        Feedback...
                                    </a>
                                    <div class="dropdown-menu" aria-labelledby="navbarDropdown">
                                        <a class="dropdown-item" href="https://learnedleague.com/profiles.php?34441">WyattW <img class="pb-1" src="https://www.learnedleague.com/images/f2/wy/WyattWsm.gif"></a>
                                        <a class="dropdown-item" href="https://twitter.com/tayknight">@tayknight</a>
                                        <a class="dropdown-item" href="https://github.com/wusui/llama_slobber">Built with llama-slobber</a>
                                    </div>
                                </li>
                            </ul>
                        </div>
                    </div>
                </nav>
                
                {page_string}
                <main role="main" class="container">
                    {flags_string}
                </main>
                <script>
                    window.addEventListener("load", function(event) {{
                        let images = document.querySelectorAll("[data-src]");
                        let lazy = lazyload(images, {{"src": "data-src"}});
                        //$('#page_number').text($('#page_nav_1').text())
                        
                        this_page_number = $('#page_number').text();
                        match = this_page_number.match(/(Page\s)([0-9]*)/);

                        nav_element = "#page_nav_" + match[2]
                        nav_text = $(nav_element).text()

                        $('#page_number').text(nav_text);
                    }});
                </script>
            </body>
        </html>''')

            with open('ll/flag_{}.html'.format(i), 'w') as f:
                f.write(output_html)
            
            i += 1

    print('done')
