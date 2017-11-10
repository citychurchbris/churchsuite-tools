#!/usr/bin/python3
import json
import sys
from datetime import datetime, timedelta

import dateutil.parser
import emails
import requests
import tablib
from lxml import html

import drive
from terminaltables import AsciiTable

CA_DATE_FORMAT = '%d-%m-%Y'
SHEETS_ROOT_URL = 'https://docs.google.com/spreadsheets/d/'
LEAD_ROLES = ['leader', 'preacher', ]
EXCLUDE_ROLES = ['reserve', ]


def is_leader_role(role):
    role = role.lower()
    for lrole in LEAD_ROLES:
        if lrole in role:
            return True
    return False


def fetch_overview(churchname, username, password, year=None, siteid=None):
    if year is None:
        now = datetime.now()
        fromdate = datetime.now().strftime(CA_DATE_FORMAT)
        todate = (now + timedelta(days=365)).strftime(CA_DATE_FORMAT)
    else:
        fromdate = '01-01-{}'.format(year)
        todate = '01-01-{}'.format(year+1)
    print('Fetching rotas from {} to {}'.format(fromdate, todate))

    site_switcher_url = 'https://{churchname}.churchsuite.co.uk/ajax/site'
    report_url = "https://{churchname}.churchsuite.co.uk/modules/rotas/reports/rotas_overview.php?date_start={fromdate}&date_end={todate}&order_by=default&submit_btn=Generate"  # noqa
    login_url = "https://login.churchsuite.com/"
    s = requests.Session()
    login_response = s.post(
        login_url,
        data={
            'username': username,
            'password': password,
            'system': 'admin',
            },
        cookies={
            'churchapp_login_account': churchname
        }
    )
    if login_response.url == login_url:
        print('Error - login failed!')
        sys.exit(1)
    if siteid is not None:
        print('Switching site to: {}'.format(siteid))
        response = s.put(
            site_switcher_url.format(churchname=churchname),
            data={
                'site_id': siteid,
            },
        )
    url = report_url.format(
        churchname=churchname,
        fromdate=fromdate,
        todate=todate,
    )
    print('Running report: {}'.format(url))
    response = s.get(url)
    return response.text


def grab_text(el, selector):
    return el.cssselect(selector)[0].text_content()


def parse_data(text):
    print('Parsing...')
    master = []
    team_names = []
    tree = html.fromstring(text)
    report = tree.cssselect('section.report')[0]

    # First pass to read data
    dates = report.cssselect('.row h2.report_break')
    for el in dates:
        date_rotas = {}
        datetext = el.text_content()
        thedate = dateutil.parser.parse(datetext)
        # We only care about sundays at the moment
        if thedate.weekday() != 6:
            continue

        rotas = el.getparent().cssselect('div.rota-date')
        for rota in rotas:
            team = grab_text(rota, 'span.date-team')
            if team not in team_names:
                team_names.append(team)
            date_rotas[team] = []
            members = rota.cssselect('ul.date-members li.profile-initial')
            for member in members:
                name = grab_text(member, '.profile-name')
                role = grab_text(member, '.roles')
                date_rotas[team].append({
                    'name': name,
                    'role': role,
                    })
        master.append((thedate, date_rotas))

    # now organise
    team_names.sort()
    dataset = tablib.Dataset()
    dataset.headers = ['Date', ] + team_names
    for thedate, rotas in master:
        row = [thedate.date(), ]
        for team_name in team_names:
            names = []
            rota = rotas.get(team_name)
            if rota:
                rota.sort(key=lambda x: x['role'])
                included = []
                for member in rota:
                    if is_leader_role(member['role']):
                        included.append(member)
                if not included:
                    # No leader match - just use all of them
                    included = rota
                for member in included:
                    name = member['name']
                    if member['role'].lower() in EXCLUDE_ROLES:
                        continue
                    elif member['role'] and not \
                            is_leader_role(member['role']):
                        name += ' ({})'.format(member['role'])
                    names.append(name)
            row.append(', '.join(names))
        dataset.append(row)
    return dataset


