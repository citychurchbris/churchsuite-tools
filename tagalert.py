#!/usr/bin/python3
"""
TAG ALERT

Notifications for users who match a specific tag on ChurchSuite

Usage:
> python tagalert.py myconfig.json

myconfig.json:
{
    "tagid": <tag id>,
    "account": <account>.churchsuite.co.uk,
    "apikey": "",
    "subscribers": [
        'joe@yourdomaib.com'
    ],
    "smtp":{
        "host": <email-host>,
        "ssl": true,
        "port": 465,
        "user": "<smtp-user>",
        "password": "<smtp-password>"
    }
}
"""
import json
import sys
import requests
import emails

API_ROOT = 'https://api.churchsuite.co.uk/v1'
CONTACT_URL_TEMPLATE = (
    'https://{account}.churchsuite.co.uk/modules/'
    'addressbook/contact_view.php?id={contact_id}'
)
TAG_REPORT_TEMPLATE = (
    'https://{account}.churchsuite.co.uk/modules/'
    'addressbook/tag_view.php?id={tag_id}'
)


def search_tag(config):
    tag_url = "{}/addressbook/tag/{}?contacts=true".format(
        API_ROOT,
        config['tagid'],
    )
    response = requests.get(
        tag_url,
        headers={
            'X-Account': config['account'],
            'X-Auth': config['apikey'],
            'X-Application': 'tagalert',
            'Content-Type': 'application/json',
        }
    )
    if response.status_code == 200:
        return response.json()
    else:
        print('Got {} response from {}'.format(
            response.status_code,
            tag_url,
            ))
        print(response.text)
        sys.exit(1)


def notify(config, tag_name, contacts):
    contact_string = (
        "<a href='{contact_url}'>"
        "{contact[first_name]} {contact[last_name]}"
        "</a>"
    )
    contact_html = '<br />'.join(
        contact_string.format(
            contact_url=CONTACT_URL_TEMPLATE.format(
                account=config['account'],
                contact_id=contact['id'],
            ),
            contact=contact)
        for contact in contacts
    )
    html = """<p>This is an automated email generated by 'tagalert'.</p>
<p>
Tag: <b>{tag_name}</b>
<br />
Matches: <b>{total}</b>
</p>

<p>
<a href="{tag_view}">View full tag report on ChurchSuite</a>
</p>

<p>
Match details:
<br />
{contacts}
</p>
""".format(
      tag_name=tag_name,
      total=len(contacts),
      tag_view=TAG_REPORT_TEMPLATE.format(
          account=config['account'],
          tag_id=config['tagid'],
      ),
      contacts=contact_html,
    )
    smtp = config['smtp']
    message = emails.html(
        html=html,
        subject='ChurchSuite Tag Alert: {}'.format(tag_name),
        mail_from=smtp.get('user'),
    )
    for address in config['subscribers']:
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


if __name__ == "__main__":
    try:
        configfile = sys.argv[1]
    except IndexError:
        print('Please provide a JSON config file')
        sys.exit(1)
    with open(configfile, 'r') as f:
        config = json.load(f)

    data = search_tag(config)
    contacts = data['contacts']
    tag_name = data['name']
    total = len(contacts)
    if total <= 0:
        print('No contacts found for tag: {}'.format(
            tag_name,
        ))
    print('Found {} contacts for tag: {}'.format(
        total,
        tag_name,
    ))
    notify(config, tag_name, contacts)
    print('Done')
