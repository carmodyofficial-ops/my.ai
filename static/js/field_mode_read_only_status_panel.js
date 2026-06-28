(function () {
  "use strict";

  var VERSION = "S7C5_read_only_field_mode_status_panel";
  var SNAPSHOT_URL = "/static/field_mode_status_snapshot.json";
  var S7D2_FIELD_MODE_LOCKOUT_STATE_URL = "/static/field_mode_lockout_state.json";
  var PANEL_ID = "myai-field-mode-read-only-status-panel";

  function safeText(value, fallback) {
    if (value === null || value === undefined || value === "") return fallback || "unknown";
    return String(value);
  }

  function boolLabel(value) {
    return value === true ? "yes" : value === false ? "no" : "unknown";
  }

  function statusBadge(ok) {
    var span = document.createElement("span");
    span.textContent = ok ? "OK" : "Review";
    span.style.display = "inline-block";
    span.style.padding = "2px 8px";
    span.style.borderRadius = "999px";
    span.style.fontSize = "11px";
    span.style.fontWeight = "700";
    span.style.border = "1px solid " + (ok ? "#b7d7b7" : "#e0b4b4");
    span.style.background = ok ? "#eef8ee" : "#fff1f1";
    span.style.color = ok ? "#215b21" : "#7a2222";
    return span;
  }

  function addRow(container, label, value, ok) {
    var row = document.createElement("div");
    row.style.display = "flex";
    row.style.justifyContent = "space-between";
    row.style.gap = "12px";
    row.style.padding = "6px 0";
    row.style.borderBottom = "1px solid rgba(0,0,0,0.06)";

    var left = document.createElement("div");
    left.textContent = label;
    left.style.fontWeight = "600";

    var right = document.createElement("div");
    right.style.textAlign = "right";
    right.style.maxWidth = "60%";

    if (typeof ok === "boolean") {
      right.appendChild(statusBadge(ok));
      var valueSpan = document.createElement("span");
      valueSpan.textContent = " " + value;
      right.appendChild(valueSpan);
    } else {
      right.textContent = value;
    }

    row.appendChild(left);
    row.appendChild(right);
    container.appendChild(row);
  }

  function findMount() {
    return (
      document.getElementById("myai-operator-guardrail-dashboard") ||
      document.getElementById("myai-left-nav-guardrail-group") ||
      document.querySelector("main") ||
      document.body
    );
  }

  function render(snapshot, lockout) {
    var existing = document.getElementById(PANEL_ID);
    if (existing && existing.parentNode) existing.parentNode.removeChild(existing);

    var fieldMode = snapshot.field_mode || {};
    var runtime = snapshot.runtime_status || {};
    var model = snapshot.model_endpoint_posture || {};
    var queue = snapshot.proposal_queue || {};
    var classifier = snapshot.classifier || {};
    var guardrails = snapshot.guardrails || {};
    lockout = lockout || {};

    var panel = document.createElement("section");
    panel.id = PANEL_ID;
    panel.setAttribute("aria-label", "Read-only Field Mode status");
    panel.style.margin = "12px";
    panel.style.padding = "14px";
    panel.style.border = "1px solid rgba(0,0,0,0.12)";
    panel.style.borderRadius = "12px";
    panel.style.background = "#f6f6f6";
    panel.style.color = "#222";
    panel.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
    panel.style.fontSize = "13px";
    panel.style.lineHeight = "1.35";
    panel.style.boxShadow = "0 1px 4px rgba(0,0,0,0.08)";

    var title = document.createElement("div");
    title.textContent = "Field Mode: Read-only status";
    title.style.fontSize = "15px";
    title.style.fontWeight = "800";
    title.style.marginBottom = "4px";
    panel.appendChild(title);

    var subtitle = document.createElement("div");
    subtitle.textContent = "Visibility only. No remote execution, no queue execution, no protected mutations.";
    subtitle.style.fontSize = "12px";
    subtitle.style.opacity = "0.78";
    subtitle.style.marginBottom = "10px";
    panel.appendChild(subtitle);

    var rows = document.createElement("div");
    panel.appendChild(rows);

    addRow(rows, "Phase", safeText(fieldMode.field_mode_phase, "unknown"));
    addRow(rows, "Full remote Field Mode", boolLabel(fieldMode.field_mode_full_remote_applied), fieldMode.field_mode_full_remote_applied === false);
    addRow(rows, "Remote ingestion", boolLabel(fieldMode.remote_ingestion_enabled), fieldMode.remote_ingestion_enabled === false);
    addRow(rows, "Execution", boolLabel(fieldMode.execution_enabled), fieldMode.execution_enabled === false);
    addRow(rows, "Proposal queue execution", boolLabel(fieldMode.proposal_queue_execution_enabled), fieldMode.proposal_queue_execution_enabled === false);
    addRow(rows, "Queue file movement", boolLabel(fieldMode.queue_file_movement_enabled), fieldMode.queue_file_movement_enabled === false);
    addRow(rows, "Model endpoint hardened", boolLabel(model.wildcard_11434_absent && model.app_model_access_preserved), model.wildcard_11434_absent === true && model.app_model_access_preserved === true);
    addRow(rows, "LAN model endpoint", safeText(model.lan_model_endpoint_status, "unknown"), model.lan_model_endpoint_status === "blocked_or_not_exposed");
    addRow(rows, "LAN app", safeText(runtime.lan_app_http, "unknown"), runtime.lan_app_http === "200" || runtime.lan_app_http === "302");
    addRow(rows, "Local model", safeText(runtime.local_model_http, "unknown"), runtime.local_model_http === "200");
    addRow(rows, "Classifier accepted", boolLabel(classifier.accepted), classifier.accepted === true);
    addRow(rows, "Queue samples", safeText((queue.counts || {}).samples, "0"));
    addRow(rows, "Emergency lockout", safeText(lockout.lockout_state, "unknown"), lockout.lockout_state === "locked");
    addRow(rows, "Raw command guardrail", boolLabel(guardrails.raw_shell_blocked), guardrails.raw_shell_blocked === true);
    addRow(rows, "Protected surfaces blocked", boolLabel(guardrails.protected_surfaces_blocked), guardrails.protected_surfaces_blocked === true);

    var footer = document.createElement("div");
    footer.style.marginTop = "10px";
    footer.style.fontSize = "11px";
    footer.style.opacity = "0.7";
    footer.textContent = "Snapshot: " + safeText(snapshot.generated_at, "unknown") + " | " + VERSION;
    panel.appendChild(footer);

    var mount = findMount();
    if (mount === document.body) {
      panel.style.position = "fixed";
      panel.style.right = "16px";
      panel.style.bottom = "16px";
      panel.style.maxWidth = "420px";
      panel.style.zIndex = "9999";
    }

    mount.appendChild(panel);
  }

  function renderError(message) {
    var panel = document.createElement("section");
    panel.id = PANEL_ID;
    panel.style.margin = "12px";
    panel.style.padding = "14px";
    panel.style.border = "1px solid #e0b4b4";
    panel.style.borderRadius = "12px";
    panel.style.background = "#fff1f1";
    panel.style.color = "#7a2222";
    panel.textContent = "Field Mode status snapshot unavailable: " + message;
    findMount().appendChild(panel);
  }

  function init() {
    Promise.all([
      fetch(SNAPSHOT_URL, { cache: "no-store" }).then(function (response) {
        if (!response.ok) throw new Error("status snapshot HTTP " + response.status);
        return response.json();
      }),
      fetch(S7D2_FIELD_MODE_LOCKOUT_STATE_URL, { cache: "no-store" }).then(function (response) {
        if (!response.ok) throw new Error("lockout state HTTP " + response.status);
        return response.json();
      })
    ])
      .then(function (results) {
        render(results[0], results[1]);
      })
      .catch(function (error) {
        renderError(error && error.message ? error.message : "unknown error");
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