def write_to_sheet(rows, sheetid, range_name, clear=True):
    body = {
        'values': rows
    }
    service = drive.get_service()
    if clear:
        service.spreadsheets().values().clear(
            spreadsheetId=sheetid,
            body={},
            range=range_name
        ).execute()

    service.spreadsheets().values().update(
        spreadsheetId=sheetid,
        body=body,
        valueInputOption='USER_ENTERED',
        range=range_name
    ).execute()
    print('Changes written to: {}{}'.format(SHEETS_ROOT_URL, sheetid))


def write_overview(dataset, sheetid):
    # Overview
    print('Updating Overview Sheet...')
    timestamp = get_timestamp()
    values = [
        ['', "Last update: {}".format(timestamp), ],
        dataset.headers,
    ]

    for row in dataset:
        cols = [str(x) for x in row]
        values.append(cols)

    write_to_sheet(values, sheetid, "Overview")


def display_rows(rows):
    table = AsciiTable(rows)
    print(table.table)


def write_next(dataset, sheetid, churchname,
               site_name, notify=None, smtp=None):
    # Next sunday
    print('Updating Next Sunday Sheet...')
    timestamp = get_timestamp()
    sunday = dataset.dict[0]
    nicedate = sunday['Date'].strftime('%A %d %b %Y').replace(" 0", " ")
    header_rows = [
        ('Next Sunday', "Last update: {}".format(timestamp), ),
        (nicedate, ''),
    ]
    rows = []
    for header in dataset.headers[1:]:
        value = str(sunday[header])
        if value:
            rows.append((header, value))

    write_to_sheet(header_rows + rows, sheetid, "Next Sunday")
    display_rows(header_rows + rows)

    # Emails
    if notify and smtp:
        next_dataset = tablib.Dataset(
            *rows,
            headers=('Rota', 'People'))
        html = """<style>th, td {{ border-bottom: 1px solid #ccc; padding: 3px; }}</style>
<p><em>This is an automated email generated from all rotas on <a href="{churchsuiteurl}">{churchsuiteurl}</a></em></p>
<p>
<b>{nicedate}</b>
</p>

{table}

<p><em>
  You can <a href="{churchsuiteurl}">update these rotas in ChurchSuite</a>
</em></p>
<p><em>
  Further detail on all rotas is available in <a href="{sheeturl}">this google sheet</a>
</em></p>
<p>
Please note:
<br />
- Only non-leader roles are included after names
<br />
- People with the following roles are excluded from this report: {excluded}
<br />
</p>
""".format(table=next_dataset.html,
           churchsuiteurl='https://{}.churchsuite.co.uk/modules/rotas/'.format(
               churchname),
           sheeturl=SHEETS_ROOT_URL + sheetid,
           nicedate=nicedate,
           excluded=', '.join(EXCLUDE_ROLES))
        message = emails.html(
            html=html,
            subject='[{}] Sunday Roles {}'.format(site_name, nicedate),
            mail_from=smtp.get('user'),
            headers={
                'X-Mailer': 'ChurchSuite Master Rota',
                'X-Auto-Response-Suppress': (
                    'DR, NDR, RN, NRN, OOF, AutoReply'),
            })
        for address in notify:
            response = message.send(
                to=address,
                smtp={
                    "host": smtp.get('host'),
                    "ssl": smtp.get('ssl', False),
                    "port": smtp.get('port', 25),
                    "user": smtp.get('user', None),
                    "password": smtp.get('password', None),
                    }
            )
            print('Notifying {} ({})'.format(address, response.status_code))


def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M')


if __name__ == "__main__":
    try:
        configfile = sys.argv[1]
    except IndexError:
        print('Please provide a JSON config file')
        sys.exit(1)
    if '--notify' in sys.argv:
        notify = True
    else:
        notify = False

    with open(configfile, 'r') as f:
        config = json.load(f)
    if '--test' in sys.argv:
        overview = open('example.html').read()
    else:
        overview = fetch_overview(
            config['churchname'],
            config['username'],
            config['password'],
            siteid=config.get('site_id', None),
        )
    dataset = parse_data(overview)
    write_overview(dataset, config['google_sheet_id'])
    write_next(
        dataset,
        config['google_sheet_id'],
        config['churchname'],
        config['site_name'],
        notify=notify and config.get('notify'),
        smtp=config.get('smtp'),
    )
    print('Done')
