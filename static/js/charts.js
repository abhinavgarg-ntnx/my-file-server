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
          '<tr><td colspan="5" class="cm-loading cm-err">' +
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
            '<tr><td colspan="5" class="cm-loading cm-err">' +
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
      .catch(function (err) {
        document.getElementById("cm-body").innerHTML =
          '<tr><td colspan="5" class="cm-loading cm-err">' +
          "Failed to load charts</td></tr>";
      });
  }

  function renderCharts(charts) {
    var body = document.getElementById("cm-body");
    var count = document.getElementById("cm-count");
    count.textContent =
      charts.length + " chart" + (charts.length !== 1 ? "s" : "");

    if (!charts.length) {
      body.innerHTML =
        '<tr><td colspan="5" class="cm-loading">' +
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
        '<td class="cm-actions">' +
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
        "</td>" +
        "</tr>";
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
    if (section) {
      section.classList.toggle("open");
      if (section.classList.contains("open")) {
        setTimeout(function () {
          section.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }, 50);
      }
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
    var url =
      "/__api__/cm/charts/" +
      encodeURIComponent(name) +
      "/" +
      encodeURIComponent(version);
    fetch(url)
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d && d.urls && d.urls.length) {
          window.open(d.urls[0], "_blank");
        } else {
          window._toast && window._toast("No download URL found", "error");
        }
      })
      .catch(function () {
        window._toast && window._toast("Download failed", "error");
      });
  };

  /* ── Delete chart ─────────────────────────────────────────────── */

  window.cmDelete = function (name, version) {
    if (!confirm("Delete " + name + " v" + version + "?")) return;
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
          '<tr class="cm-ver-header"><td colspan="5">' +
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
            '<td class="cm-actions">' +
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

  var SVG_DL =
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
    '<path stroke-linecap="round" stroke-linejoin="round" ' +
    'd="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5' +
    "A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12L12 16.5m0 0" +
    'L7.5 12m4.5 4.5V3"/></svg>';

  var SVG_DEL =
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
    '<path stroke-linecap="round" stroke-linejoin="round" ' +
    'd="M6 18L18 6M6 6l12 12"/></svg>';

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
    if (e.key === "Escape") window.cmCloseImport && window.cmCloseImport();
  });

  /* ── Init ─────────────────────────────────────────────────────── */

  setupUploadZone();
  checkHealth();
})();
