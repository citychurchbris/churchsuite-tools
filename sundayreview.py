#!/usr/bin/python3
import json
import sys
from datetime import datetime

import dateutil
import drive
from dateutil import relativedelta
from lxml import html
from masterrota import login


def get_attendance(churchname, username, password, date, siteid=None):
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

    session = login(churchname, username, password, siteid)
    response = session.get(attendance_url)

    tree = html.fromstring(response.content)
    rows = tree.cssselect('div.week-category')

    attendance = []
    for row in rows:
        meeting = row.cssselect('h3')[0].text_content().strip()
        numbers = row.cssselect(
            'tfoot td.attendance')[0].text_content().strip()
        try:
            numbers = int(numbers)
        except ValueError:
            # no value
            continue
        if not numbers:
            continue

        attendance.append({
            'meeting_name': meeting,
            'numbers': int(numbers),
        })
    return attendance


def get_responses(sheetid, range_name, date):
    print('Getting responses data for {}'.format(date))

    service = drive.get_service()

    sheet_data = service.spreadsheets().values().get(
        spreadsheetId=sheetid,
        range=range_name
    ).execute()

    responses = []

    # Skip the header row
    for row in sheet_data['values'][1:]:
        rowdate = dateutil.parser.parse(
            row[0], dayfirst=True,
        ).date()
        if rowdate == date:
            responses.append(row)

    return responses


if __name__ == "__main__":
    try:
        configfile = sys.argv[1]
    except IndexError:
        print('Please provide a JSON config file')
        sys.exit(1)

    with open(configfile, 'r') as f:
        config = json.load(f)

    now = datetime.now()
    last_sunday = (
        now + relativedelta.relativedelta(
            weekday=relativedelta.SU(-1))
    ).date()

    print('Sunday review for last sunday ({})'.format(
        last_sunday,
    ))

    att = get_attendance(
        config['churchname'],
        config['username'],
        config['password'],
        last_sunday,
    )

    if not att:
        print('No attendance figures')
    for meeting in att:
        print(
            '{meeting_name}:\t{numbers}'.format(
                **meeting
            )
        )

    responses = get_responses(
        config['response_google_sheet_id'],
        "Form responses 1",
        last_sunday,
    )

    if responses:
        print('Responses: ')
        for response in responses:
            print(', '.join(response))
