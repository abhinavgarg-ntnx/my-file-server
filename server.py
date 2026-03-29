#!/usr/bin/env python3
"""
Caffrey's File Server — main HTTP handler and entry point.
"""

import http.server
import http.client
import socketserver
import os
import sys
import json
import shutil
import logging
import urllib.parse
import urllib.request
import urllib.error
import html as html_module
from datetime import datetime
from http import HTTPStatus
from functools import partial

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    try:
        import cgi
    except ImportError:
        cgi = None

from config import (
    STATIC_DIR,
    TEMPLATES_DIR,
    PORT,
    DIRECTORY,
    DELETE_PASSWORD,
    HOSTNAME,
    LOCAL_IP,
    VIEWABLE_EXTENSIONS,
    INLINE_EXTENSIONS,
    CM_PORT,
)
from icons import get_icon, ICONS
from charts import download_and_extract_chart, HAS_REQUESTS

log = logging.getLogger(__name__)

# ── Template Engine ────────────────────────────────────────────────────

_template_cache = {}


def _load_template(name):
    """Load an HTML template from the templates/ directory (cached)."""
    if name not in _template_cache:
        path = TEMPLATES_DIR / name
        _template_cache[name] = path.read_text(encoding="utf-8")
    return _template_cache[name]


def render_template(name, **kwargs):
    """Render a template, replacing {{KEY}} placeholders with values."""
    html = _load_template(name)
    for key, value in kwargs.items():
        html = html.replace("{{" + key.upper() + "}}", str(value))
    # Clear any remaining unreplaced placeholders
    import re

    html = re.sub(r"\{\{[A-Z_]+\}\}", "", html)
    return html


_CHARTS_BTN_HTML = (
    '<a href="/__charts__" class="hdr-btn" title="Helm Charts">'
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24"><path stroke-linecap="round"'
    ' stroke-linejoin="round" d="M3 16.5v2.25'
    "A2.25 2.25 0 0 0 5.25 21h13.5"
    "A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12L12 16.5"
    'm0 0L7.5 12m4.5 4.5V3"/></svg> Charts</a>'
)


def _render_header(show_upload=True, show_charts=True):
    """Render the header partial."""
    upload_btn = ""
    if show_upload:
        upload_btn = (
            '<button class="hdr-btn" onclick="toggleUpload()">'
            '<svg fill="none" stroke="currentColor" stroke-width="2"'
            ' viewBox="0 0 24 24"><path stroke-linecap="round"'
            ' stroke-linejoin="round" d="M3 16.5v2.25'
            "A2.25 2.25 0 0 0 5.25 21h13.5"
            "A2.25 2.25 0 0 0 21 18.75V16.5"
            "m-13.5-9L12 3m0 0l4.5 4.5"
            'M12 3v13.5"/></svg> Upload</button>'
        )
    charts_btn = _CHARTS_BTN_HTML if show_charts else ""
    return render_template(
        "header.html",
        UPLOAD_BUTTON=upload_btn,
        CHARTS_BUTTON=charts_btn,
    )


def _render_page(
    title, content, header_html=None, modals="", extra_head="", extra_scripts=""
):
    """Render a full page using the base template."""
    if header_html is None:
        header_html = _render_header()
    return render_template(
        "base.html",
        TITLE=html_module.escape(title),
        HEADER=header_html,
        CONTENT=content,
        MODALS=modals,
        EXTRA_HEAD=extra_head,
        EXTRA_SCRIPTS=extra_scripts,
    )


# ── Inline SVG constants used in HTML building ────────────────────────

SVG_HOME = (
    '<svg width="14" height="14" fill="none" stroke="currentColor"'
    ' stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75'
    " 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4"
    ".875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1"
    ".125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8."
    '25 21h8.25"/></svg>'
)
SVG_VIEW = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36'
    " 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07"
    ".431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8"
    '.573-3.007-9.963-7.178z"/>'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>'
)
SVG_DOWNLOAD = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25'
    " 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5"
    ' 4.5V3"/></svg>'
)
_DEL_D = (
    "M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052"
    ".682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25"
    " 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4"
    ".772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12"
    " .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 01"
    "3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51"
    ".964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.2"
    "01v.916m7.5 0a48.667 48.667 0 00-7.5 0"
)
SVG_DELETE = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    f'd="{_DEL_D}"/></svg>'
)
SVG_BACK = (
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"/></svg>'
)
_EDIT_D = (
    "M16.862 4.487l1.687-1.688a1.875 1.875 0 1 1 2.652 2.652"
    "L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685"
    "a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931z"
    "M19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21"
    "H5.25A2.25 2.25 0 0 1 3 18.75V8.25"
    "A2.25 2.25 0 0 1 5.25 6H10"
)
SVG_EDIT = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    f' d="{_EDIT_D}"/></svg>'
)
SVG_UPLOAD_CLOUD_SM = (
    '<svg width="16" height="16" fill="none" stroke="currentColor"'
    ' stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round"'
    ' stroke-linejoin="round" d="M3 16.5v2.25'
    "A2.25 2.25 0 0 0 5.25 21h13.5"
    "A2.25 2.25 0 0 0 21 18.75V16.5"
    "m-13.5-9L12 3m0 0l4.5 4.5"
    'M12 3v13.5"/></svg>'
)
SVG_UPLOAD_CLOUD = (
    '<svg width="48" height="48" fill="none" stroke="currentColor"'
    ' stroke-width="1.5" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3'
    "M6.75 19.5"
    "a4.5 4.5 0 0 1-1.41-8.775"
    " 5.25 5.25 0 0 1 10.338-2.32"
    " 3.75 3.75 0 0 1 3.572 5.345"
    ' 4.5 4.5 0 0 1-2.76 5.75"/></svg>'
)

