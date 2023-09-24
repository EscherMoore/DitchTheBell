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
"""Main Application Class"""

import atexit
import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from .config import config
from .feed import feed

log = logging.getLogger(__name__)
try:
    from gi.repository import GLib
except ImportError:
    log.error(
        "You must install PyGObject (PyGI) from your distribution's "
        "repository - it's usually called python-gi, python-gobject "
        "or pygobject. See the README for more info")
    sys.exit(1)


class DitchTheBell:
    """Main Application Class"""

    def __init__(self):
        self._prepare_logger()
        self.loop = GLib.MainLoop()
        atexit.register(self._cleanup)

    def _prepare_logger(self):
        log_format = '%(asctime)s %(levelname)s - %(name)s - %(message)s'
        formatter = logging.Formatter(log_format)

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(
            logging.DEBUG if '--debug' in sys.argv else logging.WARNING
        )
        stream_handler.setFormatter(formatter)

        one_mb_base10 = 1e6
        file_handler = RotatingFileHandler(
            config.USER_LOG_PATH, maxBytes=one_mb_base10, backupCount=3)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)

    def start(self):
        """Start the main event loop"""

        log.info('STARTING: Ditch The Bell...')
        GLib.timeout_add_seconds(
            config.SEARCH_INTERVAL.total_seconds(),
            lambda: asyncio.run(feed.fetch_new()) or True
        )
        if config.SEARCH_ON_STARTUP:
            asyncio.run(feed.fetch_new())
        self.loop.run()

    def _cleanup(self):
        deleted, delete_quota = 0, len(os.listdir(config.USER_TMP_DIR))
        for thumbnail in os.listdir(config.USER_TMP_DIR):
            try:
                thumbnail_path = os.path.join(config.USER_TMP_DIR, thumbnail)
                os.remove(thumbnail_path)
                deleted += 1
            except OSError as error:
                log.error(
                    '%s occurred while attempting to delete a thumbnail',
                    error)
        log.info(
            'Cleaned up (%s/%s) thumbnails in <%s>',
            deleted, delete_quota, config.USER_TMP_DIR)
        log.info('STOPPING: Ditch The Bell...')
        logging.shutdown()
        self.loop.quit()


def entry_point():
    """Entry point for Ditch The Bell"""

    dtbell = DitchTheBell()
    dtbell.start()


if __name__ == '__main__':
    entry_point()
