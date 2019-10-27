function GetURLParameter(sParam) {
    var sPageURL = window.location.search.substring(1);
    var sURLVariables = sPageURL.split('&');
    for (var i = 0; i < sURLVariables.length; i++)
    {
        var sParameterName = sURLVariables[i].split('=');
        if (sParameterName[0] == sParam)
        {
            return sParameterName[1];
        }
    }
}

function GetPageNum() {
    var found_page = 1;
    var urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('page')) {
        found_page = GetURLParameter('page');
    }
    else {
        var urlHref = window.location.href;
        parts = urlHref.split('/');
        if ($.isNumeric(parts[(parts.length)-1]) == true) {
            found_page = parts[(parts.length)-1];
        }
    }
    console.log('Looking for page ' + found_page + '.');
    return found_page;
}

function GetPageMembers(pageNum) {
    var results = $.map(members, function(e){
        if( e.page == pageNum ) return e;
    });
    return results;
}

function GetFirstAndLast() {
    max_member = members.length;
    this_member = members[max_member - 1];
    max_page = this_member['page'];
    menu_members = []
    for (i = 1; i <= max_page; i++) {
        // Extract members of this page.
        page_members = GetPageMembers(i);
        first_member = page_members[0];
        last_member = page_members[(page_members.length - 1)];
        menu_members.push({'first': first_member, 'last': last_member});
    }
    return menu_members;
}

function BuildPageDescription() {
    page_num = GetPageNum();
    fl = GetFirstAndLast();
    first_name = fl[page_num - 1]['first']['memberName'];
    last_name = fl[page_num - 1]['last']['memberName'];
    $("#page_number").text("Page " + page_num + ": " + first_name + " through " + last_name + ".");
}

function BuildFlags(results) {
    var col_counter = 1;
    var flags_string = '\t<div class="row">\n';
    $.each(results, function(index, value){
        flags_string += '\t\t<div class="col-sm bg-white align-items-end m-2 p-2 border border-secondary">\n';
        flags_string += '\t\t\t<a href="' + value['memberLink'] + '" class="flag">\n';
        flags_string += '\t\t\t\t<img src="/ll/images/loading.png" data-src="' + value['flagUrl'] + '" class="flagimg" width="154" height="87" title="' + value['memberName'] + '" alt="' + value['memberName'] + '">\n';
        flags_string += '\t\t\t</a><br />' + value['memberName'] + '\n';
        flags_string += '\t\t</div>\n';
        if (col_counter == 4) {
            flags_string += '\t</div>\n\t<div class="row">\n';
            col_counter = 1;
        }
        else {
            col_counter += 1;
        }
    })
    flags_string += '\t\t</div>\n\t\t</div>\n';
    return flags_string;
}

function BuildMenu() {
    menu_members = GetFirstAndLast();
    toc_string = '';
    for(i=1; i <= menu_members.length; i++) {
        toc_string += '\t\t\t\t<a class="dropdown-item" href="/ll/flag/' + i + '" id="page_nav_' + i + '">Page ' + i + ': ' + menu_members[i-1]['first']['memberName'] + ' through ' + menu_members[i-1]['last']['memberName'] + '</a>\n';
        toc_string += '\n';
    }
    page_menu_container = $('#page_menu');
    page_menu_container.append(toc_string);
}

function DrawFlags() {
    found_page = GetPageNum();
    // Extract members of this page.
    results = GetPageMembers(found_page);

    flags_container = $('#flags');
    results_string = BuildFlags(results);
    flags_container.append(results_string);
}
