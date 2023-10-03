<br />
<div align="center">
  <h1 align="center">Ditch The Bell</h1>
  <a href="https://github.com/EscherMoore/DitchTheBell">
    <img src="https://raw.githubusercontent.com/EscherMoore/DitchTheBell/main/logo.png" alt="Logo">
  </a>
  <p align="center">
    A desktop notifier for RSS/Atom feeds that lets you closely configure features of the <a href="https://specifications.freedesktop.org/notification-spec/latest/ar01s02.html">freedesktop notification specification</a> to unlock the most customizable feed notification experience possible on Linux.
  </p>
</div>

### Features

* Configure a custom command to launch when clicking on a notification (e.g., your favorite application, shell command, custom script). The feed entry link will be passed as an argument, allowing the command to open the link directly.

* A feed profile system built to separate notification behaviors for each of your different types of feeds (e.g., news, blogs, podcasts, videos, etc).

* Define patterns in your profiles to filter feeds so you're only notified for the entries that are relevant to you.

* Configuration options to fine-tune feed fetching behavior such as the search window, search interval, etc.

<br />

### Install

###### Dependencies:

* `Python 3.7+`
* **Optional**: Before installing, it is recommended that you install <a href="https://pygobject.readthedocs.io/en/latest/devguide/dev_environ.html?highlight=install#install-dependencies">PyGObject</a> from your distribution's package manager for <a href="https://wiki.gnome.org/Projects/GObjectIntrospection">GObject Introspection</a>. The package is typically named one of the following: `python-gi`, `python-gobject`, or `pygobject` on most distributions.

Ditch The Bell is available on <a href="https://pypi.org/project/dtbell/">PyPI</a> and can be installed via <a href="https://pip.pypa.io/en/stable/">pip</a>, the Python package manager.
```bash
pip install dtbell
```

<br />

### Usage

To run, simply execute:

```bash
dtbell
```

If needed, use the `--debug` flag to print debug logs to the console:

```bash
dtbell --debug 
```

<br />

## Configuring

#### File Locations

All relevant files are stored in accordance with the <a href="https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html">XDG Base Directory Specification</a>.

Configuration files `config.ini`, `urls`: are located in `$XDG_CONFIG_HOME/dtbell/`. 
> If `$XDG_CONFIG_HOME` is not set, the default location is `$HOME/.config/dtbell/`.

Data files `dtbell.db`, `dtbell.log`: are located in `$XDG_DATA_HOME/dtbell/`. 
> If `$XDG_DATA_HOME` is not set, the default location is `$HOME/.local/share/dtbell/`.

If you enable thumbnail downloads, thumbnails will be temporarily downloaded to `/tmp/dtbell/`.

### Adding Feeds

To add feeds, edit the `urls` file, adding one URL per line.

```text
https://example.com/feed/rss.xml
https://another-example.com/feed/rss.xml
```

Authenticated feeds are not yet supported.

### Configuration Options 

To modify the configuration settings, edit the `config.ini` file.

#### Feed Configuration

The `[feed]` section in your `config.ini` file serves as the primary area for defining feed fetch behavior. Below are the available configuration options for the `[feed]` section:

| Name                | Description                                                                                                | Data Type | Default Value |
|---------------------|------------------------------------------------------------------------------------------------------------|-----------|---------------|
| `search_window`     | The number of days to go back when searching for new feeds. Cached entries are retained for this duration. | Integer   | `1`           |
| `search_interval`   | Time interval (in minutes) between each search for new entries.                                            | Integer   | `30`          |
| `search_on_startup` | Determines if a search is initiated upon application launch.                                               | Boolean   | `true`        |
| `flood_cap`         | Maximum number of notifications to avoid notification flooding. Set to 0 for unlimited.                    | Integer   | `10`          |
| `fetch_timeout`     | Maximum time (in seconds) the app will wait for a response after requesting a feed.                        | Integer   | `10`          |

#### Defining Profiles

The profile system is designed to adapt to the diverse array of feeds that modern RSS users often manage (news feeds, blog feeds, podcast feeds, etc). It allows for tailored notification behavior based on the nature of each feed. You can define custom notification profiles for these specific types of feeds in your `config.ini` file. For instance, a profile for video based feeds could look like this:

```ini
[video]
entry_age = true
persist_on_click = true
launcher = mpv 
launcher_args = '--save-position-on-quit'
```

A `[default]` profile is defined in the `config.ini` file and serves as the baseline configuration for all feeds not tagged with a custom profile. Below are the available configuration options for the `[default]` section:

| Name                  | Description                                                                              | Data Type                        | Default Value     |
|-----------------------|------------------------------------------------------------------------------------------|----------------------------------|-------------------|
| `launcher`            | Shell command to open notifications; must accept a URL as argument.                      | String                           | `default_browser` |
| `launch_args`         | Argument(s) to pass to `launcher`; e.g., `'-P news'` if `launcher` was set to `firefox`. | String                           | `''`              |
| `transience`          | Determines whether notifications are temporary and disappear after a short time.         | Boolean                          | `false`           |
| `persist_on_click`    | Keep notification after click; useful if transience is set to false.                     | Boolean                          | `false`           |
| `urgency`             | Notification urgency: 0 (low), 1 (normal), 2 (critical).                                 | Integer                          | `1`               |
| `timeout`             | Timeout in ms; -1 for server default, 0 for never.                                       | Integer                          | `-1`              |
| `entry_age`           | Display entry age.                                                                       | Boolean                          | `false`           |
| `download_thumbnails` | Download thumbnails; consult your feed's TOS and be mindful of bandwidth usage.          | Boolean                          | `true`            |
| `require_patterns`    | Require entries to contain at least one of these patterns; e.g., `'Open Source', Linux`  | Custom (Comma-separated values)  | `''`              |
| `exclude_patterns`    | Exclude entries that contain any one of these patterns; e.g., `Proprietary, Windows`     | Custom (Comma-separated values)  | `''`              |

You can modify the default profile directly to affect all untagged feeds, or define custom profiles like the `[video]` profile if you wish to customize settings for a select group of feeds. Omitting fields in a custom profile will cause those settings to fall back to the values defined in the default profile.

#### Adding Profiles to URLs

As mentioned earlier, the `urls` file should contain one RSS feed URL per line. To associate a profile with a specific feed, simply append the profile name (the name within the square brackets `[ ]` in your `config.ini`) to the end of the feed URL, separated by a space. The format is simply `url profile`. For instance, using the `[video]` profile from earlier, an example `urls` file would look like this:

```text
https://example.com/feed/rss.xml video
https://another-example.com/feed/rss.xml video
```

<br />

## Contributing

This program is in its early stages of development and may have some rough edges or bugs. If you encounter any issues and want to contribute, feel free to submit an issue or open a PR!

Note: All PRs must adhere to PEP 8 and pass pylint checks.

<br />

#### License

This program is licensed under the GPLv3; see the LICENSE file.
