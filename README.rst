ChurchSuite Tools
=================

Requirements
------------

 * Python 3.6
 * Pipenv_

Installation
------------

First, obtain a credentials 'secret' for Google Drive, by following Step 1 of this guide:

https://developers.google.com/drive/api/v3/quickstart/python

(Please note - only step one of the guide above is required. All other steps are
covered automatically by the code in this package)

Rename the downloaded credentials file to 'drive_client_secret.json' and
move to the root of directory you placed this package.

.. code:: sh

          pipenv install

.. _Pipenv: https://docs.pipenv.org/