# ── HTTP Handler ───────────────────────────────────────────────────────

# MIME types for static assets
_STATIC_MIME = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class FileServerHandler(http.server.SimpleHTTPRequestHandler):

    server_dir = "."

    def __init__(self, *args, directory=None, **kwargs):
        self.server_dir = directory or "."
        super().__init__(*args, directory=directory, **kwargs)

    # ── Routing ──────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/__static__/"):
            return self._serve_static(path[len("/__static__/") :])  # noqa: E203
        if path == "/__charts__":
            return self._serve_charts_page()
        if path.startswith("/__viewer__"):
            qs = urllib.parse.parse_qs(parsed.query)
            return self._serve_viewer_page(qs.get("file", [""])[0])
        if path.startswith("/__editor__"):
            qs = urllib.parse.parse_qs(parsed.query)
            return self._serve_editor_page(qs.get("file", [""])[0])
        if path == "/__api__/readfile":
            qs = urllib.parse.parse_qs(parsed.query)
            return self._handle_readfile(qs.get("path", [""])[0])
        if path.startswith("/__api__/cm/"):
            return self._proxy_cm("GET", path[len("/__api__/cm") :])  # noqa: E203

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/__api__/upload":
            return self._handle_upload()
        if path == "/__api__/delete":
            return self._handle_delete()
        if path == "/__api__/mkdir":
            return self._handle_mkdir()
        if path == "/__api__/newfile":
            return self._handle_newfile()
        if path == "/__api__/savefile":
            return self._handle_savefile()
        if path == "/__api__/chart-download":
            return self._handle_chart_download()
        if path.startswith("/__api__/cm/"):
            return self._proxy_cm("POST", path[len("/__api__/cm") :])  # noqa: E203

        self.send_error(404, "Not found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/__api__/cm/"):
            return self._proxy_cm("DELETE", path[len("/__api__/cm") :])  # noqa: E203

        self.send_error(404, "Not found")

    # ── ChartMuseum Proxy ─────────────────────────────────────────

    def _proxy_cm(self, method, cm_path):
        """Forward a request to the local ChartMuseum instance."""
        body = None
        ct = self.headers.get("Content-Type", "")
        if method in ("POST", "PUT"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else None

        try:
            conn = http.client.HTTPConnection("127.0.0.1", CM_PORT, timeout=60)
            headers = {}
            if ct:
                headers["Content-Type"] = ct
            conn.request(method, cm_path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            self.send_response(resp.status)
            for hdr in ("Content-Type",):
                val = resp.getheader(hdr)
                if val:
                    self.send_header(hdr, val)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            conn.close()
        except ConnectionRefusedError:
            self._send_json(
                {
                    "error": "ChartMuseum is not running on port "
                    f"{CM_PORT}. Start it with: caffrey restart"
                },
                502,
            )
        except Exception as exc:
            log.exception("ChartMuseum proxy error")
            self._send_json({"error": str(exc)}, 502)

    # ── Static file serving (app assets) ─────────────────────────

    def _serve_static(self, rel_path):
        """Serve files from the application's static/ directory."""
        safe = os.path.normpath(rel_path).lstrip("/").lstrip("\\")
        local = STATIC_DIR / safe

        if not local.is_file() or ".." in rel_path:
            self.send_error(404, "Static file not found")
            return

        ext = os.path.splitext(safe)[1].lower()
        ctype = _STATIC_MIME.get(ext, "application/octet-stream")

        data = local.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    # ── Directory Listing ────────────────────────────────────────

    def list_directory(self, path):
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None

        entries.sort(
            key=lambda a: (not os.path.isdir(os.path.join(path, a)), a.lower())
        )
        displaypath = urllib.parse.unquote(self.path, errors="surrogatepass")
        is_cm_dir = self._is_cm_protected(path)

        # Breadcrumb
        bc = f'<a class="bc-chip" href="/">{SVG_HOME} Home</a>'
        if displaypath != "/":
            parts = [p for p in displaypath.strip("/").split("/") if p]
            for i, part in enumerate(parts):
                qp = (
                    "/"
                    + "/".join(
                        urllib.parse.quote(p, errors="surrogatepass")
                        for p in parts[: i + 1]
                    )
                    + "/"
                )
                bc += (
                    '<span class="bc-sep">/</span>'
                    f'<a class="bc-chip" href="{qp}">'
                    f"{html_module.escape(part)}</a>"
                )

        # Upload section (hidden in CM dirs)
        upload_html = ""
        show_upload = not is_cm_dir
        if show_upload:
            upload_html = (
                f'<div id="upload-section" class="upload-section">'
                f'  <div id="upload-zone" class="upload-zone">'
                f'    <div class="upload-icon">{SVG_UPLOAD_CLOUD}</div>'
                f"    <p>Drag files here or click to browse</p>"
                f'    <input type="file" id="upload-input" multiple>'
                f'    <input type="hidden" id="upload-dir"'
                f'     value="{html_module.escape(displaypath)}">'
                f"  </div>"
                f'  <div id="upload-progress" class="upload-progress">'
                f'    <div class="progress-bar">'
                f'<div id="progress-fill" class="progress-fill"></div></div>'
                f"  </div>"
                f"</div>"
            )

        # Dir toolbar (new folder / new file)
        dir_toolbar = ""
        if show_upload:
            esc_dp = html_module.escape(displaypath, quote=True)
            dir_toolbar = (
                f'<div class="dir-toolbar">'
                f'  <button class="hdr-btn" onclick="promptNewFolder(\'{esc_dp}\')">'
                f"    + Folder</button>"
                f'  <button class="hdr-btn" onclick="promptNewFile(\'{esc_dp}\')">'
                f"    + File</button>"
                f"</div>"
            )
        elif is_cm_dir:
            dir_toolbar = (
                '<div class="dir-toolbar">'
                '<span class="cm-note-warn" style="padding:0">'
                "Read-only &mdash; managed by ChartMuseum</span>"
                "</div>"
            )

        # File items
        items = []

        if displaypath != "/":
            parent = os.path.dirname(displaypath.rstrip("/"))
            if not parent or parent == "/":
                parent_url = "/"
            else:
                pp = [p for p in parent.split("/") if p]
                parent_url = (
                    "/"
                    + "/".join(
                        urllib.parse.quote(p, errors="surrogatepass") for p in pp
                    )
                    + "/"
                )
            items.append(
                f'<li class="file-item">'
                f'<a class="file-link" href="{parent_url}">'
                f'{ICONS["parent"]}'
                f'<span class="file-name">.. (Parent Directory)</span>'
                f"</a></li>"
            )

        for name in entries:
            fullname = os.path.join(path, name)
            is_dir = os.path.isdir(fullname)
            icon = get_icon(name, is_dir)
            display = name + "/" if is_dir else name

            rel = (displaypath.rstrip("/") + "/" + name) if displaypath != "/" else name
            parts = [p for p in rel.split("/") if p]
            link = "/" + "/".join(
                urllib.parse.quote(p, errors="surrogatepass") for p in parts
            )
            if is_dir:
                link += "/"

            ext = os.path.splitext(name)[1].lower()
            is_viewable = not is_dir and ext in VIEWABLE_EXTENSIONS
            is_editable = is_viewable and not is_cm_dir

            file_link = (
                f"/__viewer__?file={urllib.parse.quote(link, safe='/')}"
                if is_viewable
                else link
            )

            try:
                size_str = (
                    "-" if is_dir else self._format_size(os.path.getsize(fullname))
                )
                mtime_str = datetime.fromtimestamp(os.path.getmtime(fullname)).strftime(
                    "%Y-%m-%d %H:%M"
                )
            except Exception:
                size_str, mtime_str = "-", "-"

            actions = ""
            if is_viewable:
                vlink = urllib.parse.quote(link, safe="/")
                actions += (
                    f'<button class="act-btn view-btn" title="View"'
                    f' onclick="event.preventDefault();'
                    f"location.href='/__viewer__?file={vlink}'\">"
                    f"{SVG_VIEW}</button>"
                )
            if is_editable:
                elink = urllib.parse.quote(link, safe="/")
                actions += (
                    f'<button class="act-btn view-btn" title="Edit"'
                    f' onclick="event.preventDefault();'
                    f"location.href='/__editor__?file={elink}'\">"
                    f"{SVG_EDIT}</button>"
                )
            if not is_dir:
                actions += (
                    f'<a class="act-btn dl-btn" title="Download"'
                    f' href="{link}" download>{SVG_DOWNLOAD}</a>'
                )
            if not is_cm_dir:
                esc_link = html_module.escape(link, quote=True).replace("'", "\\'")
                esc_disp = html_module.escape(display, quote=True).replace("'", "\\'")
                actions += (
                    f'<button class="act-btn del-btn" title="Delete"'
                    f' onclick="event.preventDefault();event.stopPropagation();'
                    f"showDeleteModal('{esc_link}','{esc_disp}')\">"
                    f"{SVG_DELETE}</button>"
                )

            esc_name = html_module.escape(display)
            items.append(
                f'<li class="file-item">'
                f'<a class="file-link" href="{file_link}">{icon}'
                f'<span class="file-name">{esc_name}</span></a>'
                f'<div class="file-meta">'
                f"<span>{size_str}</span>"
                f"<span>{mtime_str}</span></div>"
                f'<div class="file-actions">{actions}</div>'
                f"</li>"
            )

        if not entries:
            items.append('<li class="empty-state">This directory is empty</li>')

        content = (
            f'<div class="breadcrumb">{bc}</div>'
            f"{dir_toolbar}"
            f"{upload_html}"
            f'<div class="file-list-wrap">'
            f'<ul class="file-list">{"".join(items)}</ul>'
            f"</div>"
        )

        delete_modal = _load_template("delete_modal.html") if not is_cm_dir else ""
        html = _render_page(
            f"Caffrey's Treasure — {displaypath}",
            content,
            header_html=_render_header(show_upload=show_upload),
            modals=delete_modal,
        )

        encoded = html.encode("utf-8", "surrogateescape")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        return None

    # ── File Viewer ──────────────────────────────────────────────

    def _serve_viewer_page(self, file_path):
        if not file_path:
            self.send_error(400, "Missing file parameter")
            return

        local_path = self.translate_path(file_path)
        if not os.path.isfile(local_path):
            self.send_error(404, "File not found")
            return

        filename = os.path.basename(local_path)
        ext = os.path.splitext(filename)[1].lower()

        max_size = 2 * 1024 * 1024
        try:
            file_size = os.path.getsize(local_path)
            truncated = file_size > max_size
            with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_size)
        except Exception as e:
            self.send_error(500, f"Cannot read file: {e}")
            return

        size_str = self._format_size(file_size)
        mtime_str = datetime.fromtimestamp(os.path.getmtime(local_path)).strftime(
            "%Y-%m-%d %H:%M"
        )

        lines = content.split("\n")
        viewer_lines = []
        for i, line in enumerate(lines, 1):
            escaped = html_module.escape(line)
            viewer_lines.append(
                f'<div class="viewer-line"><span class="viewer-ln">{i}</span>'
                f'<span class="viewer-code">{escaped}</span></div>'
            )
        if truncated:
            viewer_lines.append(
                f'<div class="viewer-line"><span class="viewer-ln">...</span>'
                f'<span class="viewer-code" style="color:var(--warning)">'
                f"[File truncated — showing first {self._format_size(max_size)} of {size_str}]</span></div>"
            )

        parent_dir = os.path.dirname(file_path.rstrip("/"))
        parent_url = parent_dir + "/" if parent_dir and parent_dir != "/" else "/"

        extra_scripts = ""
        if ext == ".json":
            extra_scripts = (
                "<script>window.enhanceJsonViewer && enhanceJsonViewer();</script>"
            )

        page_content = (
            f'<div class="viewer-header">'
            f'  <a href="{parent_url}" class="hdr-btn">{SVG_BACK} Back</a>'
            f'  <div style="flex:1">'
            f'    <div style="font-weight:600;font-size:16px">{html_module.escape(filename)}</div>'
            f'    <div class="file-info">{size_str} &middot; Modified {mtime_str}</div>'
            f"  </div>"
            f'  <a href="{file_path}" class="hdr-btn" download>{SVG_DOWNLOAD} Download</a>'
            f"</div>"
            f'<div class="viewer-wrap">'
            f'  <div class="viewer-content">{"".join(viewer_lines)}</div>'
            f"</div>"
        )

        html = _render_page(
            f"View — {filename}",
            page_content,
            header_html=_render_header(show_upload=False),
            extra_scripts=extra_scripts,
        )

        encoded = html.encode("utf-8", "surrogateescape")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    # ── Charts Page ──────────────────────────────────────────────

    def _serve_charts_page(self):
        repo_url = f"http://{HOSTNAME}:{CM_PORT}"

        requests_note = ""
        if not HAS_REQUESTS:
            requests_note = (
                '<p class="cm-note-warn">'
                "Install <code>requests</code> for Artifactory import: "
                "<code>pip install requests</code></p>"
            )

        svg_copy = (
            '<svg width="14" height="14" fill="none"'
            ' stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
            '<path stroke-linecap="round" stroke-linejoin="round"'
            ' d="M8.25 7.5V6.108c0-1.135.845-2.098 1.976-2.192'
            ".373-.03.748-.057 1.123-.08M15.75 18H18a2.25 2.25 0"
            " 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192"
            "a48.424 48.424 0 0 0-1.123-.08M15.75 18.75v-1.875a3.375"
            " 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125"
            "-1.125v-1.5A3.375 3.375 0 0 0 6.375 7.5H5.25m11.9-3.664"
            "A2.251 2.251 0 0 0 15 2.25h-1.5a2.251 2.251 0 0 0-2.15"
            " 1.586m5.8 0c.065.21.1.433.1.664v.75h-6V4.5c0-.231.035"
            "-.454.1-.664M6.75 7.5H4.875c-.621 0-1.125.504-1.125"
            " 1.125v12c0 .621.504 1.125 1.125 1.125h9.75c.621 0"
            ' 1.125-.504 1.125-1.125V16.5a9 9 0 0 0-9-9z"/></svg>'
        )

        page_content = (
            # ── Top bar: back + title + repo command
            '<div class="cm-topbar">'
            '  <div class="cm-topbar-left">'
            f'    <a href="/" class="cm-back-btn" title="Back to Files">'
            f"      {SVG_BACK}</a>"
            "    <div>"
            '      <h2 class="cm-title">Helm Chart Repository</h2>'
            '      <p class="cm-subtitle">'
            "        Powered by ChartMuseum</p>"
            "    </div>"
            "  </div>"
            '  <div class="cm-repo-cmd">'
            "    <label>Add this repo</label>"
            f'    <div class="cm-cmd-row">'
            f'      <code id="repo-cmd">'
            f"helm repo add caffrey {repo_url}</code>"
            f'      <button class="cm-copy-btn" onclick="copyRepoCmd()"'
            f'       title="Copy">{svg_copy}</button>'
            "    </div>"
            "  </div>"
            "</div>"
            # ── Toolbar: health + search + buttons
            '<div class="cm-controls">'
            '  <div class="cm-health" id="cm-health">'
            '    <span class="cm-dot" id="cm-dot"></span>'
            '    <span id="cm-health-text">Checking...</span>'
            "  </div>"
            '  <div class="cm-toolbar">'
            '    <input type="search" id="cm-search"'
            '     placeholder="Search charts..." autocomplete="off">'
            '    <span class="cm-count" id="cm-count"></span>'
            '    <button class="hdr-btn" onclick="cmToggleUpload()">'
            f"      {SVG_UPLOAD_CLOUD_SM} Upload</button>"
            '    <button class="hdr-btn" onclick="cmShowImport()">'
            f"      {SVG_DOWNLOAD} Import</button>"
            "  </div>"
            "</div>"
            # ── Upload zone (hidden, toggled)
            '<div id="cm-upload-section" class="upload-section">'
            '  <div class="cm-upload-zone" id="cm-upload-zone">'
            '    <div class="cm-upload-icon">'
            '      <svg width="28" height="28" fill="none"'
            '       stroke="currentColor" stroke-width="1.5"'
            '       viewBox="0 0 24 24"><path stroke-linecap="round"'
            '       stroke-linejoin="round"'
            '       d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5'
            "       A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3"
            '       m0 0l4.5 4.5M12 3v13.5"/></svg></div>'
            "    <p>Drop <code>.tgz</code> chart here or browse</p>"
            '    <input type="file" id="cm-upload-input"'
            '     accept=".tgz,.gz">'
            "  </div>"
            '  <div id="cm-upload-status" class="chart-status"></div>'
            "</div>"
            # ── Charts table
            '<div class="cm-card">'
            '  <table class="cm-table">'
            "    <thead><tr>"
            "      <th>Chart</th><th>Latest</th>"
            "      <th>App Version</th><th>Description</th>"
            "      <th></th>"
            "    </tr></thead>"
            '    <tbody id="cm-body">'
            '      <tr><td colspan="5" class="cm-loading">'
            "        Loading...</td></tr>"
            "    </tbody>"
            "  </table>"
            "</div>"
        )

        import_modal = (
            '<div id="import-modal" class="modal-overlay"'
            ' onclick="if(event.target===this)cmCloseImport()">'
            '  <div class="modal">'
            "    <h3>Import from Artifactory</h3>"
            "    <p>Download a Helm chart .tgz and optionally push"
            "      it to ChartMuseum.</p>"
            f"    {requests_note}"
            '    <div class="form-group" style="margin-bottom:10px">'
            "      <label>Chart Name</label>"
            '      <input type="text" id="chart-name"'
            '       placeholder="e.g. ncm-base"></div>'
            '    <div class="form-group" style="margin-bottom:14px">'
            "      <label>Version</label>"
            '      <input type="text" id="chart-version"'
            '       placeholder="e.g. 2.0.11"></div>'
            '    <div id="chart-status" class="chart-status"></div>'
            '    <div class="modal-btns">'
            '      <button class="modal-btn cancel"'
            '       onclick="cmCloseImport()">Cancel</button>'
            '      <button class="modal-btn cancel"'
            '       onclick="downloadChart(false)">Download Only</button>'
            '      <button class="hdr-btn accent"'
            '       onclick="downloadChart(true)">'
            f"       {SVG_DOWNLOAD} Import &amp; Push</button>"
            "    </div>"
            "  </div>"
            "</div>"
        )

        html = _render_page(
            "Charts — Caffrey's Treasure",
            page_content,
            header_html=_render_header(show_upload=False, show_charts=False),
            modals=import_modal,
            extra_scripts=('<script src="/__static__/js/charts.js"></script>'),
        )

        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    # ── API Handlers ─────────────────────────────────────────────

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length))

    def _handle_upload(self):
        if cgi is None:
            self._send_json(
                {
                    "success": False,
                    "error": "Upload not supported (cgi module unavailable)",
                },
                500,
            )
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json(
                {"success": False, "error": "Expected multipart/form-data"}, 400
            )
            return

        try:
            environ = {
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            }
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers, environ=environ
            )

            upload_path = form.getvalue("upload_path", "/")
            target_dir = self.translate_path(upload_path)
            if self._is_cm_protected(target_dir):
                self._send_json(
                    {"success": False, "error": "Cannot write to chart repository"}, 403
                )
                return
            os.makedirs(target_dir, exist_ok=True)

            file_items = form["files"] if "files" in form else []
            if not isinstance(file_items, list):
                file_items = [file_items]

            uploaded = []
            for item in file_items:
                if item.filename:
                    filename = os.path.basename(item.filename)
                    dest = os.path.join(target_dir, filename)
                    with open(dest, "wb") as f:
                        shutil.copyfileobj(item.file, f)
                    uploaded.append(filename)
                    log.info("Uploaded %s to %s", filename, target_dir)

            self._send_json({"success": True, "files": uploaded})
        except Exception as e:
            log.exception("Upload failed")
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_delete(self):
        try:
            data = self._read_json_body()
        except Exception:
            self._send_json({"success": False, "error": "Invalid request body"}, 400)
            return

        password = data.get("password", "")
        file_path = data.get("path", "")

        if password != DELETE_PASSWORD:
            log.warning("Delete rejected: wrong password for %s", file_path)
            self._send_json({"success": False, "error": "Invalid password"}, 403)
            return

        if not file_path:
            self._send_json({"success": False, "error": "No path specified"}, 400)
            return

        local_path = self.translate_path(file_path)
        if self._is_cm_protected(local_path):
            self._send_json(
                {"success": False, "error": "Cannot delete chart repo files"}, 403
            )
            return
        real_served = os.path.realpath(self.server_dir)
        real_target = os.path.realpath(local_path)
        if not real_target.startswith(real_served):
            self._send_json(
                {"success": False, "error": "Path outside served directory"}, 403
            )
            return

        if not os.path.exists(local_path):
            self._send_json({"success": False, "error": "File not found"}, 404)
            return

        try:
            if os.path.isdir(local_path):
                shutil.rmtree(local_path)
            else:
                os.remove(local_path)
            log.info("Deleted %s", local_path)
            self._send_json({"success": True})
        except Exception as e:
            log.exception("Delete failed for %s", local_path)
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_chart_download(self):
        try:
            data = self._read_json_body()
        except Exception:
            self._send_json({"success": False, "error": "Invalid request body"}, 400)
            return

        name = data.get("name", "").strip()
        version = data.get("version", "").strip()
        should_push = data.get("push", True)

        if not name or not version:
            self._send_json(
                {"success": False, "error": "Chart name and version required"}, 400
            )
            return

        charts_dir = os.path.join(self.server_dir, "charts")
        os.makedirs(charts_dir, exist_ok=True)

        try:
            extract_dir, error = download_and_extract_chart(name, version, charts_dir)
            if error:
                self._send_json({"success": False, "error": error}, 500)
                return

            result = {
                "success": True,
                "path": f"/charts/{name}-{version}/",
                "chartmuseum": False,
            }

            tgz_path = os.path.join(charts_dir, f"{name}-{version}.tgz")
            if should_push and os.path.exists(tgz_path):
                result["chartmuseum"] = self._push_to_chartmuseum(
                    tgz_path, name, version
                )

            self._send_json(result)
        except Exception as e:
            log.exception("Chart download failed for %s-%s", name, version)
            self._send_json({"success": False, "error": str(e)}, 500)

    def _push_to_chartmuseum(self, tgz_path, name, version):
        """Upload a .tgz chart file to the local ChartMuseum instance."""
        try:
            with open(tgz_path, "rb") as f:
                chart_data = f.read()
            boundary = "----CaffreyChartBoundary9876"
            filename = os.path.basename(tgz_path)
            header_part = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="chart"; '
                f'filename="{filename}"\r\n'
                f"Content-Type: application/gzip\r\n\r\n"
            ).encode()
            footer = f"\r\n--{boundary}--\r\n".encode()
            body = header_part + chart_data + footer
            conn = http.client.HTTPConnection("127.0.0.1", CM_PORT, timeout=30)
            conn.request(
                "POST",
                "/api/charts",
                body=body,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Content-Length": str(len(body)),
                },
            )
            resp = conn.getresponse()
            resp_body = resp.read()
            conn.close()
            if resp.status in (200, 201):
                resp_data = json.loads(resp_body)
                if resp_data.get("saved"):
                    log.info("Pushed %s-%s to ChartMuseum", name, version)
                    return True
            log.warning(
                "ChartMuseum push returned %s: %s", resp.status, resp_body[:200]
            )
            return False
        except Exception:
            log.exception("Failed to push %s-%s to ChartMuseum", name, version)
            return False

    # ── File Operations (mkdir, newfile, save, read, edit) ──────

    def _is_cm_protected(self, local_path):
        """Return True if path is inside ChartMuseum storage."""
        cm_dir = os.path.join(self.server_dir, "helm-charts")
        real_cm = os.path.realpath(cm_dir)
        real_target = os.path.realpath(local_path)
        return real_target.startswith(real_cm)

    def _safe_local(self, rel_path):
        """Resolve a relative URL path to a local path, validating it."""
        local = self.translate_path(rel_path)
        real_served = os.path.realpath(self.server_dir)
        real_target = os.path.realpath(local)
        if not real_target.startswith(real_served):
            return None
        return local

    def _handle_mkdir(self):
        try:
            data = self._read_json_body()
        except Exception:
            self._send_json({"success": False, "error": "Invalid body"}, 400)
            return
        rel_path = data.get("path", "").strip()
        if not rel_path:
            self._send_json({"success": False, "error": "Path required"}, 400)
            return
        local = self._safe_local(rel_path)
        if not local:
            self._send_json({"success": False, "error": "Invalid path"}, 403)
            return
        if self._is_cm_protected(local):
            self._send_json(
                {"success": False, "error": "Cannot write to chart repository"}, 403
            )
            return
        try:
            os.makedirs(local, exist_ok=True)
            log.info("Created directory %s", local)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_newfile(self):
        try:
            data = self._read_json_body()
        except Exception:
            self._send_json({"success": False, "error": "Invalid body"}, 400)
            return
        rel_path = data.get("path", "").strip()
        content = data.get("content", "")
        if not rel_path:
            self._send_json({"success": False, "error": "Path required"}, 400)
            return
        local = self._safe_local(rel_path)
        if not local:
            self._send_json({"success": False, "error": "Invalid path"}, 403)
            return
        if self._is_cm_protected(local):
            self._send_json(
                {"success": False, "error": "Cannot write to chart repository"}, 403
            )
            return
        if os.path.exists(local):
            self._send_json({"success": False, "error": "File already exists"}, 409)
            return
        try:
            os.makedirs(os.path.dirname(local), exist_ok=True)
            with open(local, "w", encoding="utf-8") as f:
                f.write(content)
            log.info("Created file %s", local)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_savefile(self):
        try:
            data = self._read_json_body()
        except Exception:
            self._send_json({"success": False, "error": "Invalid body"}, 400)
            return
        rel_path = data.get("path", "").strip()
        content = data.get("content", "")
        if not rel_path:
            self._send_json({"success": False, "error": "Path required"}, 400)
            return
        local = self._safe_local(rel_path)
        if not local:
            self._send_json({"success": False, "error": "Invalid path"}, 403)
            return
        if self._is_cm_protected(local):
            self._send_json(
                {"success": False, "error": "Cannot write to chart repository"}, 403
            )
            return
        if not os.path.isfile(local):
            self._send_json({"success": False, "error": "File not found"}, 404)
            return
        try:
            with open(local, "w", encoding="utf-8") as f:
                f.write(content)
            log.info("Saved file %s (%d bytes)", local, len(content))
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_readfile(self, file_path):
        if not file_path:
            self._send_json({"error": "Path required"}, 400)
            return
        local = self._safe_local(file_path)
        if not local or not os.path.isfile(local):
            self._send_json({"error": "File not found"}, 404)
            return
        try:
            with open(local, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self._send_json({"content": content, "path": file_path})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _serve_editor_page(self, file_path):
        if not file_path:
            self.send_error(400, "No file specified")
            return

        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        esc_path = html_module.escape(file_path, quote=True)
        esc_name = html_module.escape(filename)

        parent = os.path.dirname(file_path.rstrip("/"))
        if not parent or parent == "/":
            back_url = "/"
        else:
            back_url = parent + "/"

        lang_label = {
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".xml": "XML",
            ".toml": "TOML",
            ".py": "Python",
            ".js": "JavaScript",
            ".sh": "Bash",
            ".css": "CSS",
            ".html": "HTML",
            ".md": "Markdown",
        }.get(ext, "Text")

        page_content = (
            '<div class="editor-topbar">'
            f'  <a href="{html_module.escape(back_url)}"'
            f'   class="cm-back-btn" title="Back">{SVG_BACK}</a>'
            f"  <div>"
            f'    <h2 class="cm-title">{esc_name}</h2>'
            f'    <p class="cm-subtitle">{lang_label} &middot; {esc_path}</p>'
            f"  </div>"
            f'  <div class="editor-actions">'
            f'    <span id="editor-status" class="chart-status"></span>'
            f'    <button class="hdr-btn accent" onclick="saveFile()">'
            f"      Save</button>"
            f"  </div>"
            f"</div>"
            f'<div class="editor-wrap">'
            f'  <textarea id="editor-content" class="editor-textarea"'
            f'   spellcheck="false" data-path="{esc_path}"'
            f'   data-ext="{html_module.escape(ext)}"></textarea>'
            f"</div>"
        )

        editor_script = (
            "<script>"
            "(function(){"
            "  var ta=document.getElementById('editor-content');"
            "  var ext=ta.dataset.ext;"
            "  var path=ta.dataset.path;"
            "  fetch('/__api__/readfile?path='+encodeURIComponent(path))"
            "    .then(function(r){return r.json()})"
            "    .then(function(d){"
            "      if(d.content!==undefined)ta.value=d.content;"
            "      else ta.value='Error: '+d.error;"
            "    });"
            "  ta.addEventListener('keydown',function(e){"
            "    if(e.key==='Tab'){"
            "      e.preventDefault();"
            "      var s=ta.selectionStart,end=ta.selectionEnd;"
            "      ta.value=ta.value.substring(0,s)+'  '+ta.value.substring(end);"
            "      ta.selectionStart=ta.selectionEnd=s+2;"
            "    }"
            "    if((e.ctrlKey||e.metaKey)&&e.key==='s'){"
            "      e.preventDefault();window.saveFile();"
            "    }"
            "  });"
            "  window.saveFile=function(){"
            "    var stat=document.getElementById('editor-status');"
            "    var content=ta.value;"
            "    var err=validate(content,ext);"
            "    if(err){stat.textContent=err;stat.className='chart-status error';return}"
            "    stat.textContent='Saving...';stat.className='chart-status';"
            "    fetch('/__api__/savefile',{"
            "      method:'POST',"
            "      headers:{'Content-Type':'application/json'},"
            "      body:JSON.stringify({path:path,content:content})"
            "    }).then(function(r){return r.json()}).then(function(d){"
            "      if(d.success){"
            "        stat.textContent='Saved';stat.className='chart-status success';"
            "        window._toast&&window._toast('Saved','success');"
            "      }else{"
            "        stat.textContent=d.error;stat.className='chart-status error';"
            "      }"
            "    });"
            "  };"
            "  function validate(c,e){"
            "    if(e==='.json'){"
            "      try{JSON.parse(c)}catch(x){return 'Invalid JSON: '+x.message}"
            "    }"
            "    return null;"
            "  }"
            "})();"
            "</script>"
        )

        html = _render_page(
            f"Edit — {filename}",
            page_content,
            header_html=_render_header(show_upload=False),
            extra_scripts=editor_script,
        )

        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    # ── File Serving Overrides ───────────────────────────────────

    def guess_type(self, path):
        _, ext = os.path.splitext(path.lower())
        type_map = {
            ".log": "text/plain",
            ".out": "text/plain",
            ".err": "text/plain",
            ".txt": "text/plain",
            ".cfg": "text/plain",
            ".conf": "text/plain",
            ".ini": "text/plain",
            ".json": "application/json",
            ".yaml": "application/yaml",
            ".yml": "application/yaml",
            ".csv": "text/csv",
            ".tsv": "text/csv",
            ".xml": "application/xml",
            ".md": "text/markdown",
        }
        return type_map.get(ext, super().guess_type(path))

    def send_head(self):
        path = self.translate_path(self.path)

        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith("/"):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + "/", parts[3], parts[4])
                self.send_header("Location", urllib.parse.urlunsplit(new_parts))
                self.end_headers()
                return None
            return self.list_directory(path)

        ctype = self.guess_type(path)
        _, ext = os.path.splitext(path.lower())
        force_inline = ext in INLINE_EXTENSIONS or (ctype and ctype.startswith("text/"))

        if force_inline and "charset=" not in ctype.lower():
            if ctype.startswith("text/") or ctype in {
                "application/json",
                "application/xml",
                "application/yaml",
            }:
                ctype = f"{ctype}; charset=utf-8"

        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            if not force_inline and ctype == "application/octet-stream":
                try:
                    sample = f.read(2048)
                    f.seek(0)
                except Exception:
                    sample = b""
                if self._looks_like_text(sample):
                    ctype = "text/plain; charset=utf-8"
                    force_inline = True

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            if force_inline:
                self.send_header("Content-Disposition", "inline")
            self.send_header("Content-Length", str(fs.st_size))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except Exception:
            f.close()
            raise

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _looks_like_text(sample):
        if not sample:
            return True
        if b"\x00" in sample:
            return False
        printable = sum(1 for b in sample if b in (9, 10, 13) or 32 <= b <= 126)
        return (printable / len(sample)) >= 0.90

    @staticmethod
    def _format_size(size):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def log_message(self, format, *args):
        log.info(format, *args, extra={"client": self.client_address[0]})

    def log_error(self, format, *args):
        log.warning(format, *args, extra={"client": self.client_address[0]})


