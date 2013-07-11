# Copyright (C) 2010 Google Inc.
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

"""Utilities for OAuth.

Utilities for making it easier to work with OAuth 2.0
credentials.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import logging
import os
import stat
import threading


from anyjson import simplejson
from client import Storage as BaseStorage
from client import Credentials

from gi.repository import GConf


class CredentialsFileSymbolicLinkError(Exception):
  """Credentials files must not be symbolic links."""


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from a file."""

  CREDENTIALS_KEY = "/desktop/sugar/collaboration/gdrive_credentials"

  def __init__(self, filename, use_gconf=False):
    self._filename = filename
    self._lock = threading.Lock()
    self._use_gconf = use_gconf

  def _validate_file(self):
    if os.path.islink(self._filename):
      raise CredentialsFileSymbolicLinkError(
        'File: %s is a symbolic link.' % self._filename)

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant."""
    if not self._use_gconf:
      self._lock.acquire()

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    if not self._use_gconf:
      self._lock.release()

  def locked_get(self):
    """Retrieve Credential from file or gconf.

    Returns:
      client.Credentials

    Raises:
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """
    credentials = None

    if self._use_gconf:
      client = GConf.Client.get_default()
      content = client.get_string(self.CREDENTIALS_KEY)
      print 'Storage get content:', content
      if content is None:
        return credentials
    else:
      self._validate_file()
      try:
        f = open(self._filename, 'rb')
        content = f.read()
        f.close()
      except IOError:
        return credentials

    try:
      credentials = Credentials.new_from_json(content)
      credentials.set_store(self)
    except: #  ValueError:
      logging.error('Could not get credentials from %s' % (str(content)))

    return credentials

  def _create_file_if_needed(self):
    """Create an empty file if necessary.

    This method will not initialize the file. Instead it implements a
    simple version of "touch" to ensure the file has been created.
    """
    if not os.path.exists(self._filename):
      old_umask = os.umask(0177)
      try:
        open(self._filename, 'a+b').close()
      finally:
        os.umask(old_umask)

  def locked_put(self, credentials):
    """Write Credentials to file or to gconf.

    Args:
      credentials: Credentials, the credentials to store.

    Raises:
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """
    print 'Storage put content', credentials.to_json()
    if self._use_gconf:
      client = GConf.Client.get_default()
      client.set_string(self.CREDENTIALS_KEY, credentials.to_json())
    else:
      self._create_file_if_needed()
      self._validate_file()
      f = open(self._filename, 'wb')
      f.write(credentials.to_json())
      f.close()

  def locked_delete(self):
    """Delete Credentials file.

    Args:
      credentials: Credentials, the credentials to store.
    """
    if self._use_gconf:
      client = GConf.Client.get_default()
      client.remove_dir(self.CREDENTIALS_KEY)
    else:
      os.unlink(self._filename)
