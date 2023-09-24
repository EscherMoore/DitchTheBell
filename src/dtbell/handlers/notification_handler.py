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
"""Handle notification events."""

import logging
import os
import subprocess
from pathlib import Path

from gi.repository import GLib
from pydbus import SessionBus

from dtbell.config import config
from dtbell.cache import cache_manager

log = logging.getLogger(__name__)

session_bus = SessionBus()
notification_service = session_bus.get('org.freedesktop.Notifications')


def send_notifications(new_entries):
    """
    Send notifications for new entries found in feeds and cache
    each entry to avoid sending again on subsequent searches.

    :param new_entries: List of new feed entries.

    :return: None
    """

    if not new_entries:
        return
    if (
        len(new_entries) <= config.FLOOD_CAP
        or config.FLOOD_CAP == 0
    ):
        for entry in new_entries:
            notification_id = send_notification(entry)
            if notification_id:
                cache_manager.add(entry)
                notification_data = {
                    'launcher': entry.get('launcher'),
                    'launcher_args': entry.get('launcher_args'),
                    'link': entry.get('link'),
                    'thumbnail_path': entry.get('thumbnail_path'),
                }
                config.active_notifications[
                    notification_id
                ] = notification_data
            else:
                log.error(
                    'Failed to send a notification for: %s', entry['link'])
    else:
        flood_capped_notification = {
            'title': f'{len(new_entries)} new entries!', 'actions': []}
        send_notification(flood_capped_notification)


def send_notification(notification_contents):
    """
    Build and send a desktop notification based on the provided
    contents.

    :param notification_contents: A dictionary containing
        key-value pairs for constructing the notification. Expected
        keys include 'thumbnail_path', 'author', 'title', 'actions',
        'timeout', 'urgency', 'transience', and 'persist_on_click'.

    :return: The ID of the notification that was sent.
    """

    app_name = 'Ditch The Bell'
    replaces_id = 0  # 0 will not replace any existing notifications
    thumbnail_path = notification_contents.get(
        'thumbnail_path', str(config.DEFAULT_THUMBNAIL_PATH))
    title = notification_contents.get('author', 'Ditch The Bell')
    body = notification_contents.get('title', 'ERROR: TITLE NOT FOUND')
    actions = notification_contents.get('actions', ['default', 'Open'])
    timeout = notification_contents.get(
        'timeout', config.profiles['default']['timeout'])
    hints = {
        'urgency': GLib.Variant(
            'i', notification_contents.get(
                'urgency', config.profiles['default']['urgency'])
            ),
        'transient': GLib.Variant(
            'b', notification_contents.get(
                'transience', config.profiles['default']['transience'])),
        'resident': GLib.Variant(
            'b', notification_contents.get(
                'persist_on_click',
                config.profiles['default']['persist_on_click']))
    }
    notification_id = notification_service.Notify(
        app_name, replaces_id, thumbnail_path,
        title, body, actions, hints, timeout
    )
    return notification_id


def on_notification_clicked(notification, action_key):
    """
    Retrieve the associated link for the clicked notification and, if
    available, the user-configured 'launcher' and 'launcher_args'
    to open it. If no such configurations are present,
    default to opening the link using the user's default browser.

    :param notification: The ID of the clicked notification.
    :param action_key: The action key associated with the clicked
                       notification (e.g., 'default').

    :return: None
    """

    if action_key == 'default':
        if notification in config.active_notifications:
            clicked_notification = config.active_notifications[notification]
            link = clicked_notification.get('link')
            launcher = clicked_notification.get('launcher')
            launcher_args = clicked_notification.get('launcher_args')

            if launcher == 'default_browser':
                config.USER_DEFAULT_BROWSER.launch_uris([link], None)
                log.info('Launching <%s> with default browser.', link)
                return

            custom_launch_cmd = [launcher]
            if launcher_args:
                custom_launch_cmd.extend(launcher_args)
            custom_launch_cmd.append(link)
            log.info('Launching <%s> with (%s)', link, launcher)
            try:
                with open(os.devnull, 'w', encoding='utf-8') as null:
                    subprocess.Popen(
                        custom_launch_cmd, shell=False, stderr=null)
            except OSError as error:
                log.error(
                    '%s when launching <%s> with (%s)',
                    error, link, launcher)
            except ValueError as error:
                log.error(
                    '%s when launching <%s> with (%s)',
                    error, link, launcher)


def on_notification_closed(notification, _):
    """
    Remove the downloaded thumbnail associated with the notification if
    it exists.

    :param notification: The ID of the closed notification.
    :param _: Placeholder for a 'reason' parameter (not used).

    :return: None
    """

    if notification in config.active_notifications:
        thumbnail_path = Path(
            config.active_notifications[notification]['thumbnail_path']
        )
        if thumbnail_path.parent == config.USER_TMP_DIR:
            os.remove(thumbnail_path)
        config.active_notifications.pop(notification)
        log.info('Notification (%s) was closed and cleaned up.', notification)


notification_service.ActionInvoked.connect(on_notification_clicked)
notification_service.NotificationClosed.connect(on_notification_closed)
