# Caffrey's Treasure — Personal File Server

A modern, feature-rich HTTP file server built in Python with a polished dark/light web UI, remote filer browsing, ZIP downloads with real-time progress, favorites, search, and more.

## Features

### Core File Server
- **Dark / Light theme** — one-click toggle, persists across sessions via `localStorage`
- **File browser** — directory listing with SVG file-type icons, sizes, timestamps, sortable columns
- **Multi-threaded server** — handles concurrent requests via `ThreadingMixIn` (no request queuing)
- **Gzip compression** — automatic compression of HTML/CSS/JS responses with ETag caching (80-89% size reduction)
- **Responsive design** — works on desktop and mobile with adaptive layout

### File Operations
- **File upload** — drag-and-drop or click-to-browse, uploads to current directory with progress bar
- **Create folders / files** — icon buttons in the sort bar for quick creation
- **Rename** — rename files and folders inline
- **Password-protected delete** — delete files/folders through the UI with a password prompt
- **In-browser file viewer** — view `.log`, `.txt`, `.json`, `.yaml`, `.py`, `.sh` and 25+ formats with syntax highlighting (Prism.js)
- **In-browser file editor** — edit text files directly with a save-back-to-server flow

### ZIP Downloads (Google Drive-style)
- **Download folders as ZIP** — one-click ZIP for any folder (up to 4 GB)
- **Real-time progress** — Server-Sent Events (SSE) stream progress to a Google Drive-style tray
- **Multi-card tray** — multiple concurrent ZIP downloads, each with its own progress card
- **Cancellation** — cancel mid-ZIP via the close button; auto-cancels on page close (`sendBeacon`)
- **Persistent cards** — completed/errored cards stay visible until manually dismissed

### Remote Filer Browser
- **Browse external Apache file servers** directly inside Caffrey's UI
- **Pre-configured filers** (editable in `config.py`):
  - PC Builds, NCC Builds (endor)
  - MSP Platform (phx-fs)
  - NCM Filer (ncmfiler)
  - LCM CCI Builds (builds.dyn)
  - Nutanix Central (endor)
  - CALM Filer (10.40.64.33)
- **Filers dropdown** — icon button in the navbar opens a dropdown to switch filers
- **Full navigation** — breadcrumbs, subdirectory browsing, "Open on source server" link
- **Copy link** — copy the source server URL for any file/folder (useful for `wget`/`curl`)

### Favorites
- **Star any file or folder** — click the star icon on any row to save it
- **Persistent storage** — favorites saved in `data/favorites.json`, survives restarts
- **Favorites page** — dedicated `/__favorites__` page accessible from the navbar star icon
- **Works across local and remote** — favorite both local paths and remote filer paths
- **Badges** — remote favorites show the filer name; missing local items show a "Missing" badge

### Search
- **Instant client-side filter** — typing in the search bar immediately hides non-matching rows (zero latency)
- **Recursive server search** — after 350ms debounce, a background API call walks the filesystem (up to 200 results, 5-second timeout)
- **Results dropdown** — highlighted matches with directory paths, click to navigate
- **Keyboard shortcut** — press `/` to focus, `Escape` to clear

### ChartMuseum Integration
- **Built-in ChartMuseum** — manages Helm chart repos alongside file serving
- **Web UI** — browse charts, versions, download, and upload `.tgz` packages
- **Artifactory import** — download charts from Artifactory directly into ChartMuseum
- **Proxy API** — all ChartMuseum API calls proxied through Caffrey's server

### Copy Link
- **Every file and folder** has a copy-link button in the actions column
- **Local files** — copies the full server URL (e.g., `http://hostname:8086/path/to/file`)
- **Remote files** — copies the source server URL (e.g., `http://ncmfiler.nutanixqa.com/LCM/...`)
- **Current folder** — copy-link button in the sort bar for the directory you're viewing

## Quick Start

```bash
git clone https://github.com/abhinavgarg-ntnx/my-file-server.git ~/my-file-server
cd ~/my-file-server
pip install -r requirements.txt   # optional: only needed for Artifactory chart downloads
```

### Configure your credentials

Create a `.env` file in the project root (it is git-ignored):

```bash
# Required — password used for file/folder deletion via the UI
CFS_PASSWORD=your-secret-password

# Optional — only needed for importing Helm charts from Artifactory
CFS_ARTIFACTORY_KEY=your-jfrog-api-key
```

> **Important:** Never commit real credentials. The `.env` file is listed in
> `.gitignore` and the launcher (`caffrey`) loads it automatically at startup.
> If `CFS_PASSWORD` is not set, it defaults to `caffrey`.
> If `CFS_ARTIFACTORY_KEY` is not set, Artifactory chart imports will be disabled.

### Start the server

```bash
./caffrey
```

The server starts at `http://<hostname>:8086` with ChartMuseum on port `8089`.

## The `caffrey` Command

