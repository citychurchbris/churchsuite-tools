import json
import requests
from lxml import html
from datetime import datetime


def fetch_overview(churchname, username, password, year=None):
    if year is None:
        year = datetime.today().year
    fromdate = '01-01-{}'.format(year)
    todate = '01-01-{}'.format(year+1)

    report_url = "https://{churchapp}.churchapp.co.uk/modules/rotas/reports/rotas_overview.php?date_start={fromdate}&date_end={todate}&order_by=default&submit_btn=Generate"  # noqa
    login_url = "https://login.churchapp.co.uk/"
    s = requests.Session()
    s.post(
        login_url,
        data={
            'churchname': churchname,
            'username': username,
            'password': password,
            'system': 'churchapp',
            },
        cookies={
            'churchapp_login_account': churchname
        }
    )
    response = s.get(report_url.format(
        fromdate=fromdate,
        todate=todate,
    ))

    return response.text


if __name__ == "__main__":
    with open('config.json', 'r') as f:
        config = json.load(f)
    overview = fetch_overview(
        config['churchname'],
        config['username'],
        config['password'])
    tree = html.fromstring(overview)
    people = tree.cssselect('.rota-subsection a.profile span.profile-name')
    for person in people:
        print(person.text)