# ── Entry Point ────────────────────────────────────────────────────────


def run_server(directory, port):
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        log.error("Directory '%s' does not exist or is not a directory", directory)
        sys.exit(1)

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    handler = partial(FileServerHandler, directory=directory)

    try:
        with ReusableTCPServer(("", port), handler) as httpd:
            log.info("=" * 60)
            log.info("  Caffrey's File Server")
            log.info("=" * 60)
            log.info("  Directory : %s", directory)
            log.info("  Password  : %s (env: CFS_PASSWORD)", "*" * len(DELETE_PASSWORD))
            log.info("  Local     : http://localhost:%d", port)
            log.info("  Network   : http://%s:%d", LOCAL_IP, port)
            log.info("  Hostname  : http://%s:%d", HOSTNAME, port)
            log.info("=" * 60)
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 98:
            log.error("Port %d is already in use", port)
        else:
            log.error("Server error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Server stopped")


def main():
    import argparse

    from log_setup import configure_logging

    configure_logging()

    parser = argparse.ArgumentParser(
        description="Caffrey's File Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Environment variables: CFS_PORT, CFS_DIRECTORY, CFS_PASSWORD, "
        "CFS_LOG_DIR, CFS_LOG_LEVEL, CFS_ARTIFACTORY_URL, CFS_ARTIFACTORY_KEY",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        default=DIRECTORY,
        help=f"Directory to serve (default: {DIRECTORY})",
    )
    parser.add_argument(
        "-p", "--port", type=int, default=PORT, help=f"Port (default: {PORT})"
    )
    args = parser.parse_args()

    run_server(args.directory, args.port)


if __name__ == "__main__":
    main()
