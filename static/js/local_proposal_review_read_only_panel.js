(() => {
  const PANEL_ID = "myai-local-proposal-review-panel";
  const SNAPSHOT_URL = "/static/local_proposal_review_snapshot.json";

  const escapeHtml = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const normalizeSnapshot = (snapshot) => {
    const acceptedGates = snapshot?.accepted_gates || snapshot?.gates || {};
    const health = snapshot?.health || {};
    const lockout =
      snapshot?.lockout_status ||
      snapshot?.lockout ||
      snapshot?.field_mode_lockout ||
      "unknown";

    return {
      lockout,
      acceptedGates,
      health,
      raw: snapshot || {},
    };
  };

  const summarizeGateStatus = (acceptedGates) => {
    const values = Object.values(acceptedGates || {}).map((value) => String(value || ""));
    if (!values.length) return "NO GATES";
    if (values.every((value) => value.includes("PASS"))) return "PASS";
    if (values.some((value) => value.includes("FAIL"))) return "ATTN";
    return "CHECK";
  };

  const rowsFromObject = (obj) => {
    const entries = Object.entries(obj || {});
    if (!entries.length) {
      return `<tr><td colspan="2" class="myai-lpr-empty">No data available</td></tr>`;
    }

    return entries
      .map(
        ([key, value]) => `
          <tr>
            <th>${escapeHtml(key)}</th>
            <td>${escapeHtml(value)}</td>
          </tr>
        `
      )
      .join("");
  };

  const ensureStyles = () => {
    if (document.getElementById(`${PANEL_ID}-style`)) return;

    const style = document.createElement("style");
    style.id = `${PANEL_ID}-style`;
    style.textContent = `
      #${PANEL_ID} {
        /* Rendered inline as a compact item in the left sidebar menu (not floating). */
        width: auto;
        margin: 6px 8px;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: inherit;
      }

      #${PANEL_ID} * {
        box-sizing: border-box;
      }

      #${PANEL_ID} details {
        pointer-events: auto;
      }

      #${PANEL_ID} summary {
        list-style: none;
        cursor: pointer;
        user-select: none;
        border: 1px solid rgba(148, 163, 184, 0.45);
        background: rgba(248, 250, 252, 0.96);
        color: #334155;
        border-radius: 999px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
        padding: 8px 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        font-size: 12px;
        line-height: 1.2;
      }

      #${PANEL_ID} summary::-webkit-details-marker {
        display: none;
      }

      #${PANEL_ID} .myai-lpr-title {
        font-weight: 700;
        letter-spacing: 0.01em;
        white-space: nowrap;
      }

      #${PANEL_ID} .myai-lpr-summary {
        opacity: 0.82;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      #${PANEL_ID} .myai-lpr-card {
        margin-top: 8px;
        border: 1px solid rgba(148, 163, 184, 0.4);
        background: rgba(255, 255, 255, 0.98);
        border-radius: 16px;
        box-shadow: 0 14px 36px rgba(15, 23, 42, 0.16);
        overflow: hidden;
        max-height: min(56vh, 520px);
        display: flex;
        flex-direction: column;
      }

      #${PANEL_ID} .myai-lpr-header {
        padding: 12px 14px;
        border-bottom: 1px solid rgba(226, 232, 240, 0.9);
      }

      #${PANEL_ID} .myai-lpr-heading {
        font-size: 14px;
        font-weight: 800;
        margin: 0 0 4px;
        color: #111827;
      }

      #${PANEL_ID} .myai-lpr-note {
        font-size: 12px;
        line-height: 1.35;
        margin: 0;
        color: #64748b;
      }

      #${PANEL_ID} .myai-lpr-body {
        overflow: auto;
        padding: 10px 14px 14px;
      }

      #${PANEL_ID} .myai-lpr-section-title {
        font-size: 11px;
        font-weight: 800;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 12px 0 6px;
      }

      #${PANEL_ID} table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
      }

      #${PANEL_ID} th,
      #${PANEL_ID} td {
        border-top: 1px solid rgba(226, 232, 240, 0.95);
        padding: 6px 0;
        vertical-align: top;
      }

      #${PANEL_ID} th {
        width: 45%;
        text-align: left;
        color: #64748b;
        font-weight: 650;
        padding-right: 10px;
      }

      #${PANEL_ID} td {
        color: #1f2937;
        word-break: break-word;
      }

      #${PANEL_ID} .myai-lpr-empty {
        color: #94a3b8;
        font-style: italic;
      }

      @media (max-width: 720px) {
        #${PANEL_ID} summary {
          padding: 7px 10px;
        }
      }
    `;
    document.head.appendChild(style);
  };

  const renderPanel = (snapshot) => {
    const existing = document.getElementById(PANEL_ID);
    if (existing) existing.remove();

    const data = normalizeSnapshot(snapshot);
    const gateSummary = summarizeGateStatus(data.acceptedGates);
    const lockoutText = String(data.lockout || "unknown");

    const root = document.createElement("aside");
    root.id = PANEL_ID;
    root.setAttribute("aria-label", "Local proposal review read-only status");

    root.innerHTML = `
      <details>
        <summary title="Open local proposal review diagnostics">
          <span class="myai-lpr-title">Local Review</span>
          <span class="myai-lpr-summary">Lockout: ${escapeHtml(lockoutText)} • ${escapeHtml(gateSummary)}</span>
        </summary>

        <div class="myai-lpr-card">
          <div class="myai-lpr-header">
            <p class="myai-lpr-heading">Local Proposal Review - Read Only</p>
            <p class="myai-lpr-note">
              Static visibility only. No queue movement, proposal execution, backend route, or remote ingestion.
            </p>
          </div>

          <div class="myai-lpr-body">
            <div class="myai-lpr-section-title">Status</div>
            <table>
              <tr>
                <th>Lockout</th>
                <td>${escapeHtml(lockoutText)}</td>
              </tr>
              <tr>
                <th>Gate summary</th>
                <td>${escapeHtml(gateSummary)}</td>
              </tr>
            </table>

            <div class="myai-lpr-section-title">Accepted gates</div>
            <table>
              ${rowsFromObject(data.acceptedGates)}
            </table>

            <div class="myai-lpr-section-title">Health</div>
            <table>
              ${rowsFromObject(data.health)}
            </table>
          </div>
        </div>
      </details>
    `;

    const target = document.querySelector(".sidebar-inner")
      || document.getElementById("sidebar")
      || document.body;
    target.appendChild(root);

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        const details = root.querySelector("details");
        if (details) details.open = false;
      }
    });
  };

  const init = async () => {
    ensureStyles();

    try {
      const response = await fetch(SNAPSHOT_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`snapshot HTTP ${response.status}`);
      const snapshot = await response.json();
      renderPanel(snapshot);
    } catch (error) {
      renderPanel({
        lockout_status: "unknown",
        accepted_gates: {
          snapshot: "UNAVAILABLE",
        },
        health: {
          error: error?.message || "Failed to load local proposal review snapshot",
        },
      });
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

  // D4_MIRROR_ONLY_PATCH_MARKER
  // Mirror-only marker used to validate dev/mirror patch, diff, and review flow.
  // This line must never be promoted without local operator review.
