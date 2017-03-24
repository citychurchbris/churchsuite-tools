#!/usr/bin/python3
import json
import sys
import requests
import tablib
import drive
import emails
from lxml import html
from datetime import datetime
from datetime import timedelta
import dateutil.parser

CA_DATE_FORMAT = '%d-%m-%Y'
SHEETS_ROOT_URL = 'https://docs.google.com/spreadsheets/d/'
LEAD_ROLES = ['leader', 'preacher', ]


def fetch_overview(churchname, username, password, year=None, siteid=None):
    if year is None:
        now = datetime.now()
        fromdate = datetime.now().strftime(CA_DATE_FORMAT)
        todate = (now + timedelta(days=365)).strftime(CA_DATE_FORMAT)
    else:
        fromdate = '01-01-{}'.format(year)
        todate = '01-01-{}'.format(year+1)
    print('Fetching rotas from {} to {}'.format(fromdate, todate))

    site_switcher_url = 'https://{churchname}.churchapp.co.uk/ajax/site'
    report_url = "https://{churchname}.churchapp.co.uk/modules/rotas/reports/rotas_overview.php?date_start={fromdate}&date_end={todate}&order_by=default&submit_btn=Generate"  # noqa
    login_url = "https://login.churchapp.co.uk/"
    s = requests.Session()
    s.post(
        login_url,
        data={
            'username': username,
            'password': password,
            'system': 'churchapp',
            },
        cookies={
            'churchapp_login_account': churchname
        }
    )
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
            date_rotas[team] = {}
            members = rota.cssselect('ul.date-members li.profile-initial')
            for member in members:
                name = grab_text(member, '.profile-name')
                role = grab_text(member, '.roles')
                date_rotas[team][role] = name
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
                for role, name in list(rota.items()):
                    for lead_role in LEAD_ROLES:
                        if lead_role in role.lower():
                            names.append(name)
                if not names:
                    # No leader match - just use all of them
                    names = list(rota.values())
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


def write_next(dataset, sheetid, notify=None, smtp=None):
    # Next sunday
    print('Updating Next Sunday Sheet...')
    timestamp = get_timestamp()
    sunday = dataset.dict[0]
    nicedate = sunday['Date'].strftime('%A %d %b %Y')
    rows = [
        ('Next Sunday', "Last update: {}".format(timestamp), ),
        (nicedate, ''),
    ]
    for header in dataset.headers[1:]:
        value = str(sunday[header])
        if value:
            rows.append((header, value))

    write_to_sheet(rows, sheetid, "Next Sunday")

    # Emails
    if notify and smtp:
        # Skip first row
        next_dataset = tablib.Dataset(*rows[2:], headers=rows[1])
        message = emails.html(
            html=next_dataset.html,
            subject='Sunday roles {}'.format(nicedate),
            mail_from=('ChurchApp Master Rota', smtp.get('user')),
        )
        for address in notify:
            response = message.send(
                to=address,
                smtp=smtp,
            )
            print('Notifying {} ({})'.format(address, response.status_code))


def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M')


if __name__ == "__main__":
    try:
        configfile = sys.argv[1]
    except IndexError:
        configfile = 'config.json'
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
        notify=notify and config.get('notify'),
        smtp=config.get('smtp'),
    )
    print('Done')
