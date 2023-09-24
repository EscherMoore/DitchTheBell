# This file is part of Ditch The Bell.

# Ditch The Bell is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# Ditch The Bell is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Ditch The Bell. If not, see
# <https://www.gnu.org/licenses/>.
"""A class for loading various config options into memory"""

import configparser
from datetime import timedelta
import logging
import shlex
import shutil
import sys
from tempfile import gettempdir
from pathlib import Path

from aiohttp import ClientTimeout
from gi.repository import GLib, Gio


class Config:
    """A class for loading various config options into memory"""

    XDG_CONFIG_HOME = GLib.get_user_config_dir()
    XDG_DATA_HOME = GLib.get_user_data_dir()
    TMP_DIR = gettempdir()

    CURRENT_DIRECTORY = Path(__file__).parent
    DEFAULT_CONFIG_PATH = CURRENT_DIRECTORY / 'default' / 'config.ini'
    DEFAULT_URLS_PATH = CURRENT_DIRECTORY / 'default' / 'urls'
    DEFAULT_THUMBNAIL_PATH = CURRENT_DIRECTORY / 'default' / 'thumbnail.png'

    USER_CONFIG_DIR = Path(XDG_CONFIG_HOME) / 'dtbell'
    USER_DATA_DIR = Path(XDG_DATA_HOME) / 'dtbell'
    USER_TMP_DIR = Path(TMP_DIR) / 'dtbell'

    USER_CONFIG_PATH = USER_CONFIG_DIR / 'config.ini'
    USER_URLS_PATH = USER_CONFIG_DIR / 'urls'
    USER_CACHE_PATH = USER_DATA_DIR / 'dtbell.db'
    USER_LOG_PATH = USER_DATA_DIR / 'dtbell.log'

    USER_DEFAULT_BROWSER = Gio.AppInfo.get_default_for_uri_scheme('http')

    def __init__(self):
        self.active_notifications = {}
        self.urls = []
        self.profiles = {}
        self.new_cache = False
        self.log = logging.getLogger(__name__)

        self._create_user_paths()
        self._load_config()
        self._parse_urls()

    def _create_user_paths(self):
        self.USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not self.USER_CONFIG_PATH.exists():
            shutil.copy(self.DEFAULT_CONFIG_PATH, self.USER_CONFIG_PATH)

        self.USER_URLS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not self.USER_URLS_PATH.exists():
            shutil.copy(self.DEFAULT_URLS_PATH, self.USER_URLS_PATH)

        # The initial call to sqlite3.connect() will implicitly create cache
        self.USER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not self.USER_CACHE_PATH.exists():
            self.new_cache = True

        # The logger will implicitly create the log file
        self.USER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        self.USER_TMP_DIR.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        config_parser = configparser.ConfigParser()

        config_parser.read(self.USER_CONFIG_PATH)

        if 'feed' not in config_parser.sections():
            pass

        # pylint: disable=C0103
        self.SEARCH_WINDOW = timedelta(
            days=config_parser.getint('feed', 'search_window', fallback=1))
        self.SEARCH_INTERVAL = timedelta(
            minutes=config_parser.getint(
                'feed', 'search_interval', fallback=30))
        self.SEARCH_ON_STARTUP = config_parser.getboolean(
            'feed', 'search_on_startup', fallback='True')
        self.FLOOD_CAP = config_parser.getint(
            'feed', 'flood_cap', fallback=10)
        self.HTTP_REQUEST_TIMEOUT = ClientTimeout(total=config_parser.getint(
            'feed', 'fetch_timeout', fallback=10)
        )

        if 'default' not in config_parser.sections():
            pass

        default_profile = {
            'profile_name': 'default',
            'launcher': config_parser.get(
                'default', 'launcher', fallback='default_browser'),
            'launcher_args': shlex.split(config_parser.get(
                'default', 'launch_args', fallback='').strip('\'"')),
            'transience': config_parser.getboolean(
                'default', 'transience', fallback=False),
            'persist_on_click': config_parser.getboolean(
                'default', 'persist_on_click', fallback=False),
            'urgency': config_parser.getint(
                'default', 'urgency', fallback=1),
            'timeout': config_parser.getint(
                'default', 'timeout', fallback=-1),
            'entry_age': config_parser.getboolean(
                'default', 'entry_age', fallback=False),
            'download_thumbnails': config_parser.getboolean(
                'default', 'download_thumbnails', fallback=True),
        }

        self.profiles['default'] = default_profile

        for profile_name in config_parser.sections():
            if profile_name in ['feed', 'default']:
                continue

            custom_profile = {
                'profile_name': profile_name,
                'launcher': config_parser.get(
                    profile_name,
                    'launcher', fallback=default_profile['launcher']),
                'launcher_args': shlex.split(config_parser.get(
                    profile_name,
                    'launcher_args',
                    fallback=default_profile['launcher_args']).strip('\'"')),
                'transience': config_parser.getboolean(
                    profile_name, 'transience',
                    fallback=default_profile['transience']),
                'persist_on_click': config_parser.getboolean(
                    profile_name,
                    'persist_on_click',
                    fallback=default_profile['persist_on_click']),
                'urgency': config_parser.getint(
                    profile_name,
                    'urgency',
                    fallback=default_profile['urgency']),
                'download_thumbnails': config_parser.getboolean(
                    profile_name,
                    'download_thumbnails',
                    fallback=default_profile['download_thumbnails']),
                'entry_age': config_parser.getboolean(
                    profile_name,
                    'entry_age',
                    fallback=default_profile['entry_age']),
                'timeout': config_parser.getint(
                    profile_name,
                    'timeout', fallback=default_profile['timeout']),
            }

            self.profiles[profile_name] = custom_profile
            self.log.error('Loaded custom profile: %s', profile_name)

    def _parse_urls(self):
        with open(self.USER_URLS_PATH, 'r', encoding='utf-8') as urls:
            for line in urls:
                if line.startswith('http'):
                    strings = [string.strip() for string in line.split(' ')]
                    url, url_data = strings[0], {}

                    for string in strings[1:]:
                        if string == '#' or string.startswith('#'):
                            if not url_data:
                                url_data = {
                                    'profile_name': 'default',
                                    'url': url
                                }
                            break
                        elif (
                            string in self.profiles and string != 'default'
                        ):
                            url_data = {
                                'profile_name': string,
                                'url': url
                            }
                            break
                        else:
                            self.log.warning(
                                    'Feed <%s> used a profile with the name '
                                    '\'%s\' but that name isn\'t recognized '
                                    'as a valid profile name. Using default '
                                    'profile instead.')
                            url_data = {
                                'profile_name': 'default',
                                'url': url
                            }
                            break
                    self.urls.append(url_data)
            if not self.urls:
                self.log.error('No urls found at: %s', self.USER_URLS_PATH)
                sys.exit(1)


config = Config()