| Command                        | Description                    |
| ------------------------------ | ------------------------------ |
| `caffrey` or `caffrey restart` | Stop + start the server        |
| `caffrey start`                | Start if not already running   |
| `caffrey stop`                 | Stop the server                |
| `caffrey status`               | Check if running               |
| `caffrey logs`                 | Tail the log file              |
| `caffrey test`                 | Run in foreground (debug mode) |

### Shell alias (optional)

Add to `~/.bash_aliases` or `~/.zshrc`:

```bash
alias caffrey="~/my-file-server/caffrey"
```

## Environment Variables

| Variable               | Default       | Description                                       |
| ---------------------- | ------------- | ------------------------------------------------- |
| `CFS_PORT`             | `8086`        | Server port                                       |
| `CFS_DIRECTORY`        | `~/my-server` | Root directory to serve                            |
| `CFS_PASSWORD`         | `caffrey`     | **Set your own** — password for delete actions     |
| `CFS_CM_PORT`          | `8089`        | ChartMuseum port                                  |
| `CFS_LOG_DIR`          | `./logs`      | Log file directory                                |
| `CFS_LOG_LEVEL`        | `INFO`        | Logging level (DEBUG, INFO, WARNING)              |
| `CFS_LOG_MAX_MB`       | `50`          | Max log file size before rotation                 |
| `CFS_LOG_BACKUP_COUNT` | `14`          | Number of rotated logs to keep                    |
| `CFS_ARTIFACTORY_URL`  | _(none)_      | Artifactory download URL template                 |
| `CFS_ARTIFACTORY_KEY`  | _(none)_      | **Set your own** — JFrog API key for chart imports |

All variables can be set in a `.env` file in the project root — the launcher loads it automatically.
Never commit `.env` to version control.

## Adding Remote Filers

Edit the `REMOTE_FILERS` dictionary in `config.py`:

```python
REMOTE_FILERS = {
    "my-filer": {
        "label": "My Filer",
        "url": "http://example.com/builds/",
    },
    # ... add more
}
```

Any Apache httpd directory listing server works out of the box.

## API Endpoints

| Method | Path                      | Description                          |
| ------ | ------------------------- | ------------------------------------ |
| POST   | `/__api__/upload`         | Upload files (multipart)             |
| POST   | `/__api__/delete`         | Delete a file/folder (password)      |
| POST   | `/__api__/mkdir`          | Create a new directory               |
| POST   | `/__api__/newfile`        | Create a new empty file              |
| POST   | `/__api__/savefile`       | Save edited file content             |
| POST   | `/__api__/rename`         | Rename a file/folder                 |
| POST   | `/__api__/zip-start`      | Start a background ZIP job           |
| POST   | `/__api__/zip-cancel`     | Cancel a running ZIP job             |
| GET    | `/__api__/zip-progress`   | SSE stream for ZIP progress          |
| GET    | `/__api__/zip-download`   | Download completed ZIP               |
| GET    | `/__api__/favorites`      | List all favorites                   |
| POST   | `/__api__/favorites`      | Add/remove a favorite                |
| GET    | `/__api__/search`         | Recursive file search                |
| GET    | `/__api__/readfile`       | Read file content (for editor)       |
| *      | `/__api__/cm/*`           | Proxy to ChartMuseum API             |

## Project Structure

```
my-file-server/
├── server.py              # HTTP handler, routing, template rendering (~2100 lines)
├── config.py              # Environment variables, constants, remote filer config
├── log_setup.py           # Rotating file logging
├── charts.py              # Helm chart download from Artifactory
├── icons.py               # SVG file-type icon definitions
├── svgs.py                # UI SVG icon constants (star, search, link, etc.)
├── caffrey                # Launcher script (start/stop/restart/logs)
├── static/
│   ├── css/style.css      # Dark + light theme CSS (~1400 lines)
│   └── js/app.js          # Client-side JS: search, favorites, ZIP tray, sort (~900 lines)
├── templates/
│   ├── base.html           # Page wrapper
│   ├── header.html         # Header bar with filers/charts/favorites/theme
│   ├── charts_page.html    # ChartMuseum UI
│   ├── viewer_page.html    # Syntax-highlighted file viewer
│   ├── editor_page.html    # In-browser file editor
│   ├── delete_modal.html   # Delete confirmation dialog
│   ├── input_modal.html    # Rename/create dialog
│   └── import_modal.html   # Artifactory chart import dialog
├── data/
│   └── favorites.json      # Persistent favorites storage
├── requirements.txt
└── README.md
```

## Performance

- **Multi-threaded**: Each request gets its own thread — no blocking
- **Gzip**: HTML responses compressed ~89%, CSS ~82%, JS ~76%
- **ETag caching**: Static assets return `304 Not Modified` when unchanged
- **ZIP streaming**: Background threads with SSE progress — server stays responsive
- **Search**: 5-second timeout + 200-result cap prevents runaway walks on large trees
- **Periodic cleanup**: Daemon thread cleans stale ZIP temp files every 5 minutes

## License

MIT

