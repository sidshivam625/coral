# Firefox Local Source

Query your local Mozilla Firefox browser data using SQL through Coral.

Because browsers do not expose your personal data via public REST APIs, this source utilizes a lightweight, zero-dependency local Python server. By default, it automatically finds and uses your most recently used Firefox profile, safely reads the underlying SQLite databases and JSON files, and serves them to Coral over localhost.

If you want to pin the source to a specific profile directory, set `FIREFOX_PROFILE_PATH` before starting the server. You can also set `FIREFOX_PROFILES_PATH` to override the root `Profiles` directory that the fallback scan uses.

All processing happens entirely on your machine. No data ever leaves your computer.

## Features

* **Explicit Profile Override:** Set `FIREFOX_PROFILE_PATH` to query one specific Firefox profile directory.
* **Deterministic Profile Resolution:** No setup is required for the default case; if no explicit profile is set, the server scans the Firefox `Profiles` directory and locks onto the most recently used profile.
* **Safe SQLite Extraction:** Copies the main `places.sqlite` database along with its Write-Ahead Log (`-wal`) and Shared Memory (`-shm`) sidecars to ensure data is complete and prevents locking issues while the browser is running.
* **Zero Dependencies:** The local server uses only standard Python libraries. No pip installs required.
* **Port Isolation:** Runs on port `8766` to allow concurrent execution with the Chromium source server.

## Extracted Data

This source extracts the following data points:

* **Bookmarks:** Saved URLs and folder structures from `moz_bookmarks`.
* **History:** Browsing history from `moz_places`. (Timestamps converted from PRTime to ISO 8601 UTC).
* **Extensions:** Installed extensions and their current versions parsed from `extensions.json`.
* **Top Sites:** A ranked list of your most frequently visited sites based on Mozilla's `frecency` algorithm.

*Note: Session-restore (Tabs) parsing is intentionally omitted from this source to maintain the zero-dependency requirement, as Mozilla utilizes a proprietary `jsonlz4` compression format for session files.*

## Setup

### 1. Start the Local Browser Server

Run the included Python script to start the threaded local HTTP server. Leave this running in the background while you query Coral.

To query a specific profile, set `FIREFOX_PROFILE_PATH` to the profile directory that contains `places.sqlite` and `extensions.json`.

```bash
python sources/community/firefox/browser_server.py   
``` 




# Contributions By github.com/GaneshBamalwa and github.com/Vishy-MK 

