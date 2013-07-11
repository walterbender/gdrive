# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Google Inc.
# Copyright (C) 2013, Walter Bender
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging
import time
import urllib
import urlparse

from gi.repository import GConf
from gi.repository import WebKit

from jarabe.webservice import accountsmanager
from cpsection.webaccount.web_service import WebService

from file import Storage
from client import AccessTokenRefreshError
from client import flow_from_clientsecrets
from tools import run
from httplib2 import Http
from discovery import build

from gettext import gettext as _

# CLIENT_SECRETS, name of a file containing the OAuth 2.0 information
# for this application, including client_id and client_secret.  You
# can see the Client ID and Client secret on the API Access tab on the
# Google APIs Console <https://code.google.com/apis/console>
CLIENT_SECRETS = 'client_secrets.json'

# Helpful message to display if the CLIENT_SECRETS file is missing.
MISSING_CLIENT_SECRETS_MESSAGE = \
    os.path.join(os.path.dirname(__file__), CLIENT_SECRETS)


class WebService(WebService):
    REDIRECT_URI = 'http://www.sugarlabs.org'

    def __init__(self):
        logging.error('GETTING GOOGLE DRIVE ACCOUNT')
        self._account = accountsmanager.get_account('gdrive')
        logging.error(self._account)

    def get_icon_name(self):
        return 'gdrive'

    def config_service_cb(self, widget, event, container):
        logging.debug('GDRIVE: config_service_cb')

        wkv = WebKit.WebView()
        wkv.connect('load-error', self.__load_error_cb)
        self._get_gdrive_credentials(wkv)        
        wkv.grab_focus()

        for c in container.get_children():
            container.remove(c)

        container.add(wkv)
        container.show_all()

        self._get_gdrive_build_http()

    def _get_gdrive_credentials(self, wkv):
        # Set up a Flow object to be used for authentication.  Add one
        # or more of the following scopes. PLEASE ONLY ADD THE SCOPES
        # YOU NEED. For more information on using scopes please see
        # <https://developers.google.com/+/best-practices>.

        FLOW = flow_from_clientsecrets(CLIENT_SECRETS,
                                       scope=[
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.apps.readonly',
                'https://www.googleapis.com/auth/drive.metadata.readonly',
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive.scripts',
                'https://www.googleapis.com/auth/drive.readonly',
                ],
                                       message=MISSING_CLIENT_SECRETS_MESSAGE)

        # If the Credentials don't exist or are invalid, run through
        # the native client flow. The Storage object will ensure that
        # if successful the good Credentials will get written back to
        # gconf.

        storage = Storage(None, use_gconf=True)
        self._credentials = storage.get()

        # Commented out to force exercising the web authentification
        # code during debugging.
        # if self._credentials is None or self._credentials.invalid:
        self._credentials = run(FLOW, storage, wkv)

    def _get_gdrive_build_http(self):
        # Create an httplib2.Http object to handle our HTTP requests
        # and authorize it with our good Credentials.
        http = Http()
        http = self._credentials.authorize(http)

        service = build('drive', 'v2', http=http)

        try:
            logging.debug('Success!')

        except AccessTokenRefreshError:
            logging.error('The credentials have been revoked or expired.')

    def __load_error_cb(self, web_view, web_frame, uri, web_error):
        # Don't show error page if the load was interrupted by policy
        # change or the request is going to be handled by a
        # plugin. For example, if a file was requested for download or
        # an .ogg file is going to be played.
        if web_error.code in (
            WebKit.PolicyError.FRAME_LOAD_INTERRUPTED_BY_POLICY_CHANGE,
            WebKit.PluginError.WILL_HANDLE_LOAD):
            logging.error('WEB ERROR CODE in...')
        data = {
            'page_title': _('This web page could not be loaded'),
            'title': _('This web page could not be loaded'),
            'message': _('"%s" could not be loaded. Please check for '
                         'typing errors, and make sure you are connected '
                         'to the Internet.') % uri,
            'btn_value': _('Try again'),
            'url': uri,
            }
        logging.error(data)
        # html = open(DEFAULT_ERROR_PAGE, 'r').read() % data
        # web_frame.load_alternate_string(html, uri, uri)
        return True

def get_service():
    logging.error('get Google Drive service')
    return WebService()
