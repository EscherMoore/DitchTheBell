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
"""
A class for fetching new feed entries and notifying the user of each
new entry found.
"""

import asyncio
from datetime import datetime
import logging
import tempfile
from urllib.parse import urlparse

import aiohttp
from aiohttp import TCPConnector
from dateutil.parser import parse
import feedparser
import pytz

from .cache import cache_manager
from .config import config
from .handlers import notification_handler


class Feed:
    """
    A class for fetching new feed entries and notifying the user of
    each new entry found.

    :param urls: A list of dictionaries, each containing a feed url and
                 its associated profile.
    """

    def __init__(self, urls):
        self.urls = urls
        self.log = logging.getLogger(__name__)

    async def fetch_new(self):
        """
        Fetch new entries from feeds and send notifications.

        :return: Always returns True for successful execution.
        """

        self.log.info('Searching feeds for new entries...')
        all_new_entries = []
        cache_manager.prune_old()
        connector = TCPConnector(limit_per_host=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                self._process_feed(session, url_data)
                for url_data in self.urls
            ]
            try:
                new_entries_by_url = await asyncio.gather(
                        *tasks,
                        return_exceptions=True
                )
            except asyncio.TimeoutError:
                self.log.error('Timeout occurred while loading new entires')
                return True
            for new_entries in new_entries_by_url:
                if isinstance(new_entries, Exception):
                    continue  # Ignore feeds where errors occurred
                all_new_entries.extend(new_entries)
        all_new_entries = self._handle_new_cache(all_new_entries)
        all_new_entries = sorted(
            all_new_entries, key=lambda entry: entry['publish_date'])
        await self._download_thumbnails(all_new_entries)
        notification_handler.send_notifications(all_new_entries)

        self.log.info(
            'Search complete. (%s) new entries found.', len(all_new_entries))
        return True

    async def _process_feed(self, session, url_data):
        try:
            raw_xml = await self._fetch_raw_feed_data(
                    session, url_data['url'])
            parsed_feed = feedparser.parse(raw_xml) if raw_xml else {}
        except aiohttp.ClientResponseError:
            return []

        attribute_errors = 0
        entries, new_entries = parsed_feed.get('entries', []), []
        current_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
        for entry in entries:
            if any(key not in entry for key in ['title', 'link']):
                attribute_errors += 1
                continue
            published = entry.get('published') or entry.get('updated')
            if not published:
                attribute_errors += 1
                continue
            entry.author = entry.get('author', "???")
            publish_date = parse(published)
            if not publish_date.tzinfo: publish_date = publish_date.replace(tzinfo=pytz.UTC)
            entry_age = current_time - publish_date
            if (
                entry_age < config.SEARCH_WINDOW
                and not cache_manager.seen(entry.link)
            ):
                profile = config.profiles.get(url_data['profile_name'], {})

                require_patterns = profile.get('require_patterns')
                if require_patterns:
                    if not any(
                        pattern in entry.title
                        or pattern in entry.author
                        for pattern in require_patterns
                    ):
                        continue
                exclude_patterns = profile.get('exclude_patterns')
                if exclude_patterns:
                    if any(
                        pattern in entry.title
                        or pattern in entry.author
                        for pattern in exclude_patterns
                    ):
                        continue

                new_entry = {
                    'author': (
                        entry.author+' - '+self._readable_entry_age(entry_age)
                        if profile.get('entry_age') else entry.author),
                    'title': entry.title,
                    'link': entry.link,
                    'thumbnail_url': (
                        self._resolve_thumbnail_url(entry)
                        if profile.get('download_thumbnails') else None),
                    'publish_date': publish_date,
                    'launcher': profile.get('launcher'),
                    'launcher_args': profile.get('launcher_args'),
                    'transience': profile.get('transience'),
                    'persist_on_click': profile.get('persist_on_click'),
                    'timeout': profile.get('timeout'),
                    'urgency': profile.get('urgency'),
                }
                new_entries.append(new_entry)

        if attribute_errors > 0:
            self.log.warning(
                'Skipped (%s/%s) new entries in feed: <%s> due to missing '
                'attributes', attribute_errors, len(entries), url_data['url'])
        return new_entries

    async def _fetch_raw_feed_data(self, session, url):
        try:
            async with session.get(
                        url, timeout=config.HTTP_REQUEST_TIMEOUT
                    ) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientResponseError as error:
            self.log.error('An HTTP error occurred %s', error)
            raise

    def _readable_entry_age(self, time):
        days = time.days
        hours, remainder = divmod(time.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        format_days = (
            f'{days} days' if days > 1 else
            f'{days} day' if days == 1 else None
        )
        format_hours = (
            f'{hours} hrs' if hours > 1 else
            f'{hours} hr' if hours == 1 else None
        )

        formatted_time_parts = [
            part for part in [format_days, format_hours] if part
        ]

        if formatted_time_parts:
            return f'{", ".join(formatted_time_parts)} ago'
        return f'{minutes} mins ago'

    def _resolve_thumbnail_url(self, entry):
        thumbnails, thumbnail_url = entry.get('media_thumbnail', []), None

        smallest_width = smallest_height = float('inf')
        for thumbnail in thumbnails:
            width = int(thumbnail['width'])
            height = int(thumbnail['height'])
            if not width or not height:
                continue
            if (
                width < smallest_width
                and height < smallest_height
            ):
                smallest_width = width
                smallest_height = height
                thumbnail_url = thumbnail['url']
        if not thumbnail_url:
            parsed_url = urlparse(entry.link)
            scheme = parsed_url.scheme
            netloc = parsed_url.netloc
            favicon_path = f'{scheme}://{netloc}/favicon.ico'
            thumbnail_url = favicon_path
        return thumbnail_url

    def _handle_new_cache(self, entries):
        """
        Handles the first search with a new cache file. Caches all
        entries found within the user-configured search window but
        returns only those entries that are published within the
        current search interval. This is to prevent a flood of
        notifications.

        :param entries: List of new feed entries to be processed.
        :return: A filtered list of feed entries that were published
                 within the current search interval.
        """

        if not config.new_cache:
            return entries

        new_entries = []
        current_time = datetime.utcnow().replace(tzinfo=pytz.UTC)

        for entry in entries:
            entry_age = current_time - entry['publish_date']
            if entry_age < config.SEARCH_INTERVAL:
                new_entries.append(entry)
            cache_manager.add(entry)
        config.new_cache = False
        return new_entries

    async def _download_thumbnails(self, new_entries):
        if not new_entries:
            return
        if (
            len(new_entries) <= config.FLOOD_CAP
            or config.FLOOD_CAP == 0
        ):
            connector = TCPConnector(limit_per_host=10)
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = [
                    self._download_thumbnail(session, entry)
                    for entry in new_entries
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
        return

    async def _download_thumbnail(self, session, entry):
        thumbnail_url = entry.pop('thumbnail_url')
        if not thumbnail_url:
            entry['thumbnail_path'] = str(config.DEFAULT_THUMBNAIL_PATH)
            return

        try:
            async with session.get(
                    thumbnail_url, timeout=config.HTTP_REQUEST_TIMEOUT
            ) as response:
                response.raise_for_status()
                content = await response.read()
        except aiohttp.ClientResponseError as error:
            self.log.warning(
                'HTTP error: %s occurred while attempting to download '
                'thumbnail. Using default thumbnail instead.', error
            )
            entry['thumbnail_path'] = str(config.DEFAULT_THUMBNAIL_PATH)
            return

        content_type = response.headers.get('Content-Type')
        suffix = None
        if content_type:
            mime_to_extension = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/vnd.microsoft.icon': '.ico',
                'image/x-icon': '.ico',
                'image/bmp': '.bmp',
                'image/webp': '.webp',
                'image/svg+xml': '.svg',
            }
            content_type = content_type.lower()
            for mime, extension in mime_to_extension.items():
                if mime in content_type:
                    suffix = extension
                    break
        if not content_type or not suffix:
            self.log.warning(
                'Couldn\'t find the thumbnail image extension in response '
                'headers... Using default thumbnail instead.')
            entry['thumbnail_path'] = str(config.DEFAULT_THUMBNAIL_PATH)
            return
        with tempfile.NamedTemporaryFile(
            dir=config.USER_TMP_DIR,
            delete=False,
            prefix='thumbnail_',
            suffix=suffix
        ) as temp_file:
            temp_file.write(content)
            new_thumbnail_path = temp_file.name
            entry['thumbnail_path'] = new_thumbnail_path


feed = Feed(config.urls)
