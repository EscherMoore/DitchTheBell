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
"""A class implementing a cache for managing feed entries in SQLite."""

from datetime import datetime
import logging
import sqlite3

from .config import config


class CacheManager:
    """
    A class implementing a cache for managing feed entries in SQLite.
    """

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.db_connection = None
        self.cursor = None
        self._setup()

    @staticmethod
    def _ensure_connection(func):
        def wrapper(self, *args, **kwargs):
            self.db_connection = sqlite3.connect(config.USER_CACHE_PATH)
            self.cursor = self.db_connection.cursor()

            result = func(self, *args, **kwargs)

            self.db_connection.commit()
            self.db_connection.close()
            return result
        return wrapper

    @_ensure_connection
    def _setup(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feed_entries (
                link TEXT PRIMARY KEY,
                publish_date DATETIME
            )
        ''')

    @_ensure_connection
    def add(self, entry):
        """
        Add an entry to the cache if it doesn't already exist.

        :param entry: An entry dictionary containing a 'link' key and a
                      'publish_date' key.

        :return: None
        """
        self.cursor.execute(
            '''
                INSERT OR IGNORE INTO feed_entries (link, publish_date)
                VALUES (?, ?)
            ''',
            (entry['link'], entry['publish_date'])
        )

    @_ensure_connection
    def seen(self, link):
        """
        Search the cache to see if an entry has been seen.

        :param link: The entry link.

        :return: True if the entry has been seen, False otherwise.
        """
        self.cursor.execute(
            'SELECT EXISTS(SELECT 1 FROM feed_entries WHERE link=?)', (link,))
        (exists,) = self.cursor.fetchone()
        return bool(exists)

    @_ensure_connection
    def prune_old(self):
        """
        Prune entries outside of the search_window from the cache.

        :return: None
        """
        if config.new_cache:
            return
        cutoff_date = datetime.now() - config.SEARCH_WINDOW
        self.log.info(
            'Pruning entries older than %s from the cache.', cutoff_date)
        self.cursor.execute(
            'DELETE FROM feed_entries WHERE publish_date<?', (cutoff_date,))


cache_manager = CacheManager()
