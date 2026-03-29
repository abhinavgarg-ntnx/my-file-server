/* ===================================================================
   Caffrey's File Server — ChartMuseum Dashboard
   =================================================================== */

(function () {
  "use strict";

  var API = "/__api__/cm";

  /* ── Health check ─────────────────────────────────────────────── */

  function checkHealth() {
    fetch(API + "/health")
      .then(function (r) {
        var dot = document.getElementById("cm-dot");
        var txt = document.getElementById("cm-health-text");
        if (r.ok) {
          dot.classList.add("up");
          txt.textContent = "ChartMuseum is running";
          loadCharts();
        } else {
          dot.classList.add("down");
          txt.textContent = "ChartMuseum returned " + r.status;
        }
      })
      .catch(function () {
        var dot = document.getElementById("cm-dot");
        var txt = document.getElementById("cm-health-text");
        dot.classList.add("down");
        txt.textContent = "ChartMuseum is unreachable — run: caffrey restart";
        document.getElementById("cm-body").innerHTML =
          '<tr><td colspan="6" class="cm-loading cm-err">' +
          "ChartMuseum is not running</td></tr>";
      });
  }

  /* ── Load & render chart list ─────────────────────────────────── */

  var _allCharts = [];

  function loadCharts() {
    fetch(API + "/api/charts")
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data.error) {
          document.getElementById("cm-body").innerHTML =
            '<tr><td colspan="6" class="cm-loading cm-err">' +
            data.error +
            "</td></tr>";
          return;
        }
        _allCharts = [];
        var names = Object.keys(data).sort();
        names.forEach(function (name) {
          var versions = data[name];
          if (!versions || !versions.length) return;
          var latest = versions[0];
          _allCharts.push({
            name: name,
            version: latest.version || "",
            appVersion: latest.appVersion || "",
            description: latest.description || "",
            created: latest.created || "",
            versionCount: versions.length,
            allVersions: versions,
          });
        });
        renderCharts(_allCharts);
      })
      .catch(function () {
        document.getElementById("cm-body").innerHTML =
          '<tr><td colspan="6" class="cm-loading cm-err">' +
          "Failed to load charts</td></tr>";
      });
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    var mon = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return mon[d.getMonth()] + " " + d.getDate() + ", " + d.getFullYear();
  }

  function renderCharts(charts) {
    var body = document.getElementById("cm-body");
    var count = document.getElementById("cm-count");
    count.textContent =
      charts.length + " chart" + (charts.length !== 1 ? "s" : "");

    if (!charts.length) {
      body.innerHTML =
        '<tr><td colspan="6" class="cm-loading">' +
        "No charts in repository. Upload one above!</td></tr>";
      return;
    }

    var html = "";
    charts.forEach(function (c) {
      var badge =
        c.versionCount > 1
          ? ' <span class="cm-ver-badge">' + c.versionCount + " versions</span>"
          : "";
      html +=
        "<tr>" +
        '<td class="cm-name">' +
        '<span class="cm-chart-icon">&#x2B22;</span> ' +
        esc(c.name) +
        badge +
        "</td>" +
        "<td><code>" +
        esc(c.version) +
        "</code></td>" +
        "<td>" +
        esc(c.appVersion) +
        "</td>" +
        '<td class="cm-desc">' +
        esc(c.description) +
        "</td>" +
        '<td class="cm-date">' +
        fmtDate(c.created) +
        "</td>" +
        '<td class="cm-actions">' +
        '<button class="act-btn info-btn" title="Chart details"' +
        " onclick=\"cmShowDetail('" +
        escAttr(c.name) +
        "','" +
        escAttr(c.version) +
        "')\">" +
        SVG_INFO +
        "</button>" +
        '<button class="act-btn dl-btn" title="Download"' +
        " onclick=\"cmDownload('" +
        escAttr(c.name) +
        "','" +
        escAttr(c.version) +
        "')\">" +
        SVG_DL +
        "</button>" +
        '<button class="act-btn del-btn" title="Delete"' +
        " onclick=\"cmDelete('" +
        escAttr(c.name) +
        "','" +
        escAttr(c.version) +
        "')\">" +
        SVG_DEL +
        "</button>" +
        '<button class="act-btn view-btn" title="All versions"' +
        " onclick=\"cmVersions('" +
        escAttr(c.name) +
        "')\">" +
        SVG_LIST +
        "</button>" +
        "</td></tr>";
    });
    body.innerHTML = html;
  }

  /* ── Search filter ────────────────────────────────────────────── */

  var searchEl = document.getElementById("cm-search");
  if (searchEl) {
    searchEl.addEventListener("input", function () {
      var q = searchEl.value.toLowerCase().trim();
      if (!q) {
        renderCharts(_allCharts);
        return;
      }
      var filtered = _allCharts.filter(function (c) {
        return (
          c.name.toLowerCase().indexOf(q) !== -1 ||
          c.description.toLowerCase().indexOf(q) !== -1 ||
          c.version.indexOf(q) !== -1
        );
      });
      renderCharts(filtered);
    });
  }

  /* ── Upload toggle ────────────────────────────────────────────── */

  window.cmToggleUpload = function () {
    var section = document.getElementById("cm-upload-section");
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

  /* ── Import modal ────────────────────────────────────────────── */

  window.cmShowImport = function () {
    var m = document.getElementById("import-modal");
    if (m) m.classList.add("open");
    var el = document.getElementById("chart-name");
    if (el)
      setTimeout(function () {
        el.focus();
      }, 100);
  };

  window.cmCloseImport = function () {
    var m = document.getElementById("import-modal");
    if (m) m.classList.remove("open");
    var stat = document.getElementById("chart-status");
    if (stat) {
      stat.textContent = "";
      stat.className = "chart-status";
    }
  };

  /* ── Upload chart ─────────────────────────────────────────────── */

  function setupUploadZone() {
    var zone = document.getElementById("cm-upload-zone");
    var input = document.getElementById("cm-upload-input");
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
      if (e.dataTransfer.files.length) uploadChart(e.dataTransfer.files[0]);
    });
    input.addEventListener("change", function () {
      if (input.files.length) uploadChart(input.files[0]);
    });
  }

  function uploadChart(file) {
    var stat = document.getElementById("cm-upload-status");
    if (!file.name.match(/\.tgz$|\.tar\.gz$/)) {
      stat.textContent = "Please select a .tgz chart package";
      stat.className = "chart-status error";
      return;
    }
    stat.textContent = "Uploading " + file.name + "...";
    stat.className = "chart-status";

    var fd = new FormData();
    fd.append("chart", file);

    fetch(API + "/api/charts", { method: "POST", body: fd })
      .then(function (r) {
        return r.json().then(function (d) {
          return { ok: r.ok, data: d };
        });
      })
      .then(function (res) {
        if (res.ok && res.data.saved) {
          stat.textContent = "Uploaded " + file.name + " successfully";
          stat.className = "chart-status success";
          window._toast && window._toast("Chart uploaded!", "success");
          loadCharts();
        } else {
          stat.textContent = res.data.error || "Upload failed";
          stat.className = "chart-status error";
        }
      })
      .catch(function () {
        stat.textContent = "Upload failed — network error";
        stat.className = "chart-status error";
      });
  }

  /* ── Download chart ───────────────────────────────────────────── */

  window.cmDownload = function (name, version) {
    var metaUrl =
      API +
      "/api/charts/" +
      encodeURIComponent(name) +
      "/" +
      encodeURIComponent(version);
    fetch(metaUrl)
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d && d.urls && d.urls.length) {
          var dlUrl = d.urls[0];
          if (dlUrl.indexOf("://") === -1) {
            dlUrl = API + "/" + dlUrl;
          }
          window.open(dlUrl, "_blank");
        } else {
          window.open(
            API +
              "/charts/" +
              encodeURIComponent(name + "-" + version + ".tgz"),
            "_blank",
          );
        }
      })
      .catch(function () {
        window._toast && window._toast("Download failed", "error");
      });
  };

  /* ── Delete chart (with confirmation modal) ──────────────────── */

  var _cmDelName = "";
  var _cmDelVersion = "";

  window.cmDelete = function (name, version) {
    _cmDelName = name;
    _cmDelVersion = version;
    var m = document.getElementById("cm-delete-modal");
    var label = document.getElementById("cm-delete-label");
    if (label) label.textContent = name + " v" + version;
    if (m) m.classList.add("open");
  };

  window.cmCloseDelete = function () {
    var m = document.getElementById("cm-delete-modal");
    if (m) m.classList.remove("open");
  };

  window.cmConfirmDelete = function () {
    var name = _cmDelName;
    var version = _cmDelVersion;
    window.cmCloseDelete();
    fetch(
      API +
        "/api/charts/" +
        encodeURIComponent(name) +
        "/" +
        encodeURIComponent(version),
      { method: "DELETE" },
    )
      .then(function (r) {
        return r.json().then(function (d) {
          return { ok: r.ok, data: d };
        });
      })
      .then(function (res) {
        if (res.ok && res.data.deleted) {
          window._toast &&
            window._toast("Deleted " + name + " v" + version, "success");
          loadCharts();
        } else {
          window._toast &&
            window._toast(res.data.error || "Delete failed", "error");
        }
      })
      .catch(function () {
        window._toast && window._toast("Delete failed", "error");
      });
  };

  /* ── Show all versions ────────────────────────────────────────── */

  window.cmVersions = function (name) {
    fetch(API + "/api/charts/" + encodeURIComponent(name))
      .then(function (r) {
        return r.json();
      })
      .then(function (versions) {
        if (!versions || !versions.length) {
          window._toast && window._toast("No versions found", "info");
          return;
        }
        var body = document.getElementById("cm-body");
        var html =
          '<tr class="cm-ver-header"><td colspan="6">' +
          "<strong>" +
          esc(name) +
          "</strong> &mdash; " +
          versions.length +
          " version(s)" +
          ' <button class="cm-close-ver" onclick="cmCloseVersions()">Back to list</button>' +
          "</td></tr>";
        versions.forEach(function (v) {
          html +=
            "<tr>" +
            '<td class="cm-name">' +
            esc(v.name) +
            "</td>" +
            "<td><code>" +
            esc(v.version) +
            "</code></td>" +
            "<td>" +
            esc(v.appVersion || "") +
            "</td>" +
            '<td class="cm-desc">' +
            esc(v.description || "") +
            "</td>" +
            '<td class="cm-date">' +
            fmtDate(v.created) +
            "</td>" +
            '<td class="cm-actions">' +
            '<button class="act-btn info-btn" title="Chart details"' +
            " onclick=\"cmShowDetail('" +
            escAttr(v.name) +
            "','" +
            escAttr(v.version) +
            "')\">" +
            SVG_INFO +
            "</button>" +
            '<button class="act-btn dl-btn" title="Download"' +
            " onclick=\"cmDownload('" +
            escAttr(v.name) +
            "','" +
            escAttr(v.version) +
            "')\">" +
            SVG_DL +
            "</button>" +
            '<button class="act-btn del-btn" title="Delete this version"' +
            " onclick=\"cmDelete('" +
            escAttr(v.name) +
            "','" +
            escAttr(v.version) +
            "')\">" +
            SVG_DEL +
            "</button>" +
            "</td></tr>";
        });
        body.innerHTML = html;
        document.getElementById("cm-count").textContent =
          name + ": " + versions.length + " version(s)";
      });
  };

  window.cmCloseVersions = function () {
    renderCharts(_allCharts);
  };

  /* ── Chart detail panel ───────────────────────────────────────── */

  window.cmShowDetail = function (name, version) {
    fetch(API + "/api/charts/" + encodeURIComponent(name) + "/" + encodeURIComponent(version))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || d.error) {
          window._toast && window._toast(d.error || "Chart not found", "error");
          return;
        }
        document.getElementById("cm-detail-name").textContent = d.name || name;
        document.getElementById("cm-detail-ver").textContent = "v" + (d.version || version);
        document.getElementById("cm-detail-desc").textContent = d.description || "No description";

        var grid = document.getElementById("cm-detail-grid");
        var rows = [];
        if (d.appVersion) rows.push(["App Version", esc(d.appVersion)]);
        if (d.apiVersion) rows.push(["Chart API", esc(d.apiVersion)]);
        if (d.created) rows.push(["Created", fmtDate(d.created)]);
        if (d.home) rows.push(["Home", '<a href="' + esc(d.home) + '" target="_blank" rel="noopener">' + esc(d.home) + "</a>"]);
        if (d.sources && d.sources.length) {
          rows.push(["Sources", d.sources.map(function (s) {
            return '<a href="' + esc(s) + '" target="_blank" rel="noopener">' + esc(s) + "</a>";
          }).join("<br>")]);
        }
        if (d.maintainers && d.maintainers.length) {
          rows.push(["Maintainers", d.maintainers.map(function (m) {
            var t = esc(m.name || "");
            if (m.email) t += ' <span style="opacity:.6">&lt;' + esc(m.email) + "&gt;</span>";
            return t;
          }).join(", ")]);
        }
        if (d.keywords && d.keywords.length) {
          rows.push(["Keywords", d.keywords.map(function (k) {
            return '<span class="cm-keyword">' + esc(k) + "</span>";
          }).join(" ")]);
        }
        if (d.type) rows.push(["Type", esc(d.type)]);
        grid.innerHTML = rows.map(function (r) {
          return '<div class="cm-detail-label">' + r[0] + '</div><div class="cm-detail-value">' + r[1] + "</div>";
        }).join("");

        var repoCmd = document.getElementById("repo-cmd");
        var repoUrl = repoCmd ? repoCmd.textContent.split(" ").pop() : "";
        document.getElementById("cm-detail-install-cmd").textContent =
          "helm install " + name + " caffrey/" + name + " --version " + (d.version || version);

        var dlUrl = "";
        if (d.urls && d.urls.length) {
          dlUrl = d.urls[0];
          if (dlUrl.indexOf("://") === -1) dlUrl = repoUrl + "/" + dlUrl;
        } else {
          dlUrl = repoUrl + "/charts/" + name + "-" + (d.version || version) + ".tgz";
        }
        document.getElementById("cm-detail-dl-url").textContent = dlUrl;

        document.getElementById("cm-detail-modal").classList.add("open");
      })
      .catch(function () {
        window._toast && window._toast("Failed to load chart details", "error");
      });
  };

  window.cmCloseDetail = function () {
    document.getElementById("cm-detail-modal").classList.remove("open");
  };

  window.cmCopyInstall = function () {
    var t = document.getElementById("cm-detail-install-cmd").textContent;
    _copyText(t);
  };

  window.cmCopyDlUrl = function () {
    var t = document.getElementById("cm-detail-dl-url").textContent;
    _copyText(t);
  };

  function _copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        window._toast && window._toast("Copied to clipboard", "success");
      });
    } else {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      window._toast && window._toast("Copied to clipboard", "success");
    }
  }

  /* ── Copy repo command ────────────────────────────────────────── */

  window.copyRepoCmd = function () {
    var cmd = document.getElementById("repo-cmd");
    if (!cmd) return;
    var text = cmd.textContent.trim();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        window._toast && window._toast("Copied to clipboard", "success");
      });
    } else {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      window._toast && window._toast("Copied to clipboard", "success");
    }
  };

  /* ── Inline SVGs ──────────────────────────────────────────────── */

  var SVG_INFO =
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
    '<path stroke-linecap="round" stroke-linejoin="round" ' +
    'd="M11.25 11.25l.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0' +
    ' 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0zm-9-3.75h.008' +
    'v.008H12V8.25z"/></svg>';

  var SVG_DL =
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
    '<path stroke-linecap="round" stroke-linejoin="round" ' +
    'd="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5' +
    "A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12L12 16.5m0 0" +
    'L7.5 12m4.5 4.5V3"/></svg>';

  var SVG_DEL =
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
    '<path stroke-linecap="round" stroke-linejoin="round" ' +
    'd="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166' +
    "m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0" +
    " 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12" +
    " .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0" +
    "v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037" +
    '-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"/></svg>';

  var SVG_LIST =
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
    '<path stroke-linecap="round" stroke-linejoin="round" ' +
    'd="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008' +
    "H3.75V6.75zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0" +
    "zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 1 1-.75 0" +
    " .375.375 0 0 1 .75 0zM3.75 17.25h.007v.008H3.75v-.008zm.375" +
    ' 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0z"/></svg>';

  /* ── Helpers ──────────────────────────────────────────────────── */

  function esc(s) {
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  function escAttr(s) {
    return s.replace(/'/g, "\\'").replace(/"/g, "&quot;");
  }

  window._cmRefresh = loadCharts;

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      window.cmCloseImport && window.cmCloseImport();
      window.cmCloseDelete && window.cmCloseDelete();
      window.cmCloseDetail && window.cmCloseDetail();
    }
  });

  /* ── Init ─────────────────────────────────────────────────────── */

  setupUploadZone();
  checkHealth();
})();
