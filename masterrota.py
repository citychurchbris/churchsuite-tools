import requests
from lxml import html
username = ''
password = ''


def fetch_overview():
    url = "https://citychurchbris.churchapp.co.uk/modules/rotas/reports/rotas_overview.php?return_url=%2Fmodules%2Frotas%2Freports%2Findex.php&date_start=04-01-2016&date_end=16-12-2016&ministries%5B%5D=1&ministries%5B%5D=22&ministries%5B%5D=10&ministries%5B%5D=21&ministries%5B%5D=25&ministries%5B%5D=9&ministries%5B%5D=8&order_by=default&submit_btn=Generate"
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
            'churchapp_login_account': 'citychurchbris'
        }
    )

    response = s.get(
        url,
    )
    return response.text

if __name__ == "__main__":
    overview = fetch_overview()
    tree = html.fromstring(overview)
    people = tree.cssselect('.rota-subsection a.profile span.profile-name')
    for person in people:
        print(person.text)
