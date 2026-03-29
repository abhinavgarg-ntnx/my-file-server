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
    if (!section) return;
    var wasOpen = section.classList.contains("open");
    section.classList.toggle("open");
    if (!wasOpen) {
      setTimeout(function () {
        var rect = section.getBoundingClientRect();
        if (rect.top < 0 || rect.bottom > window.innerHeight) {
          section.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }, 60);
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

  /* ── Delete Modal ──────────────────────────────────────────────  */

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

  /* ── Input Modal (New Folder / New File) ───────────────────── */

  var _inputCallback = null;

  function openInputModal(
    title,
    desc,
    placeholder,
    btnLabel,
    cb,
    defaultValue,
  ) {
    var m = document.getElementById("input-modal");
    if (!m) return cb(null);
    document.getElementById("input-modal-title").textContent = title;
    document.getElementById("input-modal-desc").textContent = desc;
    var inp = document.getElementById("input-modal-value");
    inp.value = defaultValue || "";
    inp.placeholder = placeholder;
    var errEl = document.getElementById("input-modal-error");
    errEl.style.display = "none";
    var btn = document.getElementById("input-modal-ok");
    btn.textContent = btnLabel;
    _inputCallback = cb;
    btn.onclick = function () {
      var val = inp.value.trim();
      if (!val) {
        errEl.textContent = "Name is required";
        errEl.style.display = "block";
        return;
      }
      if (/[\/\\]/.test(val)) {
        errEl.textContent = "Name cannot contain slashes";
        errEl.style.display = "block";
        return;
      }
      window.closeInputModal();
      cb(val);
    };
    m.classList.add("open");
    setTimeout(function () {
      inp.focus();
    }, 100);
  }

  window.closeInputModal = function () {
    var m = document.getElementById("input-modal");
    if (m) m.classList.remove("open");
    _inputCallback = null;
  };

  window.showNewFolderModal = function (dir) {
    openInputModal(
      "New Folder",
      "Create a folder in " + dir,
      "folder-name",
      "Create",
      function (name) {
        if (!name) return;
        var path = (dir === "/" ? "/" : dir) + name;
        fetch("/__api__/mkdir", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: path }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            if (d.success) {
              toast("Folder created", "success");
              setTimeout(function () {
                location.reload();
              }, 400);
            } else {
              toast(d.error || "Failed", "error");
            }
          })
          .catch(function () {
            toast("Network error", "error");
          });
      },
    );
  };

  window.showNewFileModal = function (dir) {
    openInputModal(
      "New File",
      "Create a file in " + dir,
      "config.yaml",
      "Create",
      function (name) {
        if (!name) return;
        var path = (dir === "/" ? "/" : dir) + name;
        fetch("/__api__/newfile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: path, content: "" }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            if (d.success) {
              toast("File created", "success");
              location.href = "/__editor__?file=" + encodeURIComponent(path);
            } else {
              toast(d.error || "Failed", "error");
            }
          })
          .catch(function () {
            toast("Network error", "error");
          });
      },
    );
  };

  /* ── Rename Modal ────────────────────────────────────────────── */

  window.showRenameModal = function (path, currentName) {
    openInputModal(
      "Rename",
      "Enter new name for " + currentName,
      currentName,
      "Rename",
      function (newName) {
        if (!newName || newName === currentName) return;
        fetch("/__api__/rename", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: path, newName: newName }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            if (d.success) {
              toast("Renamed successfully", "success");
              setTimeout(function () {
                location.reload();
              }, 400);
            } else {
              toast(d.error || "Rename failed", "error");
            }
          })
          .catch(function () {
            toast("Network error", "error");
          });
      },
      currentName,
    );
  };

  /* ── Sort ───────────────────────────────────────────────────── */

  window.sortFiles = function (key, btn) {
    var list = document.querySelector(".file-list");
    if (!list) return;
    var items = Array.from(list.querySelectorAll(".file-item[data-name]"));
    if (!items.length) return;

    var asc = true;
    if (btn && btn.classList.contains("active") && btn.dataset.dir === "asc") {
      asc = false;
    }

    items.sort(function (a, b) {
      var aDir = a.dataset.isdir === "1";
      var bDir = b.dataset.isdir === "1";
      if (aDir !== bDir) return aDir ? -1 : 1;

      var cmp = 0;
      if (key === "name") cmp = a.dataset.name.localeCompare(b.dataset.name);
      else if (key === "size")
        cmp = (parseInt(a.dataset.size) || 0) - (parseInt(b.dataset.size) || 0);
      else if (key === "date")
        cmp =
          (parseInt(a.dataset.mtime) || 0) - (parseInt(b.dataset.mtime) || 0);
      return asc ? cmp : -cmp;
    });

    items.forEach(function (item) {
      list.appendChild(item);
    });

    document.querySelectorAll(".sort-btn").forEach(function (b) {
      b.classList.remove("active");
      b.dataset.dir = "";
    });
    if (btn) {
      btn.classList.add("active");
      btn.dataset.dir = asc ? "asc" : "desc";
      btn.textContent =
        btn.dataset.sort.charAt(0).toUpperCase() +
        btn.dataset.sort.slice(1) +
        (asc ? " ↑" : " ↓");
    }
  };

  /* ── Chart Download ──────────────────────────────────────────── */

  window.downloadChart = function (push) {
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
      stat.textContent = push ? "Importing..." : "Downloading...";
      stat.className = "chart-status";
    }
    fetch("/__api__/chart-download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: nameEl.value.trim(),
        version: verEl.value.trim(),
        push: push !== false,
      }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.success) {
          var msg =
            'Downloaded to <a href="' +
            d.path +
            '" style="color:inherit;text-decoration:underline">' +
            d.path +
            "</a>";
          if (d.chartmuseum) {
            msg += " &bull; Pushed to ChartMuseum";
            toast("Imported & pushed to ChartMuseum!", "success");
            if (typeof window._cmRefresh === "function") window._cmRefresh();
          } else {
            toast("Chart downloaded!", "success");
          }
          if (stat) {
            stat.innerHTML = msg;
            stat.className = "chart-status success";
          }
          setTimeout(function () {
            window.cmCloseImport && window.cmCloseImport();
            nameEl.value = "";
            verEl.value = "";
          }, 2000);
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

  /* ── ZIP download tray (multi-card, persistent history) ────── */

  function fmtSize(b) {
    if (b < 1024) return b + " B";
    if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
    if (b < 1073741824) return (b / 1048576).toFixed(1) + " MB";
    return (b / 1073741824).toFixed(1) + " GB";
  }

  var zipTray = {
    container: null,
    cards: {},

    _ensureContainer: function () {
      if (!this.container) {
        var c = document.createElement("div");
        c.id = "zip-tray";
        c.className = "zip-tray";
        document.body.appendChild(c);
        this.container = c;
      }
    },

    _cardHTML: function (jobId, name) {
      return (
        '<div class="zip-hdr" onclick="zipTrayToggle(\'' +
        jobId +
        "')\">" +
        '<span class="zip-title">' +
        '<span class="zip-spinner"></span>Preparing…</span>' +
        '<span class="zip-hdr-btns">' +
        '<button class="zip-hdr-btn zip-toggle-btn" ' +
        "onclick=\"event.stopPropagation();zipTrayToggle('" +
        jobId +
        '\')" title="Toggle">' +
        '<span class="zip-arrow">&#9660;</span></button>' +
        '<button class="zip-hdr-btn zip-close-btn" ' +
        "onclick=\"event.stopPropagation();zipTrayClose('" +
        jobId +
        '\')" title="Close">&times;</button>' +
        "</span></div>" +
        '<div class="zip-body">' +
        '<div class="zip-row">' +
        '<span class="zip-name">' +
        name +
        "/</span>" +
        '<span class="zip-pct">0%</span></div>' +
        '<div class="zip-bar"><div class="zip-bar-fill"></div></div>' +
        '<div class="zip-detail">Scanning files…</div>' +
        "</div>"
      );
    },

    start: function (jobId, name) {
      this._ensureContainer();
      var div = document.createElement("div");
      div.className = "zip-card zip-card--active";
      div.dataset.jobId = jobId;
      div.innerHTML = this._cardHTML(jobId, name);
      this.container.appendChild(div);
      this.cards[jobId] = { el: div, sse: null, name: name };
      this._listen(jobId, name);
    },

    _listen: function (jobId, name) {
      var card = this.cards[jobId];
      if (!card) return;
      card.sse = new EventSource("/__api__/zip-progress?id=" + jobId);

      card.sse.onmessage = function (e) {
        var d = JSON.parse(e.data);
        zipTray._updateCard(jobId, d);

        if (d.status === "done") {
          card.sse.close();
          card.sse = null;
          zipTray._triggerDownload(jobId, name);
        } else if (d.status === "error") {
          card.sse.close();
          card.sse = null;
        } else if (d.status === "cancelled") {
          card.sse.close();
          card.sse = null;
          zipTray.removeCard(jobId);
        }
      };

      card.sse.onerror = function () {
        card.sse.close();
        card.sse = null;
      };
    },

    _updateCard: function (jobId, d) {
      var card = this.cards[jobId];
      if (!card) return;
      var el = card.el;
      var pct =
        d.total_bytes > 0
          ? Math.round((d.bytes_processed / d.total_bytes) * 100)
          : 0;

      el.querySelector(".zip-bar-fill").style.width = pct + "%";
      el.querySelector(".zip-pct").textContent = pct + "%";
      var title = el.querySelector(".zip-title");
      var detail = el.querySelector(".zip-detail");

      if (d.status === "scanning") {
        title.innerHTML = '<span class="zip-spinner"></span>Scanning…';
        detail.textContent = "Discovering files…";
      } else if (d.status === "zipping") {
        title.innerHTML = '<span class="zip-spinner"></span>Zipping…';
        detail.textContent =
          d.processed_files +
          " / " +
          d.total_files +
          " files  ·  " +
          fmtSize(d.bytes_processed) +
          " / " +
          fmtSize(d.total_bytes);
      } else if (d.status === "done") {
        title.innerHTML = "&#10003; ZIP Ready";
        el.querySelector(".zip-pct").textContent = "100%";
        el.querySelector(".zip-bar-fill").style.width = "100%";
        detail.textContent = "ZIP size: " + fmtSize(d.zip_size);
        el.className = "zip-card zip-card--done";
      } else if (d.status === "error") {
        title.innerHTML = "&#10007; Failed";
        detail.textContent = d.error || "Unknown error";
        el.className = "zip-card zip-card--error";
      }
    },

    _triggerDownload: function (jobId, name) {
      var a = document.createElement("a");
      a.href = "/__api__/zip-download?id=" + jobId;
      a.download = name + ".zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
    },

    closeCard: function (jobId) {
      var card = this.cards[jobId];
      if (!card) return;
      var isActive = card.el.classList.contains("zip-card--active");
      if (isActive && card.sse) {
        card.sse.close();
        card.sse = null;
        fetch("/__api__/zip-cancel", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: jobId }),
        });
        toast("ZIP cancelled", "info");
      }
      this.removeCard(jobId);
    },

    removeCard: function (jobId) {
      var card = this.cards[jobId];
      if (!card) return;
      if (card.sse) card.sse.close();
      card.el.classList.add("zip-card--removing");
      setTimeout(function () {
        card.el.remove();
        delete zipTray.cards[jobId];
      }, 250);
    },

    toggleCard: function (jobId) {
      var card = this.cards[jobId];
      if (card) card.el.classList.toggle("zip-card--collapsed");
    },
  };

  window.zipTrayToggle = function (id) {
    zipTray.toggleCard(id);
  };
  window.zipTrayClose = function (id) {
    zipTray.closeCard(id);
  };

  window.downloadZip = function (dirPath, name) {
    fetch("/__api__/zip-start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: dirPath }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.error) {
          toast(d.error, "error");
          return;
        }
        zipTray.start(d.job_id, name);
      })
      .catch(function () {
        toast("Failed to start ZIP download", "error");
      });
  };

  window.addEventListener("beforeunload", function () {
    var ids = Object.keys(zipTray.cards);
    for (var i = 0; i < ids.length; i++) {
      var card = zipTray.cards[ids[i]];
      if (card && card.sse) {
        card.sse.close();
        var blob = new Blob([JSON.stringify({ id: ids[i] })], {
          type: "application/json",
        });
        navigator.sendBeacon("/__api__/zip-cancel", blob);
      }
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      window.closeDeleteModal && window.closeDeleteModal();
      window.closeInputModal && window.closeInputModal();
    }
    var delModal = document.getElementById("delete-modal");
    if (e.key === "Enter" && delModal && delModal.classList.contains("open")) {
      window.confirmDelete && window.confirmDelete();
    }
    var inpModal = document.getElementById("input-modal");
    if (e.key === "Enter" && inpModal && inpModal.classList.contains("open")) {
      var btn = document.getElementById("input-modal-ok");
      if (btn) btn.click();
    }
  });
})();
