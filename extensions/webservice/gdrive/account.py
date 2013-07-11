#!/usr/bin/env python
#
# Copyright (c) 2013 Walter Bender, Vadim Gerasimov

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

from gettext import gettext as _
import logging
import os
import tempfile
import json

from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import GConf
from gi.repository import GObject

from sugar3.datastore import datastore
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics.icon import Icon
from sugar3.graphics.menuitem import MenuItem

from jarabe.journal import journalwindow
from jarabe.webservice import account, accountsmanager

ACCOUNT_NEEDS_ATTENTION = 0
ACCOUNT_ACTIVE = 1
ACCOUNT_NAME = _('Google Drive')
COMMENTS = 'comments'
COMMENT_IDS = 'gd_comment_ids'
CREDENTIALS_KEY = "/desktop/sugar/collaboration/gdrive_credentials"


class Account(account.Account):

    def __init__(self):
        self.gdrive = accountsmanager.get_service('gdrive')
        self._client = GConf.Client.get_default()
        self._shared_journal_entry = None

    def get_description(self):
        return ACCOUNT_NAME

    def get_token_state(self):
        return self.STATE_VALID

    def get_shared_journal_entry(self):
        if self._shared_journal_entry is None:
            self._shared_journal_entry = _SharedJournalEntry(self)
        return self._shared_journal_entry


class _SharedJournalEntry(account.SharedJournalEntry):
    __gsignals__ = {
        'transfer-state-changed': (GObject.SignalFlags.RUN_FIRST, None,
                                   ([str])),
    }

    def __init__(self, gdaccount):
        self._account = gdaccount
        self._alert = None

    def get_share_menu(self, journal_entry_metadata):
        menu = _ShareMenu(
            self._account.gdrive,
            journal_entry_metadata,
            self._account.get_token_state() == self._account.STATE_VALID)
        self._connect_transfer_signals(menu)
        return menu

    def get_refresh_menu(self):
        menu = _RefreshMenu(
            self._account.gdrive,
            self._account.get_token_state() == self._account.STATE_VALID)
        self._connect_transfer_signals(menu)
        return menu

    def _connect_transfer_signals(self, transfer_widget):
        transfer_widget.connect('transfer-state-changed',
                                self._transfer_state_changed_cb)

    def _transfer_state_changed_cb(self, widget, state_message):
        logging.debug('_transfer_state_changed_cb')

        # First, remove any existing alert
        if self._alert is None:
            self._alert = NotifyAlert()
            self._alert.props.title = ACCOUNT_NAME
            self._alert.connect('response', self._alert_response_cb)
            journalwindow.get_journal_window().add_alert(self._alert)
            self._alert.show()

        logging.debug(state_message)
        self._alert.props.msg = state_message

    def _alert_response_cb(self, alert, response_id):
        journalwindow.get_journal_window().remove_alert(alert)
        self._alert = None


class _ShareMenu(MenuItem):
    __gsignals__ = {
        'transfer-state-changed': (GObject.SignalFlags.RUN_FIRST, None,
                                   ([str])),
    }

    def __init__(self, account, metadata, is_active):
        MenuItem.__init__(self, ACCOUNT_NAME)

        self._gdrive = account
        if is_active:
            icon_name = 'gdrive'
        else:
            icon_name = 'gdrive-insensitive'
        self.set_image(Icon(icon_name=icon_name,
                            icon_size=Gtk.IconSize.MENU))
        self.show()
        self._metadata = metadata
        self._comment = '%s: %s' % (self._get_metadata_by_key('title'),
                                    self._get_metadata_by_key('description'))

        self.connect('activate', self._gdrive_share_menu_cb)

    def _get_metadata_by_key(self, key, default_value=''):
        if key in self._metadata:
            return self._metadata[key]
        return default_value

    def _gdrive_share_menu_cb(self, menu_item):
        logging.debug('_gdrive_share_menu_cb')


class _RefreshMenu(MenuItem):
    __gsignals__ = {
        'transfer-state-changed': (GObject.SignalFlags.RUN_FIRST, None,
                                   ([str])),
        'comments-changed': (GObject.SignalFlags.RUN_FIRST, None, ([str]))
    }

    def __init__(self, account, is_active):
        MenuItem.__init__(self, ACCOUNT_NAME)

        self._gdrive = account
        self._is_active = is_active
        self._metadata = None

        if is_active:
            icon_name = 'gdrive'
        else:
            icon_name = 'gdrive-insensitive'
        self.set_image(Icon(icon_name=icon_name,
                            icon_size=Gtk.IconSize.MENU))
        self.show()

        self.connect('activate', self._gd_refresh_menu_clicked_cb)

    def set_metadata(self, metadata):
        self._metadata = metadata
        if self._is_active:
            if self._metadata:
                if 'gd_object_id' in self._metadata:
                    self.set_sensitive(True)
                    icon_name = 'gdrive'
                else:
                    self.set_sensitive(False)
                    icon_name = 'gdrive-insensitive'
                self.set_image(Icon(icon_name=icon_name,
                                    icon_size=Gtk.IconSize.MENU))

    def _gd_refresh_menu_clicked_cb(self, button):
        logging.debug('_gd_refresh_menu_clicked_cb')


def get_account():
    return Account()
