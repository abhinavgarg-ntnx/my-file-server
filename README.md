# Caffrey's File Server

A modern, feature-rich HTTP file server with a beautiful dark/light themed web UI.

## Features

- **Dark / Light theme** — one-click toggle, persists across sessions
- **File browser** — directory listing with SVG file-type icons, sizes, timestamps
- **File upload** — drag-and-drop or click-to-browse, uploads to current directory
- **Password-protected delete** — delete files/folders through the UI with a password prompt
- **In-browser file viewer** — view `.log`, `.txt`, `.json`, `.yaml`, `.py`, `.sh` and more with line numbers and syntax coloring
- **Helm chart downloader** — download and extract Helm charts from Artifactory
- **Structured logging** — timed rotating log files with symlink (like production apps)
- **Launcher script** — `caffrey start|stop|restart|status|logs|test`
- **Responsive design** — works on desktop and mobile

## Quick Start

```bash
git clone <repo-url> ~/my-file-server
cd ~/my-file-server
pip install -r requirements.txt   # optional: only for chart downloads

# One command:
./caffrey
```

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

Then you can run `caffrey` from anywhere.

## Environment Variables

| Variable               | Default       | Description                          |
| ---------------------- | ------------- | ------------------------------------ |
| `CFS_PORT`             | `8086`        | Server port                          |
| `CFS_DIRECTORY`        | `~/my-server` | Directory to serve                   |
| `CFS_PASSWORD`         | `caffrey`     | Password for file deletion           |
| `CFS_LOG_DIR`          | `./logs`      | Log file directory                   |
| `CFS_LOG_LEVEL`        | `INFO`        | Logging level (DEBUG, INFO, WARNING) |
| `CFS_LOG_MAX_MB`       | `50`          | Max log file size before rotation    |
| `CFS_LOG_BACKUP_COUNT` | `14`          | Number of rotated logs to keep       |
| `CFS_ARTIFACTORY_URL`  | _(internal)_  | Artifactory download URL template    |
| `CFS_ARTIFACTORY_KEY`  | _(internal)_  | Artifactory API key                  |

You can also create a `.env` file in the project root — the launcher loads it automatically.

## Project Structure

```
my-file-server/
├── server.py           # HTTP handler, routing, template rendering
├── config.py           # Environment variables and constants
├── log_setup.py        # Rotating file logging (nuginix pattern)
├── charts.py           # Helm chart download from Artifactory
├── icons.py            # SVG icon definitions
├── caffrey             # Launcher script (start/stop/restart/logs)
├── static/
│   ├── css/style.css   # Dark + light theme CSS
│   └── js/app.js       # Client-side JavaScript
├── templates/
│   ├── base.html       # Page wrapper
│   ├── header.html     # Header bar partial
│   └── delete_modal.html
├── requirements.txt
└── README.md
```

## License

MIT
