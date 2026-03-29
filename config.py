"""
Centralised configuration — all tunables read from env vars with sensible defaults.
"""

import os
import socket
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# ── Server ─────────────────────────────────────────────────────────────

PORT = int(os.environ.get("CFS_PORT", "8086"))
DIRECTORY = os.environ.get("CFS_DIRECTORY", os.getcwd())
DELETE_PASSWORD = os.environ.get("CFS_PASSWORD", "caffrey")

# ── Logging ────────────────────────────────────────────────────────────

LOG_DIR = Path(os.environ.get("CFS_LOG_DIR", str(BASE_DIR / "logs")))
LOG_LEVEL = os.environ.get("CFS_LOG_LEVEL", "INFO")
LOG_MAX_MB = int(os.environ.get("CFS_LOG_MAX_MB", "50"))
LOG_BACKUP_COUNT = int(os.environ.get("CFS_LOG_BACKUP_COUNT", "14"))
LOG_ROTATE_WHEN = os.environ.get("CFS_LOG_ROTATE_WHEN", "midnight")

# ── ChartMuseum ───────────────────────────────────────────────────────

CM_PORT = int(os.environ.get("CFS_CM_PORT", "8089"))
CM_STORAGE_DIR = os.environ.get("CFS_CM_STORAGE", "")

# ── Artifactory (chart downloads) ─────────────────────────────────────

ARTIFACTORY_URL = os.environ.get(
    "CFS_ARTIFACTORY_URL",
    "https://artifactory.dyn.ntnxdpro.com/ui/api/v1/download"
    "?repoKey=canaveral-helm&path={name}%2F{name}-{version}.tgz",
)
ARTIFACTORY_API_KEY = os.environ.get(
    "CFS_ARTIFACTORY_KEY",
    "REPLACE_WITH_YOUR_API_KEY",
)

# ── Hostname (auto-detected) ──────────────────────────────────────────

_hostname = socket.getfqdn()
HOSTNAME = _hostname if "." in _hostname else socket.gethostname()
try:
    LOCAL_IP = socket.gethostbyname(socket.gethostname())
except socket.gaierror:
    LOCAL_IP = "localhost"

# ── File type constants ────────────────────────────────────────────────

VIEWABLE_EXTENSIONS = {
    ".log", ".out", ".err", ".txt", ".json", ".yaml", ".yml", ".csv",
    ".xml", ".md", ".ini", ".cfg", ".conf", ".properties", ".sh",
    ".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".rs",
    ".c", ".cpp", ".h", ".rb", ".php", ".sql", ".toml",
}

INLINE_EXTENSIONS = {
    ".log", ".out", ".err", ".txt", ".json", ".yaml", ".yml", ".csv",
    ".tsv", ".xml", ".md", ".ini", ".cfg", ".conf", ".properties", ".sh",
}

EXT_LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".json": "json", ".html": "markup", ".xml": "markup",
    ".css": "css", ".yaml": "yaml", ".yml": "yaml",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".sql": "sql", ".go": "go", ".java": "java",
    ".c": "c", ".cpp": "cpp", ".rs": "rust", ".rb": "ruby",
    ".php": "php", ".md": "markdown", ".toml": "toml",
    ".ini": "ini", ".cfg": "ini", ".conf": "ini",
    ".properties": "properties",
}

SYSTEM_DIRS = {"charts", "helm-charts"}

# ── Remote filers (Apache httpd directory listings) ───────────────────

REMOTE_FILERS = {
    "pc-builds": {
        "label": "PC Builds",
        "url": "http://endor.dyn.nutanix.com/builds/pc-builds/master/",
    },
    "ncc-builds": {
        "label": "NCC Builds",
        "url": "http://endor.dyn.nutanix.com/builds/ncc-builds/master/",
    },
    "msp-platform": {
        "label": "MSP Platform",
        "url": "http://phx-fs.corp.nutanix.com/releases/MicroservicesPlatform/",
    },
    "ncm-filer": {
        "label": "NCM Filer",
        "url": "http://ncmfiler.nutanixqa.com/LCM/",
    },
    "lcm-cci": {
        "label": "LCM CCI Builds",
        "url": "http://builds.dyn.nutanix.com/lcm-cci-builds/",
    },
    "nutanix-central": {
        "label": "Nutanix Central",
        "url": "http://endor.dyn.nutanix.com/GoldImages/nutanix_central/",
    },
    "calm-filer": {
        "label": "CALM Filer",
        "url": "http://10.40.64.33/GoldImages/",
    },
}
