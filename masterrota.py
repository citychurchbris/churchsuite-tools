#!/usr/bin/python3
import json
import sys
import requests
import tablib
import drive
from lxml import html
from datetime import datetime
from datetime import timedelta
import dateutil.parser

CA_DATE_FORMAT = '%d-%m-%Y'


def fetch_overview(churchname, username, password, year=None):
    if year is None:
        now = datetime.now()
        fromdate = datetime.now().strftime(CA_DATE_FORMAT)
        todate = (now + timedelta(days=365)).strftime(CA_DATE_FORMAT)
    else:
        fromdate = '01-01-{}'.format(year)
        todate = '01-01-{}'.format(year+1)
    print('Fetching rotas from {} to {}'.format(fromdate, todate))

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
    response = s.get(report_url.format(
        churchname=churchname,
        fromdate=fromdate,
        todate=todate,
    ))

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
                    if 'leader' in role.lower():
                        names.append(name)
                if not names:
                    # No leader match - just use first person
                    names.append(list(rota.values())[0])
            row.append(', '.join(names))
        dataset.append(row)
    return dataset


def write_data(dataset, sheetid):
    print('Updating Google Sheet...')
    service = drive.get_service()
    range_name = "Overview"
    values = [dataset.headers, ]

    for row in dataset:
        cols = [str(x) for x in row]
        values.append(cols)

    body = {
        'values': values
    }
    service.spreadsheets().values().update(
        spreadsheetId=sheetid,
        body=body,
        valueInputOption='USER_ENTERED',
        range=range_name).execute()


if __name__ == "__main__":
    with open('config.json', 'r') as f:
        config = json.load(f)
    if '--test' in sys.argv:
        overview = open('example.html').read()
    else:
        overview = fetch_overview(
            config['churchname'],
            config['username'],
            config['password'])
    dataset = parse_data(overview)
    write_data(dataset, config['google_sheet_id'])
    #open('out.csv', 'w').write(dataset.csv)
