(function(){
  'use strict';
  var STATUS = {
  "version": "S5E_proposal_lifecycle_status_readonly",
  "readonly": true,
  "timestamp_utc": "2026-06-24T12:35:07Z",
  "status": "PASS",
  "destructive_cleanup_performed": false,
  "audit_history_deleted": false,
  "counts": {
    "approval_packet_count": 14,
    "report_json_count": 1150,
    "runbook_count": 47,
    "pending_or_stale_approval_count": 10,
    "lifecycle_status_counts": {
      "applied": 15,
      "approved": 4,
      "closed": 13,
      "committed_local": 4,
      "pending_approval": 1,
      "planned": 10,
      "stale_review": 825,
      "validated": 292
    }
  },
  "summary_report": "data/projectforge_sme/s5_controlled_refinement/reports/s5e_proposal_lifecycle_status_summary.json"
};
  window.MYAI_PROPOSAL_LIFECYCLE_STATUS = STATUS;
  function textCounts(){
    var c = STATUS.counts || {};
    var lc = c.lifecycle_status_counts || {};
    return 'Reports: ' + (c.report_json_count || 0) +
      ' | Approvals: ' + (c.approval_packet_count || 0) +
      ' | Pending/stale approvals: ' + (c.pending_or_stale_approval_count || 0) +
      ' | Closed: ' + (lc.closed || 0) +
      ' | Local commits: ' + (lc.committed_local || 0);
  }

  function ensureLeftMenuRefresh(){
    try {
      if (window.MYAI_OPERATOR_GUARDRAIL_DASHBOARD &&
          typeof window.MYAI_OPERATOR_GUARDRAIL_DASHBOARD.ensureLeftMenuItems === 'function') {
        window.MYAI_OPERATOR_GUARDRAIL_DASHBOARD.ensureLeftMenuItems();
      }
    } catch (e) {}
  }

  function inject(){
    var panel = document.getElementById('myai-operator-guardrail-dashboard');
    if (!panel || document.getElementById('myai-proposal-lifecycle-status-row')) return;
    var row = document.createElement('div');
    row.id = 'myai-proposal-lifecycle-status-row';
    row.setAttribute('data-version', STATUS.version);
    row.style.cssText = 'padding:8px 0;border-top:1px solid rgba(120,120,120,.18)';
    var head = document.createElement('div');
    head.style.cssText = 'display:flex;justify-content:space-between;gap:10px;align-items:center;';
    var strong = document.createElement('strong');
    strong.textContent = 'Proposal lifecycle';
    strong.style.cssText = 'font-size:13px;';
    var badge = document.createElement('span');
    badge.textContent = 'Read-only: OK';
    badge.style.cssText = 'display:inline-flex;padding:4px 7px;border-radius:999px;border:1px solid rgba(80,130,80,.35);background:rgba(235,248,235,.96);color:#222;font-size:12px;white-space:nowrap';
    head.appendChild(strong); head.appendChild(badge);
    var body = document.createElement('div');
    body.textContent = textCounts();
    body.style.cssText = 'margin-top:4px;color:#444;font-size:12px;line-height:1.35;';
    var note = document.createElement('div');
    note.textContent = 'Non-destructive lifecycle visibility only. Audit artifacts are preserved.';
    note.style.cssText = 'margin-top:3px;color:#666;font-size:11px;line-height:1.3;';
    row.appendChild(head); row.appendChild(body); row.appendChild(note);
    var footer = panel.lastElementChild;
    if (footer && /Visibility only/i.test(footer.textContent || '')) panel.insertBefore(row, footer);
    else panel.appendChild(row);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ inject(); ensureLeftMenuRefresh(); });
  else { inject(); ensureLeftMenuRefresh(); }
  var observer = new MutationObserver(function(){ inject(); ensureLeftMenuRefresh(); });
  if (document.documentElement) observer.observe(document.documentElement, {childList:true, subtree:true});
})();
