/* ===================================================================
   Caffrey's File Server — Client-side JavaScript
   =================================================================== */

(function () {
  "use strict";

  /* ── Theme ───────────────────────────────────────────────────── */

  var THEME_KEY = "cfs-theme";

  function initTheme() {
    if (localStorage.getItem(THEME_KEY) === "light") {
      document.documentElement.classList.add("light");
    }
    updateThemeIcon();
  }

  function updateThemeIcon() {
    var icon = document.getElementById("theme-icon");
    if (!icon) return;
    var isLight = document.documentElement.classList.contains("light");
    icon.innerHTML = isLight
      ? '<path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z"/>'
      : '<path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"/>';
  }

  window.toggleTheme = function () {
    document.documentElement.classList.toggle("light");
    var isLight = document.documentElement.classList.contains("light");
    localStorage.setItem(THEME_KEY, isLight ? "light" : "dark");
    updateThemeIcon();
  };

  initTheme();

  /* ── Toast ───────────────────────────────────────────────────── */

  function toast(msg, type) {
    type = type || "info";
    var container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    var el = document.createElement("div");
    el.className = "toast " + type;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(function () {
      el.style.opacity = "0";
      el.style.transform = "translateX(20px)";
      setTimeout(function () {
        el.remove();
      }, 300);
    }, 3500);
  }
  window._toast = toast;

  /* ── Upload ──────────────────────────────────────────────────── */

  window.toggleUpload = function () {
    var section = document.getElementById("upload-section");
    if (section) {
      section.classList.toggle("open");
      if (section.classList.contains("open")) {
        setTimeout(function () {
          section.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 50);
      }
    }
  };

  function setupUpload() {
    var zone = document.getElementById("upload-zone");
    var input = document.getElementById("upload-input");
    if (!zone || !input) return;

    zone.addEventListener("dragover", function (e) {
      e.preventDefault();
      zone.classList.add("dragover");
    });
    zone.addEventListener("dragleave", function () {
      zone.classList.remove("dragover");
    });
    zone.addEventListener("drop", function (e) {
      e.preventDefault();
      zone.classList.remove("dragover");
      if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
    });
    input.addEventListener("change", function () {
      if (input.files.length) uploadFiles(input.files);
    });
  }

  function uploadFiles(files) {
    var fd = new FormData();
    var dirEl = document.getElementById("upload-dir");
    fd.append("upload_path", dirEl ? dirEl.value : "/");
    for (var i = 0; i < files.length; i++) fd.append("files", files[i]);

    var bar = document.getElementById("progress-fill");
    var wrap = document.getElementById("upload-progress");
    if (wrap) wrap.classList.add("active");
    if (bar) bar.style.width = "30%";

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/__api__/upload", true);
    xhr.upload.onprogress = function (e) {
      if (e.lengthComputable && bar)
        bar.style.width = Math.round((e.loaded / e.total) * 100) + "%";
    };
    xhr.onload = function () {
      if (xhr.status === 200) {
        toast("Files uploaded successfully", "success");
        setTimeout(function () {
          location.reload();
        }, 600);
      } else {
        var r;
        try {
          r = JSON.parse(xhr.responseText);
        } catch (_) {}
        toast((r && r.error) || "Upload failed", "error");
      }
      if (wrap) wrap.classList.remove("active");
    };
    xhr.onerror = function () {
      toast("Upload failed — network error", "error");
      if (wrap) wrap.classList.remove("active");
    };
    xhr.send(fd);
  }

  setTimeout(setupUpload, 0);

  /* ── Delete ──────────────────────────────────────────────────── */

  var _deletePath = "";

  window.showDeleteModal = function (path, name) {
    _deletePath = path;
    var overlay = document.getElementById("delete-modal");
    var label = document.getElementById("delete-filename");
    var pwd = document.getElementById("delete-password");
    if (label) label.textContent = name;
    if (pwd) pwd.value = "";
    if (overlay) overlay.classList.add("open");
    setTimeout(function () {
      if (pwd) pwd.focus();
    }, 100);
  };

  window.closeDeleteModal = function () {
    var m = document.getElementById("delete-modal");
    if (m) m.classList.remove("open");
  };

  window.confirmDelete = function () {
    var pwd = document.getElementById("delete-password");
    if (!pwd || !pwd.value) {
      toast("Please enter the password", "error");
      return;
    }
    fetch("/__api__/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: _deletePath, password: pwd.value }),
    })
      .then(function (r) {
        return r.json().then(function (d) {
          return { ok: r.ok, data: d };
        });
      })
      .then(function (res) {
        if (res.ok && res.data.success) {
          toast("Deleted successfully", "success");
          window.closeDeleteModal();
          setTimeout(function () {
            location.reload();
          }, 500);
        } else {
          toast(res.data.error || "Delete failed", "error");
        }
      })
      .catch(function () {
        toast("Delete failed — network error", "error");
      });
  };

  /* ── Chart Download ──────────────────────────────────────────── */

  window.downloadChart = function () {
    var nameEl = document.getElementById("chart-name");
    var verEl = document.getElementById("chart-version");
    var stat = document.getElementById("chart-status");
    if (!nameEl.value || !verEl.value) {
      if (stat) {
        stat.textContent = "Please fill in both fields.";
        stat.className = "chart-status error";
      }
      return;
    }
    if (stat) {
      stat.textContent = "Downloading and extracting...";
      stat.className = "chart-status";
    }
    fetch("/__api__/chart-download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: nameEl.value.trim(),
        version: verEl.value.trim(),
      }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.success) {
          if (stat) {
            stat.innerHTML =
              'Chart downloaded! <a href="' +
              d.path +
              '" style="color:var(--accent);text-decoration:underline;font-weight:600">' +
              "Open " + d.path +
              "</a>";
            stat.className = "chart-status success";
          }
          toast("Chart downloaded!", "success");
        } else {
          if (stat) {
            stat.textContent = "Error: " + d.error;
            stat.className = "chart-status error";
          }
          toast("Download failed", "error");
        }
      })
      .catch(function () {
        if (stat) {
          stat.textContent = "Network error";
          stat.className = "chart-status error";
        }
      });
  };

  /* ── JSON Viewer Enhancement ─────────────────────────────────── */

  window.enhanceJsonViewer = function () {
    try {
      var codeEls = document.querySelectorAll(".viewer-code");
      var raw = "";
      codeEls.forEach(function (el) {
        raw += el.textContent + "\n";
      });
      var parsed = JSON.parse(raw);
      var pretty = JSON.stringify(parsed, null, 2);
      var container = document.querySelector(".viewer-content");
      container.innerHTML = "";
      pretty.split("\n").forEach(function (line, idx) {
        var d = document.createElement("div");
        d.className = "viewer-line";
        var ln = document.createElement("span");
        ln.className = "viewer-ln";
        ln.textContent = idx + 1;
        var code = document.createElement("span");
        code.className = "viewer-code";
        line = line.replace(
          /"([^"]+)"\s*:/g,
          '<span style="color:#7dd3fc">"$1"</span>:',
        );
        line = line.replace(
          /: "([^"]*)"/g,
          ': <span style="color:#86efac">"$1"</span>',
        );
        line = line.replace(
          /: (\d+\.?\d*)/g,
          ': <span style="color:#fbbf24">$1</span>',
        );
        line = line.replace(
          /: (true|false|null)/g,
          ': <span style="color:#f472b6">$1</span>',
        );
        code.innerHTML = line;
        d.appendChild(ln);
        d.appendChild(code);
        container.appendChild(d);
      });
    } catch (_) {}
  };

  /* ── Keyboard shortcuts ──────────────────────────────────────── */

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      window.closeDeleteModal && window.closeDeleteModal();
    }
    var modal = document.getElementById("delete-modal");
    if (e.key === "Enter" && modal && modal.classList.contains("open")) {
      window.confirmDelete && window.confirmDelete();
    }
  });
})();
