"""
SVG icon definitions and file-type → icon mapping.
"""

import os


def _icon(stroke, paths, fill="none", fill_opacity="0"):
    return (
        f'<svg class="fi-svg" viewBox="0 0 24 24" fill="{fill}" '
        f'fill-opacity="{fill_opacity}" stroke="{stroke}" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    )


_FILE_BASE = (
    '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>'
    '<path d="M14 2v6h6"/>'
)

ICONS = {
    "folder": _icon(
        "#f59e0b",
        '<path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>',
        fill="#f59e0b",
        fill_opacity="0.15",
    ),
    "parent": (
        '<svg class="fi-svg" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M11 17l-5-5 5-5"/><path d="M18 17l-5-5 5-5"/></svg>'
    ),
    "code": _icon(
        "#60a5fa", _FILE_BASE + '<path d="M10 12l-2 2 2 2"/><path d="M14 12l2 2-2 2"/>'
    ),
    "data": _icon(
        "#34d399",
        _FILE_BASE
        + '<path d="M8 13h2"/><path d="M8 17h2"/><path d="M14 13h2"/><path d="M14 17h2"/>',
    ),
    "text": _icon(
        "#94a3b8",
        _FILE_BASE + '<path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
    ),
    "archive": _icon(
        "#fb923c",
        _FILE_BASE
        + '<path d="M10 12h4"/><path d="M10 16h4"/><rect x="10" y="12" width="4" height="4" rx="0.5" fill="#fb923c" fill-opacity="0.15"/>',
    ),
    "image": _icon(
        "#a78bfa",
        _FILE_BASE
        + '<circle cx="10" cy="13" r="2"/><path d="M20 17l-3.5-3.5a2 2 0 00-2.83 0L8 19"/>',
    ),
    "config": _icon(
        "#2dd4bf",
        _FILE_BASE
        + '<circle cx="12" cy="15" r="2"/><path d="M12 11v2"/><path d="M12 17v2"/>',
    ),
    "shell": _icon(
        "#4ade80", _FILE_BASE + '<path d="M8 15l2 2-2 2"/><path d="M14 19h2"/>'
    ),
    "markdown": _icon(
        "#818cf8",
        _FILE_BASE
        + '<path d="M7 13v4l2.5-2.5L12 17v-4"/><path d="M15 13v4"/><path d="M17 15h-4"/>',
    ),
    "default": _icon("var(--text-muted)", _FILE_BASE),
}

EXT_ICON_MAP = {
    ".py": "code",
    ".pyw": "code",
    ".js": "code",
    ".jsx": "code",
    ".ts": "code",
    ".tsx": "code",
    ".java": "code",
    ".go": "code",
    ".rs": "code",
    ".c": "code",
    ".cpp": "code",
    ".h": "code",
    ".rb": "code",
    ".php": "code",
    ".swift": "code",
    ".kt": "code",
    ".html": "code",
    ".css": "code",
    ".scss": "code",
    ".vue": "code",
    ".json": "data",
    ".csv": "data",
    ".tsv": "data",
    ".xml": "data",
    ".sql": "data",
    ".toml": "data",
    ".txt": "text",
    ".log": "text",
    ".out": "text",
    ".err": "text",
    ".yaml": "config",
    ".yml": "config",
    ".ini": "config",
    ".cfg": "config",
    ".conf": "config",
    ".properties": "config",
    ".env": "config",
    ".md": "markdown",
    ".mdx": "markdown",
    ".rst": "markdown",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".fish": "shell",
    ".tgz": "archive",
    ".tar": "archive",
    ".gz": "archive",
    ".zip": "archive",
    ".bz2": "archive",
    ".xz": "archive",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".svg": "image",
    ".webp": "image",
}


def get_icon(filename, is_dir=False):
    """Return the SVG icon markup for a file or directory."""
    if is_dir:
        return ICONS["folder"]
    ext = os.path.splitext(filename)[1].lower()
    return ICONS.get(EXT_ICON_MAP.get(ext, "default"), ICONS["default"])
