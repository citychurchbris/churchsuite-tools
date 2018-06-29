#!/usr/bin/python3
import json
import sys
from datetime import datetime
from string import ascii_letters

import dateutil
import drive
from dateutil import relativedelta
from lxml import html
from masterrota import login

SHEETS_ROOT_URL = 'https://docs.google.com/spreadsheets/d/'


def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M')


def get_text(elem):
    """Grab cleaned text from an etree element"""
    return elem.text_content().strip()


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

    print('Reading attendance figures from {}'.format(attendance_url))
    response = session.get(attendance_url)

    tree = html.fromstring(response.content)
    site_rows = tree.cssselect('div.week-category')

    attendance = {}
    for site_row in site_rows:
        meeting_name = get_text(site_row.cssselect('h3')[0])
        meeting_data = {}
        attendance_entries = site_row.cssselect('tr')
        for entry in attendance_entries:
            groupname = get_text(entry.cssselect('td.group')[0])
            try:
                attendance_value = int(
                    get_text(entry.cssselect('td.attendance')[0])
                )
            except ValueError:
                # Ignore - no value
                continue
            else:
                meeting_data[groupname] = attendance_value
        attendance[meeting_name] = meeting_data
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


def update_cell(sheetid, cellref, data):
    body = {
        'values': [
            [data, ],
        ]
    }
    service = drive.get_service()
    service.spreadsheets().values().update(
        spreadsheetId=sheetid,
        body=body,
        valueInputOption='USER_ENTERED',
        range=cellref,
    ).execute()


def update_sheet_dates(sheetid, thedate):
    update_cell(
        sheetid,
        "'Last Sunday Summary'!B2",
        get_timestamp(),
    )
    update_cell(
        sheetid,
        "'Last Sunday Summary'!B3",
        thedate.strftime('%A %d %b %Y')
    )


def find_row_by_label(rows, label):
    """
    Pull a single row from tabular data (rows and columns aka a list of lists)
    using the value of the first column
    """
    for row_num, row in enumerate(rows, start=1):
        if row[0] == label:
            return row_num, row


def update_sheet_numbers(sheetid, attendance_data):
    service = drive.get_service()
    sheet_data = service.spreadsheets().values().get(
        spreadsheetId=sheetid,
        range="Last Sunday Summary",
    ).execute()

    sheet_rows = sheet_data['values']

    _, heading_row = find_row_by_label(sheet_rows, 'Attendance')

    for meeting_name, meeting_attendance in attendance_data.items():
        if meeting_name not in heading_row:
            print('Skipping meeting not in output sheet: {}'.format(
                meeting_name,
            ))
            continue

        # Look up the column letter for this meeting
        meeting_column = ascii_letters[heading_row.index(
            meeting_name)].upper()

        for groupname, attendance_value in meeting_attendance.items():
            try:
                group_row_num, _ = find_row_by_label(sheet_rows, groupname)
            except TypeError:
                print('Skipping group not in output sheet: {}'.format(
                    groupname,
                ))
                continue

            # print('Writing {} to {}{}'.format(
            #     attendance_value,
            #     meeting_column,
            #     group_row_num,
            # ))
            update_cell(
                sheetid,
                "'Last Sunday Summary'!{col}{row}".format(
                    col=meeting_column,
                    row=group_row_num,
                ),
                attendance_value,
            )


if __name__ == "__main__":
    try:
        configfile = sys.argv[1]
    except IndexError:
        print('Please provide a JSON config file')
        sys.exit(1)

    with open(configfile, 'r') as f:
        config = json.load(f)

    sheetid = config['google_sheet_id']

    now = datetime.now()
    last_sunday = (
        now + relativedelta.relativedelta(
            weekday=relativedelta.SU(-1))
    ).date()

    last_sunday = datetime(2018, 6, 17)

    print('Sunday review for last sunday ({})'.format(
        last_sunday,
    ))

    attendance = get_attendance(
        config['churchname'],
        config['username'],
        config['password'],
        last_sunday,
    )

    if not attendance:
        print('No attendance figures')
    for meeting_name, meeting_attendance in attendance.items():
        print(
            '{meeting_name}:\t{total}'.format(
                meeting_name=meeting_name,
                total=meeting_attendance.get('Total'),
            )
        )

    # Update the sunday heading and timestamp
    update_sheet_dates(
        sheetid,
        last_sunday,
    )

    # Write attendance to the google sheet
    sheetid = config['google_sheet_id']
    update_sheet_numbers(sheetid, attendance)

    responses = get_responses(
        sheetid,
        "Form responses 1",
        last_sunday,
    )

    if responses:
        print('Responses: ')
        for response in responses:
            print(', '.join(response))

    print('Changes written to: {}{}'.format(SHEETS_ROOT_URL, sheetid))
