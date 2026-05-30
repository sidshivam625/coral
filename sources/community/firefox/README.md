# Firefox Local Source

Query your local Mozilla Firefox browser data using SQL through Coral.

Because browsers do not expose personal data via public REST APIs, this source
uses a lightweight, zero-dependency local Python server. The server reads your
Firefox SQLite databases, serves them to Coral over `localhost`, and **requires
a shared bearer token** so that only the Coral client that knows the token can
read the data.

> **⚠️ Local data exposure risk**
> The server makes your Firefox bookmarks, browsing history, and installed
> extensions readable to any process on your machine that holds the bearer
> token.  Start the server only when you intend to query Coral, and stop it
> immediately afterwards with **Ctrl+C**.  Never expose port `8766` beyond
> `127.0.0.1`.

All processing happens entirely on your machine. No data ever leaves your
computer.

---

## Features

* **Shared bearer token:** Every request must carry `Authorization: Bearer <token>`.
  The token is generated at startup (or read from `FIREFOX_SERVER_TOKEN`) and
  must be exported before running `coral source add`.
* **Host, origin, and fetch-metadata checks:** Requests with an unexpected
  `Host`, `Origin`, or `Referer` header, or a cross-site `Sec-Fetch-Site`
  value, are rejected, blocking DNS-rebinding and browser-side request
  smuggling.
* **Security headers:** All responses include `Cache-Control: no-store` and
  `X-Content-Type-Options: nosniff`.
* **Accurate profile resolution:** Reads Firefox's own `installs.ini` /
  `profiles.ini` metadata to find the correct default profile, instead of
  guessing by file-modification time.
* **Explicit profile override:** Set `FIREFOX_PROFILE_PATH` to pin the server
  to one specific profile directory.
* **Safe SQLite extraction:** Copies `places.sqlite` together with its WAL and
  SHM sidecar files so reads are safe while Firefox is running.
* **Zero dependencies:** Only standard Python libraries – no `pip install`
  required.
* **Port isolation:** Runs on port `8766` to allow concurrent use with the
  Chromium source server.

---

## Extracted Data

| Table | Description |
|-------|-------------|
| `bookmarks` | Saved URLs and folder structures from `moz_bookmarks` |
| `history` | Browsing history from `moz_places` (timestamps as ISO 8601 UTC) |
| `extensions` | Installed extensions and versions from `extensions.json` |
| `top_sites` | Most-visited sites ranked by Mozilla's `frecency` algorithm |

*Note: Session-restore (tabs) parsing is intentionally omitted to preserve the
zero-dependency requirement, as Mozilla uses a proprietary `jsonlz4` format.*

---

## Setup – First-Success Walkthrough

### Step 1 – (Optional) Identify your profile directory

If you have multiple Firefox profiles and want to pin the server to a specific
one, find the profile directory that contains `places.sqlite`:

```
# macOS
ls ~/Library/Application\ Support/Firefox/Profiles/

# Linux
ls ~/.mozilla/firefox/

# Windows (PowerShell)
ls $env:APPDATA\Mozilla\Firefox\Profiles\
```

Note the full path to the profile you want (e.g.
`~/.mozilla/firefox/abc123.default-release`).

### Step 2 – Start the local browser server

Open a **dedicated terminal** and run:

```bash
# Pin to a specific profile (recommended if you have more than one):
export FIREFOX_PROFILE_PATH="~/.mozilla/firefox/abc123.default-release"
# Windows PowerShell:
# $env:FIREFOX_PROFILE_PATH = "$env:APPDATA\Mozilla\Firefox\Profiles\abc123.default-release"

python sources/community/firefox/browser_server.py
```

On first run the server prints a generated bearer token:

```
============================================================
No FIREFOX_API_KEY set. Generated a new token:
  a3f8c1d2e4b5...  (32 hex characters)

Export this value before running `coral source add`:
  export FIREFOX_API_KEY=a3f8c1d2e4b5...   # macOS/Linux
  $env:FIREFOX_API_KEY="a3f8c1d2e4b5..."   # PowerShell
============================================================
Starting Firefox local server on http://127.0.0.1:8766
```

**Keep this terminal open.** The server must stay running while you query Coral.

### Step 3 – Export the bearer token

In a **second terminal**, export the token printed in Step 2 so that
`coral source add` can forward it in the manifest:

```bash
# macOS / Linux
export FIREFOX_API_KEY=a3f8c1d2e4b5...

# Windows PowerShell
$env:FIREFOX_API_KEY="a3f8c1d2e4b5..."
```

> **Tip:** To avoid retyping the token on every server restart, set
> `FIREFOX_API_KEY` to a fixed value in your shell profile (e.g.
> `~/.zshrc`) **and** export it before starting the server:
> ```bash
> export FIREFOX_API_KEY="my-fixed-secret-value"
> python sources/community/firefox/browser_server.py
> ```

### Step 4 – Add the source to Coral

```bash
coral source add --file ./sources/community/firefox/manifest.yaml
```

### Step 5 – Verify the source

```bash
coral source test firefox
```

Expected output (abridged):

```
✔ firefox  bookmarks  1 row
```

If the command reports an error, check that:
- The server is still running (Step 2 terminal).
- `FIREFOX_API_KEY` is exported in **this** terminal and matches the
  value printed by the server (Step 3).
- The profile path contains `places.sqlite`.

If Firefox profile metadata cannot be resolved or `places.sqlite` is missing,
`coral source test firefox` now fails instead of returning an empty success.

### Step 6 – Run a representative query

```sql
-- 10 most recently visited URLs
SELECT title, url, last_visit_date
FROM firefox.history
ORDER BY last_visit_date DESC
LIMIT 10;
```

```sql
-- All bookmarks added in the last 30 days
SELECT title, url, date_added
FROM firefox.bookmarks
WHERE date_added >= datetime('now', '-30 days')
ORDER BY date_added DESC;
```

### Step 7 – Stop the server when done

Return to the first terminal and press **Ctrl+C**:

```
^C
Shutting down server.
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `FIREFOX_API_KEY` | Bearer token for the local HTTP server. If unset, a random token is generated at startup and printed to stdout. |
| `FIREFOX_PROFILE_PATH` | Full path to a specific Firefox profile directory (must contain `places.sqlite`). Overrides automatic profile detection. |
| `FIREFOX_PROFILES_PATH` | Full path to the Firefox `Profiles` root directory. Overrides the platform default used by the `profiles.ini` scanner. |

---

# Contributions by github.com/GaneshBamalwa and github.com/Vishy-MK
