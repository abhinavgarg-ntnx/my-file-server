/* ===================================================================
   Caffrey's File Server — Editor Page
   =================================================================== */

(function () {
  "use strict";

  var ta = document.getElementById("editor-content");
  if (!ta) return;

  var ext = ta.dataset.ext;
  var path = ta.dataset.path;

  fetch("/__api__/readfile?path=" + encodeURIComponent(path))
    .then(function (r) {
      return r.json();
    })
    .then(function (d) {
      if (d.content !== undefined) ta.value = d.content;
      else ta.value = "Error: " + d.error;
    });

  ta.addEventListener("keydown", function (e) {
    if (e.key === "Tab") {
      e.preventDefault();
      var s = ta.selectionStart;
      var end = ta.selectionEnd;
      ta.value = ta.value.substring(0, s) + "  " + ta.value.substring(end);
      ta.selectionStart = ta.selectionEnd = s + 2;
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      window.saveFile();
    }
  });

  function validate(content, fileExt) {
    if (fileExt === ".json") {
      try {
        JSON.parse(content);
      } catch (x) {
        return "Invalid JSON: " + x.message;
      }
    }
    return null;
  }

  window.saveFile = function () {
    var stat = document.getElementById("editor-status");
    var content = ta.value;
    var err = validate(content, ext);
    if (err) {
      stat.textContent = err;
      stat.className = "chart-status error";
      return;
    }
    stat.textContent = "Saving...";
    stat.className = "chart-status";
    fetch("/__api__/savefile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path, content: content }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.success) {
          stat.textContent = "";
          stat.className = "chart-status";
          window._toast && window._toast("Saved", "success");
          var backBtn = document.querySelector(".cm-back-btn");
          if (backBtn && backBtn.href) {
            setTimeout(function () {
              window.location.href = backBtn.href;
            }, 600);
          }
        } else {
          stat.textContent = d.error;
          stat.className = "chart-status error";
        }
      });
  };
})();
