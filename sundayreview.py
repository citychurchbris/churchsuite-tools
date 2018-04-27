#!/usr/bin/python3
import json
import sys
from datetime import datetime

from lxml import html

from masterrota import login


def get_attendance(churchname, username, password, date):
    """
    Get attendance figures for the given date
    """
    datestr = date.strftime('%Y-%m-%d')
    print('Getting attendance for {}'.format(datestr))

    attendance_url = (
        'https://{churchname}.churchsuite.co.uk/modules/'
        'attendance/date_view.php?date={date}'.format(
            churchname=churchname,
            date=datestr,
        )
    )

    session = login(churchname, username, password)
    response = session.get(attendance_url)

    tree = html.fromstring(response.content)
    rows = tree.cssselect('div.week-category')
    for row in rows:
        print(row.cssselect('h3')[0].text_content())
        print(row.cssselect('td.attendance')[0].text_content().strip())


if __name__ == "__main__":
    try:
        configfile = sys.argv[1]
    except IndexError:
        print('Please provide a JSON config file')
        sys.exit(1)

    with open(configfile, 'r') as f:
        config = json.load(f)

    get_attendance(
        config['churchname'],
        config['username'],
        config['password'],
        datetime(2018, 4, 22),
    )

    print('Done')
