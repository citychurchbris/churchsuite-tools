ChurchSuite Tools
=================

Requirements
------------

* Python 3.6
* pipenv_

Installation
------------

#. Clone this repo

   .. code:: sh

        git clone https://github.com/citychurchbris/churchsuite-tools.git

#. Install dependencies with pipenv_

   .. code:: sh

        cd churchsuite-tools
        pipenv install

#. Obtain a credentials 'secret' for Google Drive, by following Step 1 of this guide:

   https://developers.google.com/drive/api/v3/quickstart/python

   (Please note - only step one of the guide above is required.
   All other steps are covered automatically by the code in this package)

   Rename the downloaded credentials file to 'drive_client_secret.json' and
   move to the root of directory you placed this package.

#. Initialize drive credentials:

   .. code:: sh

       pipenv run python drive.py

The Tools
---------

-------------
masterrota.py
-------------

The master rota script attempts to scrape the 'All Rotas' report in ChurchSuite
and populate a google sheet with the results, with a column for every rota,
a row for every Sunday, and the names of anyone on the rota in each cell.

It will also create an overview sheet in the same document with details for the
'next' Sunday.

It will also optionally generate an email summary of rotas for 'next' Sunday

#. Create a config file using `config-examples/masterrota.example.json` as a guide. You need to provide your churchsuite login details, a reference to the google sheet for output, and smtp credentials for the summary email.

.. include:: config-examples/masterrota.example.json
   :code: js

#. You can then run the script as follows:

   .. code:: sh

       pipenv run python masterrota.py <config-file>

#. To trigger the email summary:

   .. code:: sh

       pipenv run python masterrota.py <config-file> --notify

#. This script is designed to be run regularly with cron (e.g. once a day)
   to keep the drive doc in sync with churchsuite. The notification trigger
   is designed to be run separately - once or twice a week.

-----------
tagalert.py
-----------

Notifications for users who match a specific tag on ChurchSuite.

This uses the official `ChurchSuite API`_ and requires an API key.

#. Set up a config file as per the example, using your `ChurchSuite API`_ key:

   .. include:: config-examples/tagalert.example.json
       :code: js

#. Run with:

   .. code:: sh

        pipenv run python tagalert.py <config-file>

#. This script is designed to be run regularly with cron (e.g. once a week)
   to check for users who match a tag.



.. _pipenv: https://docs.pipenv.org/
.. _`ChurchSuite API`: https://github.com/ChurchSuite/churchsuite-api

---------------
sundayreview.py
---------------

**IN PROGRESS**

This script is designed to pull Sunday numbers and summary data
from ChurchSuite.
