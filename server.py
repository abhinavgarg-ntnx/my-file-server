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
import re
import gzip
import io
import zipfile
import shutil
import logging
import subprocess
import threading
import time
import uuid
import tempfile
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
    EXT_LANG_MAP,
    SYSTEM_DIRS,
)
from icons import get_icon, ICONS
from svgs import (
    SVG_HOME,
    SVG_VIEW,
    SVG_DOWNLOAD,
    SVG_DELETE,
    SVG_BACK,
    SVG_EDIT,
    SVG_RENAME,
    SVG_UPLOAD_CLOUD,
    SVG_UPLOAD_CLOUD_SM,
    SVG_COPY,
    SVG_UPLOAD_BTN,
    SVG_CM_UPLOAD,
)
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
    html = re.sub(r"\{\{[A-Z_]+\}\}", "", html)
    return html


_cm_version_cache = None


def _get_cm_version():
    global _cm_version_cache
    if _cm_version_cache is not None:
        return _cm_version_cache
    try:
        result = subprocess.run(
            ["chartmuseum", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        raw = result.stdout.strip() or result.stderr.strip()
        m = re.search(r"(\d+\.\d+\.\d+)", raw)
        _cm_version_cache = f"v{m.group(1)}" if m else raw or ""
    except Exception:
        _cm_version_cache = ""
    return _cm_version_cache


def _gzip_bytes(data):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6) as f:
        f.write(data)
    return buf.getvalue()


_static_gz_cache = {}


# ── ZIP job infrastructure ─────────────────────────────────────────────

_zip_jobs = {}
_zip_lock = threading.Lock()
_MAX_ZIP_BYTES = 4 * 1024 * 1024 * 1024  # 4 GB


def _fmt_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def _safe_unlink(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _cleanup_old_jobs():
    now = time.time()
    with _zip_lock:
        for jid in list(_zip_jobs):
            job = _zip_jobs[jid]
            age = now - job.get("finished_at", now)
            if job["status"] in ("done", "error", "cancelled") and age > 600:
                if job.get("zip_path"):
                    _safe_unlink(job["zip_path"])
                del _zip_jobs[jid]


def _zip_worker(job_id, local_path, cancel_event):
    job = _zip_jobs[job_id]

    file_list = []
    total_bytes = 0
    for root, _dirs, files in os.walk(local_path):
        if cancel_event.is_set():
            job.update(status="cancelled", finished_at=time.time())
            return
        for fname in files:
            full = os.path.join(root, fname)
            try:
                sz = os.path.getsize(full)
                file_list.append((full, sz))
                total_bytes += sz
            except OSError:
                pass

    if total_bytes > _MAX_ZIP_BYTES:
        job.update(
            status="error",
            error=(
                f"Directory too large ({_fmt_size(total_bytes)}). "
                f"Limit is {_fmt_size(_MAX_ZIP_BYTES)}."
            ),
            finished_at=time.time(),
        )
        return

    job.update(
        status="zipping",
        total_files=len(file_list),
        total_bytes=total_bytes,
    )

    dirname = job["dirname"]
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip", prefix="caffrey-")
    os.close(tmp_fd)
    job["zip_path"] = tmp_path

    try:
        processed_bytes = 0
        with zipfile.ZipFile(
            tmp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=1
        ) as zf:
            for i, (full, sz) in enumerate(file_list):
                if cancel_event.is_set():
                    job.update(status="cancelled", finished_at=time.time())
                    _safe_unlink(tmp_path)
                    return
                arcname = os.path.join(dirname, os.path.relpath(full, local_path))
                try:
                    zf.write(full, arcname)
                    processed_bytes += sz
                    job["processed_files"] = i + 1
                    job["bytes_processed"] = processed_bytes
                except (OSError, PermissionError):
                    pass

        job.update(
            status="done",
            zip_size=os.path.getsize(tmp_path),
            finished_at=time.time(),
        )
        log.info(
            "ZIP ready: %s (%s)",
            dirname,
            _fmt_size(job["zip_size"]),
        )
    except Exception as exc:
        job.update(status="error", error=str(exc), finished_at=time.time())
        _safe_unlink(tmp_path)


_CHARTS_BTN_HTML = (
    '<a href="/__charts__" class="hdr-btn" title="ChartMuseum">'
    f"{SVG_DOWNLOAD} ChartMuseum</a>"
)


def _render_header(show_upload=True, show_charts=True):
    """Render the header partial."""
    upload_btn = ""
    if show_upload:
        upload_btn = (
            '<button class="hdr-btn" onclick="toggleUpload()">'
            f"{SVG_UPLOAD_BTN} Upload</button>"
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


# ── HTTP Handler ───────────────────────────────────────────────────────

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
        if path == "/__api__/zip-progress":
            qs = urllib.parse.parse_qs(parsed.query)
            return self._handle_zip_progress(qs.get("id", [""])[0])
        if path == "/__api__/zip-download":
            qs = urllib.parse.parse_qs(parsed.query)
            return self._handle_zip_download(qs.get("id", [""])[0])
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
        if path == "/__api__/rename":
            return self._handle_rename()
        if path == "/__api__/zip-start":
            return self._handle_zip_start()
        if path == "/__api__/zip-cancel":
            return self._handle_zip_cancel()
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

    def _send_html(self, html_str):
        """Send an HTML response with gzip when the client supports it."""
        encoded = html_str.encode("utf-8", "surrogateescape")
        use_gz = (
            "gzip" in self.headers.get("Accept-Encoding", "") and len(encoded) > 512
        )
        if use_gz:
            encoded = _gzip_bytes(encoded)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        if use_gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Vary", "Accept-Encoding")
        self.end_headers()
        self.wfile.write(encoded)

    def _serve_static(self, rel_path):
        """Serve files from the application's static/ directory."""
        safe = os.path.normpath(rel_path).lstrip("/").lstrip("\\")
        local = STATIC_DIR / safe

        if not local.is_file() or ".." in rel_path:
            self.send_error(404, "Static file not found")
            return

        ext = os.path.splitext(safe)[1].lower()
        ctype = _STATIC_MIME.get(ext, "application/octet-stream")

        stat = local.stat()
        etag = f'"{stat.st_mtime_ns:x}-{stat.st_size:x}"'

        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.end_headers()
            return

        cache_key = (str(local), stat.st_mtime_ns)
        accepts_gz = "gzip" in self.headers.get("Accept-Encoding", "")
        use_gz = accepts_gz and ext in (".css", ".js", ".svg")

        if use_gz and cache_key in _static_gz_cache:
            data = _static_gz_cache[cache_key]
        else:
            raw = local.read_bytes()
            if use_gz:
                data = _gzip_bytes(raw)
                _static_gz_cache[cache_key] = data
            else:
                data = raw

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
        if use_gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Vary", "Accept-Encoding")
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
        show_upload = not is_cm_dir
        esc = html_module.escape

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
                    f'<span class="bc-sep">/</span>'
                    f'<a class="bc-chip" href="{qp}">{esc(part)}</a>'
                )

        # Upload section
        upload_html = ""
        if show_upload:
            upload_html = (
                '<div id="upload-section" class="upload-section">'
                f'<div id="upload-zone" class="upload-zone">'
                f'<div class="upload-icon">{SVG_UPLOAD_CLOUD}</div>'
                "<p>Drag files here or click to browse</p>"
                '<input type="file" id="upload-input" multiple>'
                f'<input type="hidden" id="upload-dir" value="{esc(displaypath)}">'
                "</div>"
                '<div id="upload-progress" class="upload-progress">'
                '<div class="progress-bar">'
                '<div id="progress-fill" class="progress-fill"></div></div>'
                "</div></div>"
            )

        # Sort bar (with create buttons + ZIP on the right)
        esc_dp = esc(displaypath, quote=True)
        zip_path_enc = esc(displaypath, quote=True).replace("'", "\\'")
        zip_name = os.path.basename(displaypath.rstrip("/")) or "root"
        zip_name_enc = esc(zip_name, quote=True).replace("'", "\\'")
        zip_btn = (
            f'<button class="hdr-btn sm"'
            f" onclick=\"downloadZip('{zip_path_enc}','{zip_name_enc}')\""
            f' title="Download folder as ZIP">'
            f"{SVG_DOWNLOAD} ZIP</button>"
        )
        sort_right = '<div class="sort-spacer"></div>'
        if show_upload:
            sort_right += (
                f'<button class="hdr-btn sm" '
                f"onclick=\"showNewFolderModal('{esc_dp}')\">"
                "+ Folder</button>"
                f'<button class="hdr-btn sm" '
                f"onclick=\"showNewFileModal('{esc_dp}')\">"
                "+ File</button>"
            )
        elif is_cm_dir:
            sort_right += (
                '<span class="cm-note-warn" style="padding:0">'
                "Read-only &mdash; managed by ChartMuseum</span>"
            )
        sort_right += zip_btn

        sort_bar = (
            '<div class="sort-bar">'
            '<span class="sort-label">Sort:</span>'
            '<button class="sort-btn active" data-sort="name"'
            " onclick=\"sortFiles('name',this)\">Name</button>"
            '<button class="sort-btn" data-sort="size"'
            " onclick=\"sortFiles('size',this)\">Size</button>"
            '<button class="sort-btn" data-sort="date"'
            " onclick=\"sortFiles('date',this)\">Date</button>"
            f"{sort_right}"
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
                f'<tr class="file-item">'
                f'<td class="ft-name">'
                f'<a class="file-link" href="{parent_url}">'
                f'{ICONS["parent"]}'
                f'<span class="file-name">.. (Parent Directory)</span>'
                f"</a></td>"
                f'<td class="ft-size"></td>'
                f'<td class="ft-date"></td>'
                f'<td class="ft-actions"></td>'
                f"</tr>"
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
                raw_size = 0 if is_dir else os.path.getsize(fullname)
                raw_mtime = os.path.getmtime(fullname)
                size_str = "-" if is_dir else self._format_size(raw_size)
                mtime_str = datetime.fromtimestamp(raw_mtime).strftime("%Y-%m-%d %H:%M")
            except Exception:
                raw_size, raw_mtime = 0, 0
                size_str, mtime_str = "-", "-"

            is_system = is_dir and displaypath == "/" and name in SYSTEM_DIRS
            system_tag = ' <span class="sys-tag">System</span>' if is_system else ""

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
            if is_dir:
                zip_path_esc = esc(link.rstrip("/") + "/", quote=True).replace(
                    "'", "\\'"
                )
                zip_name_esc = esc(name, quote=True).replace("'", "\\'")
                actions += (
                    f'<button class="act-btn dl-btn" title="Download as ZIP"'
                    f' onclick="event.preventDefault();event.stopPropagation();'
                    f"downloadZip('{zip_path_esc}','{zip_name_esc}')\">"
                    f"{SVG_DOWNLOAD}</button>"
                )
            else:
                actions += (
                    f'<a class="act-btn dl-btn" title="Download"'
                    f' href="{link}" download>{SVG_DOWNLOAD}</a>'
                )
            if not is_cm_dir and not is_system:
                ren_path = esc(link.rstrip("/"), quote=True).replace("'", "\\'")
                ren_name = esc(name, quote=True).replace("'", "\\'")
                actions += (
                    f'<button class="act-btn ren-btn" title="Rename"'
                    f' onclick="event.preventDefault();event.stopPropagation();'
                    f"showRenameModal('{ren_path}','{ren_name}')\">"
                    f"{SVG_RENAME}</button>"
                )
                el = esc(link, quote=True).replace("'", "\\'")
                ed = esc(display, quote=True).replace("'", "\\'")
                actions += (
                    f'<button class="act-btn del-btn" title="Delete"'
                    f' onclick="event.preventDefault();event.stopPropagation();'
                    f"showDeleteModal('{el}','{ed}')\">{SVG_DELETE}</button>"
                )

            items.append(
                f'<tr class="file-item"'
                f' data-name="{esc(name.lower())}"'
                f' data-size="{raw_size}"'
                f' data-mtime="{int(raw_mtime)}"'
                f' data-isdir="{"1" if is_dir else "0"}">'
                f'<td class="ft-name">'
                f'<a class="file-link" href="{file_link}">{icon}'
                f'<span class="file-name">{esc(display)}{system_tag}</span></a></td>'
                f'<td class="ft-size">{size_str}</td>'
                f'<td class="ft-date">{mtime_str}</td>'
                f'<td class="ft-actions">'
                f'<div class="file-actions">{actions}</div></td>'
                f"</tr>"
            )

        if not entries:
            items.append(
                '<tr><td colspan="4" class="empty-state">'
                "This directory is empty</td></tr>"
            )

        content = (
            f'<div class="breadcrumb">{bc}</div>'
            f"{upload_html}"
            f"{sort_bar}"
            f'<div class="file-list-wrap">'
            f'<table class="file-table">'
            f'<tbody class="file-list">{"".join(items)}</tbody>'
            f"</table></div>"
        )

        modals = ""
        if not is_cm_dir:
            modals = _load_template("delete_modal.html") + _load_template(
                "input_modal.html"
            )

        html = _render_page(
            f"Caffrey's Treasure — {displaypath}",
            content,
            header_html=_render_header(show_upload=show_upload),
            modals=modals,
        )
        self._send_html(html)
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

        esc = html_module.escape
        prism_lang = EXT_LANG_MAP.get(ext, "none")
        escaped_content = esc(content)

        truncated_msg = ""
        if truncated:
            truncated_msg = (
                '<div style="padding:8px 16px;font-size:12px;'
                'color:var(--warning)">'
                f"[Truncated — first {self._format_size(max_size)} "
                f"of {size_str}]</div>"
            )

        parent_dir = os.path.dirname(file_path.rstrip("/"))
        parent_url = parent_dir + "/" if parent_dir and parent_dir != "/" else "/"

        prism_head = (
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/'
            "prismjs@1.29.0/plugins/line-numbers/"
            'prism-line-numbers.min.css">'
        )

        json_pretty = ""
        if ext == ".json":
            json_pretty = (
                "<script>"
                'var _c=document.querySelector(".viewer-wrap code");'
                "if(_c)try{_c.textContent="
                "JSON.stringify(JSON.parse(_c.textContent),null,2)}"
                "catch(e){}"
                "</script>"
            )

        prism_scripts = (
            "<script>window.Prism=window.Prism||{};"
            "Prism.manual=true;</script>"
            '<script defer src="https://cdn.jsdelivr.net/npm/'
            'prismjs@1.29.0/prism.min.js"></script>'
            '<script defer src="https://cdn.jsdelivr.net/npm/'
            "prismjs@1.29.0/plugins/line-numbers/"
            'prism-line-numbers.min.js"></script>'
            '<script defer src="https://cdn.jsdelivr.net/npm/'
            "prismjs@1.29.0/plugins/autoloader/"
            'prism-autoloader.min.js"></script>'
            + json_pretty
            + "<script>document.addEventListener('DOMContentLoaded',"
            "function(){Prism.highlightAll()});</script>"
        )

        page_content = render_template(
            "viewer_page.html",
            PARENT_URL=parent_url,
            SVG_BACK=SVG_BACK,
            SVG_DOWNLOAD=SVG_DOWNLOAD,
            FILENAME=esc(filename),
            SIZE=size_str,
            MTIME=mtime_str,
            FILE_PATH=file_path,
            LANG=prism_lang,
            CODE_CONTENT=escaped_content,
            TRUNCATED_MSG=truncated_msg,
        )

        html = _render_page(
            f"View — {filename}",
            page_content,
            header_html=_render_header(show_upload=False),
            extra_head=prism_head,
            extra_scripts=prism_scripts,
        )
        self._send_html(html)

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

        cm_version = _get_cm_version()
        cm_ver_html = html_module.escape(cm_version) if cm_version else ""

        page_content = render_template(
            "charts_page.html",
            SVG_BACK=SVG_BACK,
            SVG_COPY=SVG_COPY,
            SVG_DOWNLOAD=SVG_DOWNLOAD,
            SVG_UPLOAD_CLOUD_SM=SVG_UPLOAD_CLOUD_SM,
            SVG_CM_UPLOAD=SVG_CM_UPLOAD,
            REPO_URL=repo_url,
            CM_VERSION=cm_ver_html,
        )

        import_modal = render_template(
            "import_modal.html",
            REQUESTS_NOTE=requests_note,
            SVG_DOWNLOAD=SVG_DOWNLOAD,
        )

        html = _render_page(
            "ChartMuseum — Caffrey's Treasure",
            page_content,
            header_html=_render_header(show_upload=False, show_charts=False),
            modals=import_modal,
            extra_scripts='<script src="/__static__/js/charts.js"></script>',
        )
        self._send_html(html)

    # ── Editor Page ──────────────────────────────────────────────

    def _serve_editor_page(self, file_path):
        if not file_path:
            self.send_error(400, "No file specified")
            return

        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        esc = html_module.escape

        parent = os.path.dirname(file_path.rstrip("/"))
        back_url = parent + "/" if parent and parent != "/" else "/"

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

        page_content = render_template(
            "editor_page.html",
            SVG_BACK=SVG_BACK,
            BACK_URL=esc(back_url),
            FILENAME=esc(filename),
            LANG_LABEL=lang_label,
            FILE_PATH=esc(file_path, quote=True),
            FILE_EXT=esc(ext),
        )

        html = _render_page(
            f"Edit — {filename}",
            page_content,
            header_html=_render_header(show_upload=False),
            extra_scripts='<script src="/__static__/js/editor.js"></script>',
        )
        self._send_html(html)

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
            self._send_json({"success": False, "error": "Upload not supported"}, 500)
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
                    {"success": False, "error": "Cannot write to chart repository"},
                    403,
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
                {"success": False, "error": "Cannot delete chart repo files"},
                403,
            )
            return
        real_served = os.path.realpath(self.server_dir)
        real_target = os.path.realpath(local_path)
        if not real_target.startswith(real_served):
            self._send_json(
                {"success": False, "error": "Path outside served directory"},
                403,
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
                {"success": False, "error": "Chart name and version required"},
                400,
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
                    "Content-Type": (f"multipart/form-data; boundary={boundary}"),
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
                "ChartMuseum push returned %s: %s",
                resp.status,
                resp_body[:200],
            )
            return False
        except Exception:
            log.exception("Failed to push %s-%s to ChartMuseum", name, version)
            return False

    # ── File Operations ──────────────────────────────────────────

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
                {"success": False, "error": "Cannot write to chart repository"},
                403,
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
                {"success": False, "error": "Cannot write to chart repository"},
                403,
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
                {"success": False, "error": "Cannot write to chart repository"},
                403,
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

    def _handle_rename(self):
        try:
            data = self._read_json_body()
        except Exception:
            self._send_json({"success": False, "error": "Invalid body"}, 400)
            return

        old_path = data.get("path", "").strip().rstrip("/")
        new_name = data.get("newName", "").strip()

        if not old_path or not new_name:
            self._send_json(
                {"success": False, "error": "Path and new name required"}, 400
            )
            return
        if "/" in new_name or "\\" in new_name:
            self._send_json(
                {"success": False, "error": "Name cannot contain slashes"}, 400
            )
            return

        local = self._safe_local(old_path)
        if not local:
            self._send_json({"success": False, "error": "Invalid path"}, 403)
            return
        if self._is_cm_protected(local):
            self._send_json(
                {"success": False, "error": "Cannot rename chart repo items"},
                403,
            )
            return
        if not os.path.exists(local):
            self._send_json({"success": False, "error": "Item not found"}, 404)
            return

        basename = os.path.basename(local)
        parent = os.path.dirname(local)
        if (
            os.path.realpath(parent) == os.path.realpath(self.server_dir)
            and basename in SYSTEM_DIRS
        ):
            self._send_json(
                {"success": False, "error": "Cannot rename system directories"},
                403,
            )
            return

        if basename == new_name:
            self._send_json({"success": True})
            return

        new_local = os.path.join(parent, new_name)
        if os.path.exists(new_local):
            self._send_json(
                {"success": False, "error": "An item with that name already exists"},
                409,
            )
            return

        try:
            os.rename(local, new_local)
            log.info("Renamed %s → %s", local, new_local)
            self._send_json({"success": True})
        except Exception as e:
            log.exception("Rename failed for %s", local)
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

    def _handle_zip_start(self):
        try:
            data = self._read_json_body()
        except Exception:
            self._send_json({"error": "Invalid body"}, 400)
            return

        dir_path = data.get("path", "").strip()
        if not dir_path:
            self._send_json({"error": "Path required"}, 400)
            return

        local = self._safe_local(dir_path)
        if not local or not os.path.isdir(local):
            self._send_json({"error": "Directory not found"}, 404)
            return

        _cleanup_old_jobs()

        job_id = uuid.uuid4().hex[:12]
        cancel_event = threading.Event()
        dirname = os.path.basename(local.rstrip("/")) or "download"

        job = {
            "status": "scanning",
            "processed_files": 0,
            "total_files": 0,
            "bytes_processed": 0,
            "total_bytes": 0,
            "zip_path": None,
            "zip_size": 0,
            "dirname": dirname,
            "cancel_event": cancel_event,
            "error": "",
            "started_at": time.time(),
            "finished_at": 0,
        }

        with _zip_lock:
            _zip_jobs[job_id] = job

        t = threading.Thread(
            target=_zip_worker, args=(job_id, local, cancel_event), daemon=True
        )
        t.start()
        self._send_json({"job_id": job_id, "dirname": dirname})

    def _handle_zip_progress(self, job_id):
        job = _zip_jobs.get(job_id)
        if not job:
            self._send_json({"error": "Job not found"}, 404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        try:
            while True:
                evt = {
                    "status": job["status"],
                    "processed_files": job["processed_files"],
                    "total_files": job["total_files"],
                    "bytes_processed": job["bytes_processed"],
                    "total_bytes": job["total_bytes"],
                }
                if job["status"] == "done":
                    evt["zip_size"] = job.get("zip_size", 0)
                elif job["status"] == "error":
                    evt["error"] = job.get("error", "")

                self.wfile.write(f"data: {json.dumps(evt)}\n\n".encode())
                self.wfile.flush()

                if job["status"] in ("done", "error", "cancelled"):
                    break
                time.sleep(0.25)
        except (BrokenPipeError, ConnectionResetError, OSError):
            job["cancel_event"].set()

    def _handle_zip_download(self, job_id):
        job = _zip_jobs.get(job_id)
        if not job or job["status"] != "done":
            self._send_json({"error": "ZIP not ready"}, 404)
            return

        zip_path = job.get("zip_path")
        if not zip_path or not os.path.exists(zip_path):
            self._send_json({"error": "ZIP file missing"}, 404)
            return

        zip_size = os.path.getsize(zip_path)
        safe_name = job.get("dirname", "download").replace('"', "_")

        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header(
            "Content-Disposition", f'attachment; filename="{safe_name}.zip"'
        )
        self.send_header("Content-Length", str(zip_size))
        self.end_headers()

        with open(zip_path, "rb") as f:
            shutil.copyfileobj(f, self.wfile)

        _safe_unlink(zip_path)
        with _zip_lock:
            _zip_jobs.pop(job_id, None)

    def _handle_zip_cancel(self):
        try:
            data = self._read_json_body()
        except Exception:
            self._send_json({"error": "Invalid body"}, 400)
            return

        job_id = data.get("id", "")
        job = _zip_jobs.get(job_id)
        if job:
            job["cancel_event"].set()
        self._send_json({"ok": True})

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

    def log_message(self, fmt, *args):
        log.info(fmt, *args, extra={"client": self.client_address[0]})

    def log_error(self, fmt, *args):
        log.warning(fmt, *args, extra={"client": self.client_address[0]})


# ── Entry Point ────────────────────────────────────────────────────────


def run_server(directory, port):
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        log.error("Directory '%s' does not exist or is not a directory", directory)
        sys.exit(1)

    class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    handler = partial(FileServerHandler, directory=directory)

    try:
        with ReusableTCPServer(("", port), handler) as httpd:
            log.info("=" * 60)
            log.info("  Caffrey's File Server")
            log.info("=" * 60)
            log.info("  Directory : %s", directory)
            log.info(
                "  Password  : %s (env: CFS_PASSWORD)",
                "*" * len(DELETE_PASSWORD),
            )
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
        epilog=(
            "Environment variables: CFS_PORT, CFS_DIRECTORY, CFS_PASSWORD, "
            "CFS_LOG_DIR, CFS_LOG_LEVEL, CFS_ARTIFACTORY_URL, "
            "CFS_ARTIFACTORY_KEY"
        ),
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        default=DIRECTORY,
        help=f"Directory to serve (default: {DIRECTORY})",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=PORT,
        help=f"Port (default: {PORT})",
    )
    args = parser.parse_args()

    run_server(args.directory, args.port)


if __name__ == "__main__":
    main()
