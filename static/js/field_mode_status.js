(function () {
  "use strict";

  var PANEL_ID = "myai-field-mode-status-panel";
  var VERSION = "S5A5_compact_field_mode_status_chip";

  function resolveFieldMode() {
    if (window.MYAI_FIELD_MODE) return String(window.MYAI_FIELD_MODE);
    if (document.body && document.body.dataset && document.body.dataset.fieldMode) {
      return String(document.body.dataset.fieldMode);
    }
    var node = document.querySelector("[data-field-mode]");
    if (node) return String(node.getAttribute("data-field-mode") || "");
    return "field_disabled";
  }

  function labelForMode(mode) {
    if (mode === "field_disabled") return "Disabled";
    return mode.replace(/^field_/, "").replace(/_/g, " ");
  }

  function isDisabled(mode) {
    return mode === "field_disabled" || !mode;
  }

  function createPanel() {
    if (document.getElementById(PANEL_ID)) return;

    var mode = resolveFieldMode();
    var panel = document.createElement("aside");
    panel.id = PANEL_ID;
    panel.setAttribute("role", "status");
    panel.setAttribute("aria-live", "polite");
    panel.setAttribute("data-version", VERSION);

    // Rendered as a compact item in the left sidebar menu (not a floating pill).
    panel.style.cssText = [
      "box-sizing:border-box",
      "display:block",
      "width:auto",
      "margin:6px 8px",
      "padding:7px 10px",
      "border:1px solid rgba(120,120,120,.28)",
      "border-radius:10px",
      "background:rgba(127,127,127,.10)",
      "color:inherit",
      "font:12px/1.25 system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif"
    ].join(";");

    var status = document.createElement("div");
    status.style.cssText = [
      "display:flex",
      "align-items:center",
      "gap:8px",
      "white-space:nowrap"
    ].join(";");

    var dot = document.createElement("span");
    dot.setAttribute("aria-hidden", "true");
    dot.style.cssText = [
      "display:inline-block",
      "width:8px",
      "height:8px",
      "border-radius:50%",
      "background:" + (isDisabled(mode) ? "#777" : "#b36b00"),
      "flex:0 0 auto"
    ].join(";");

    var text = document.createElement("span");
    text.textContent = "Field Mode: " + labelForMode(mode);
    text.style.cssText = "font-weight:600;";

    var button = document.createElement("button");
    button.type = "button";
    button.textContent = "Guide";
    button.setAttribute("aria-expanded", "false");
    button.style.cssText = [
      "border:0",
      "background:transparent",
      "color:inherit",
      "opacity:.75",
      "font:12px system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif",
      "text-decoration:underline",
      "cursor:pointer",
      "padding:0",
      "margin-left:auto"
    ].join(";");

    var details = document.createElement("div");
    details.hidden = true;
    details.style.cssText = [
      "margin-top:8px",
      "padding-top:8px",
      "border-top:1px solid rgba(120,120,120,.25)",
      "white-space:normal",
      "font-size:12px",
      "line-height:1.35",
      "opacity:.85",
      "color:inherit"
    ].join(";");
    details.textContent = "Keep Field Mode disabled unless explicitly approved. Preserve Guest restrictions, auth, model endpoint isolation, and approval gates. If remote behavior is suspected, stop and rerun S4D/S4F validation.";

    button.addEventListener("click", function () {
      details.hidden = !details.hidden;
      button.setAttribute("aria-expanded", details.hidden ? "false" : "true");
    });

    status.appendChild(dot);
    status.appendChild(text);
    status.appendChild(button);
    panel.appendChild(status);
    panel.appendChild(details);
    var target = document.querySelector(".sidebar-inner")
      || document.getElementById("sidebar")
      || document.body;
    target.appendChild(panel);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createPanel);
  } else {
    createPanel();
  }

  window.MYAI_FIELD_MODE_STATUS_UX = {
    version: VERSION,
    panelId: PANEL_ID,
    compact: true,
    resolveFieldMode: resolveFieldMode
  };
})();
