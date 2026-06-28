// static/js/workspace.js
//
// Workspace picker: browse server directories in a draggable modal, choose a
// folder, and show it as a removable pill in the chat input bar. While set, the
// chat request sends `workspace` so the agent's file/shell tools are confined
// to that folder (see routes/chat_routes.py + src/tool_execution.py).

import Storage, { KEYS } from './storage.js';
import uiModule from './ui.js';
import { makeWindowDraggable } from './windowDrag.js';

const API_BASE = window.location.origin;
// Same folder glyph as the overflow menu item + pill (not an emoji).
const _FOLDER_SVG = '<svg class="workspace-row-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>';
let _modal = null;
let _curPath = '';

export function getWorkspace() {
  return Storage.get(KEYS.WORKSPACE, '') || '';
}

function _basename(p) {
  if (!p) return '';
  // Handle both POSIX (/) and Windows (\) separators.
  const parts = p.replace(/[\\/]+$/, '').split(/[\\/]/);
  return parts[parts.length - 1] || p;
}

// Workspace only applies to agent mode (it scopes the file/shell tools), so the
// pill + overflow entry are hidden in chat mode, like the bash toggle.
function _isChatMode() {
  const b = document.getElementById('mode-chat-btn');
  return !!(b && b.classList.contains('active'));
}

export function syncWorkspaceIndicator(path) {
  const chat = _isChatMode();
  const pill = document.getElementById('workspace-indicator-btn');
  const name = document.getElementById('workspace-indicator-name');
  const overflow = document.getElementById('overflow-workspace-btn');
  if (pill) {
    pill.style.display = (path && !chat) ? '' : 'none';
    pill.classList.toggle('active', !!path);
    if (path) pill.title = `Workspace: ${path}\nFile tools are confined here; shell commands start here but are not sandboxed and can reach outside it.\nClick to clear.`;
  }
  if (name) name.textContent = path ? _basename(path) : '';
  if (overflow) {
    overflow.style.display = chat ? 'none' : '';
    overflow.classList.toggle('active', !!path);
  }
  // Recompute the "+" overflow dot (app.js owns updatePlusDot via this event).
  try { document.dispatchEvent(new CustomEvent('overflow-state-change')); } catch (_) {}
}

// Called by the agent/chat mode toggle so the pill + overflow entry follow mode.
export function applyMode(_mode) {
  syncWorkspaceIndicator(getWorkspace());
}

export function setWorkspace(path) {
  if (path) Storage.set(KEYS.WORKSPACE, path);
  else Storage.remove(KEYS.WORKSPACE);
  syncWorkspaceIndicator(path || '');
}

/**
 * Validate a manually entered path server-side, then persist the canonical
 * form. Returns {ok, path|null}. Without this, a typo / file path / deleted
 * folder / filesystem root would be stored and shown as active while the
 * backend silently refuses to bind it on every send.
 */
export async function vetAndSetWorkspace(path) {
  try {
    const res = await fetch(`${API_BASE}/api/workspace/vet?path=${encodeURIComponent(path)}`, { credentials: 'same-origin' });
    if (!res.ok) return { ok: false, path: null };
    const data = await res.json();
    if (data.ok && data.path) {
      setWorkspace(data.path);
      return { ok: true, path: data.path };
    }
    return { ok: false, path: null };
  } catch (e) {
    return { ok: false, path: null };
  }
}

export function clearWorkspace() {
  setWorkspace('');
  if (uiModule && uiModule.showToast) uiModule.showToast('Workspace cleared');
}

async function _load(path) {
  const url = `${API_BASE}/api/workspace/browse${path ? `?path=${encodeURIComponent(path)}` : ''}`;
  const res = await fetch(url, { credentials: 'same-origin' });
  if (!res.ok) throw new Error(`browse failed: ${res.status}`);
  return res.json();
}

function _render(data) {
  _curPath = data.path;
  const body = _modal.querySelector('#workspace-body');
  const pathEl = _modal.querySelector('#workspace-cur-path');
  if (pathEl) {
    // Reflect the resolved (realpath) location back into the editable field.
    pathEl.value = data.path;
    pathEl.title = data.path;
  }
  let rows = '';
  if (data.parent) {
    rows += `<div class="workspace-row workspace-up" data-path="${encodeURIComponent(data.parent)}">↑ ..</div>`;
  }
  for (const d of data.dirs) {
    // Backend supplies the full child path (os.path.join → cross-platform).
    rows += `<div class="workspace-row" data-path="${encodeURIComponent(d.path)}">${_FOLDER_SVG}<span>${uiModule.esc(d.name)}</span></div>`;
  }
  if (data.truncated) {
    rows += '<div class="workspace-empty">Too many folders to list. Type or paste a path above to jump in.</div>';
  }
  if (!data.dirs.length && !data.parent) rows = '<div class="workspace-empty">No subfolders</div>';
  body.innerHTML = rows || '<div class="workspace-empty">No subfolders</div>';
  body.querySelectorAll('.workspace-row').forEach((row) => {
    row.addEventListener('click', () => _navigate(decodeURIComponent(row.dataset.path)));
  });
  // Filesystem roots (and sensitive dirs) can be browsed through but never
  // bound as the workspace; the backend rejects them too.
  const useBtn = _modal.querySelector('#workspace-use');
  if (useBtn) {
    useBtn.disabled = data.selectable === false;
    useBtn.title = data.selectable === false ? 'This folder cannot be used as a workspace' : '';
  }
}

async function _navigate(path) {
  try {
    _render(await _load(path));
  } catch (e) {
    if (uiModule && uiModule.showError) uiModule.showError('Could not open folder');
  }
}

function _getModal() {
  if (_modal) return _modal;
  _modal = document.createElement('div');
  _modal.id = 'workspace-modal';
  _modal.className = 'modal';
  _modal.style.display = 'none';
  _modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h4><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:6px"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>Select workspace</h4>
        <button class="close-btn" id="workspace-close" aria-label="Close">✖</button>
      </div>
      <input type="text" class="styled-prompt-input workspace-cur" id="workspace-cur-path"
             spellcheck="false" autocomplete="off" autocapitalize="off" autocorrect="off"
             placeholder="Type or paste a folder path, then press Enter" />
      <p class="muted workspace-note">File tools are <strong>confined</strong> to this folder. Shell commands start here but are <strong>not sandboxed</strong> and can reach outside it. A workspace scopes the tools; it is not a security boundary.</p>
      <div class="modal-body workspace-body" id="workspace-body"></div>
      <div class="modal-footer workspace-footer">
        <button type="button" class="confirm-btn confirm-btn-secondary" id="workspace-cancel">Cancel</button>
        <button type="button" class="confirm-btn confirm-btn-primary" id="workspace-use">Use this folder</button>
      </div>
    </div>`;
  document.body.appendChild(_modal);
  _modal.querySelector('#workspace-close').addEventListener('click', closeWorkspaceBrowser);
  _modal.querySelector('#workspace-cancel').addEventListener('click', closeWorkspaceBrowser);
  // Editable path bar: Enter navigates to a typed/pasted folder.
  _modal.querySelector('#workspace-cur-path').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const v = e.target.value.trim();
      if (v) _navigate(v);
    }
  });
  _modal.querySelector('#workspace-use').addEventListener('click', () => {
    setWorkspace(_curPath);
    if (uiModule && uiModule.showToast) uiModule.showToast(`Workspace set: ${_basename(_curPath)}`);
    closeWorkspaceBrowser();
  });
  const content = _modal.querySelector('.modal-content');
  const header = _modal.querySelector('.modal-header');
  if (content && header) makeWindowDraggable(_modal, { content, header });
  return _modal;
}

export async function openWorkspaceBrowser() {
  const modal = _getModal();
  modal.style.display = 'flex';
  try {
    _render(await _load(getWorkspace() || ''));
  } catch (e) {
    if (uiModule && uiModule.showError) uiModule.showError('Could not browse folders');
  }
}

export function closeWorkspaceBrowser() {
  if (_modal) _modal.style.display = 'none';
}

export function initWorkspace() {
  // Restore persisted workspace into the pill on load.
  syncWorkspaceIndicator(getWorkspace());
  const overflow = document.getElementById('overflow-workspace-btn');
  if (overflow) overflow.addEventListener('click', openWorkspaceBrowser);
  const pill = document.getElementById('workspace-indicator-btn');
  if (pill) pill.addEventListener('click', clearWorkspace);
}

export default { initWorkspace, openWorkspaceBrowser, getWorkspace, setWorkspace, vetAndSetWorkspace, clearWorkspace, syncWorkspaceIndicator, applyMode };


// ProjectForge Workspace Planner MVP
(function () {
  const MODAL_ID = 'projectforge-workspace-planner-modal';
  const BTN_ID = 'projectforge-workspace-planner-btn';

  function ensureStyles() {
    if (document.getElementById('projectforge-workspace-planner-style')) return;
    const style = document.createElement('style');
    style.id = 'projectforge-workspace-planner-style';
    style.textContent = `
      #${MODAL_ID} {
        position: fixed; inset: 0; z-index: 9999;
        display: none; align-items: center; justify-content: center;
        background: rgba(0,0,0,.45);
      }
      #${MODAL_ID}.open { display: flex; }
      .pfws-panel {
        width: min(980px, 94vw); max-height: 90vh; overflow: auto;
        background: var(--surface, #111827); color: var(--text, #f9fafb);
        border: 1px solid rgba(255,255,255,.14); border-radius: 16px;
        box-shadow: 0 24px 80px rgba(0,0,0,.45);
      }
      .pfws-header, .pfws-footer {
        padding: 14px 18px; display: flex; align-items: center; justify-content: space-between;
        border-bottom: 1px solid rgba(255,255,255,.12);
      }
      .pfws-footer { border-top: 1px solid rgba(255,255,255,.12); border-bottom: 0; }
      .pfws-body { padding: 18px; display: grid; gap: 14px; }
      .pfws-textarea {
        width: 100%; min-height: 150px; resize: vertical; box-sizing: border-box;
        border-radius: 12px; border: 1px solid rgba(255,255,255,.16);
        background: rgba(255,255,255,.06); color: inherit; padding: 12px;
      }
      .pfws-actions { display: flex; gap: 10px; flex-wrap: wrap; }
      .pfws-btn {
        border: 1px solid rgba(255,255,255,.18); border-radius: 10px;
        padding: 9px 12px; background: rgba(255,255,255,.08); color: inherit;
        cursor: pointer;
      }
      .pfws-btn.primary { background: #2563eb; border-color: #2563eb; color: #fff; }
      .pfws-pre {
        white-space: pre-wrap; overflow: auto; max-height: 45vh;
        background: rgba(0,0,0,.24); border: 1px solid rgba(255,255,255,.12);
        border-radius: 12px; padding: 12px; font-size: 12px;
      }
      #${BTN_ID} {
        width: calc(100% - 16px); margin: 8px; justify-content: flex-start;
      }
    `;
    document.head.appendChild(style);
  }

  function ensureModal() {
    ensureStyles();
    let modal = document.getElementById(MODAL_ID);
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = MODAL_ID;
    modal.innerHTML = `
      <div class="pfws-panel" role="dialog" aria-modal="true" aria-label="Workspace Planner">
        <div class="pfws-header">
          <strong>Workspace</strong>
          <button class="pfws-btn" data-pfws-close>Close</button>
        </div>
        <div class="pfws-body">
          <div>
            <div style="font-size:13px;opacity:.78;margin-bottom:8px;">
              Enter a local task prompt. Odysseus will classify it, build a ProjectForge SME agent team, and generate a guarded task packet. MVP does not auto-execute.
            </div>
            <textarea class="pfws-textarea" id="pfws-prompt" placeholder="Example: Build a local-only project tracker web app..."></textarea>
          </div>
          <div class="pfws-actions">
            <button class="pfws-btn primary" id="pfws-plan-btn">Review & Build Team</button>
            <button class="pfws-btn" id="pfws-history-btn">Load Recent Requests</button>
          </div>
          <pre class="pfws-pre" id="pfws-output">Workspace planner ready.</pre>
        </div>
        <div class="pfws-footer">
          <span style="font-size:12px;opacity:.72;">Local-only · No GitHub sync · v13_verified/v14/no-v15</span>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    modal.querySelector('[data-pfws-close]')?.addEventListener('click', () => modal.classList.remove('open'));

    modal.querySelector('#pfws-plan-btn')?.addEventListener('click', async () => {
      const prompt = modal.querySelector('#pfws-prompt')?.value || '';
      const out = modal.querySelector('#pfws-output');
      if (!prompt.trim()) {
        out.textContent = 'Enter a prompt first.';
        return;
      }
      out.textContent = 'Building Workspace plan...';
      try {
        const res = await fetch('/api/workspace/plan', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        out.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        out.textContent = `Workspace plan failed: ${err && err.message ? err.message : err}`;
      }
    });

    modal.querySelector('#pfws-history-btn')?.addEventListener('click', async () => {
      const out = modal.querySelector('#pfws-output');
      out.textContent = 'Loading recent Workspace requests...';
      try {
        const res = await fetch('/api/workspace/requests', { credentials: 'same-origin' });
        const data = await res.json();
        out.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        out.textContent = `Workspace history failed: ${err && err.message ? err.message : err}`;
      }
    });

    return modal;
  }

  function openWorkspacePlanner() {
    ensureModal().classList.add('open');
  }

  function installWorkspacePlannerButton() {
    if (document.getElementById(BTN_ID)) return;
    ensureStyles();
    const btn = document.createElement('button');
    btn.id = BTN_ID;
    btn.className = 'pfws-btn';
    btn.type = 'button';
    btn.textContent = 'Workspace';
    btn.addEventListener('click', openWorkspacePlanner);

    const sidebar = document.getElementById('sidebar')
      || document.querySelector('.sidebar')
      || document.querySelector('[data-sidebar]')
      || document.body;

    sidebar.appendChild(btn);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installWorkspacePlannerButton);
  } else {
    installWorkspacePlannerButton();
  }

  window.ProjectForgeWorkspacePlanner = { open: openWorkspacePlanner };
})();


// ProjectForge Workspace V2 full-page planner
(function () {
  const OVERLAY_ID = 'pfws-v2-overlay';
  const BTN_TEXT_RE = /^(workspace|review\s*&?\s*build\s*team|build\s*team)$/i;
  let activeRequest = null;

  function el(id) { return document.getElementById(id); }

  function pretty(obj) {
    return JSON.stringify(obj, null, 2);
  }

  function parseJsonTextarea(id) {
    const raw = el(id)?.value || '';
    try {
      return JSON.parse(raw);
    } catch (err) {
      throw new Error(`Invalid JSON in ${id}: ${err.message}`);
    }
  }

  async function apiJson(url, options = {}) {
    const res = await fetch(url, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options
    });
    const text = await res.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; }
    catch { data = { raw: text }; }
    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}: ${data.detail || data.raw || 'request failed'}`);
    }
    return data;
  }

  function ensureStyles() {
    if (el('pfws-v2-style')) return;
    const style = document.createElement('style');
    style.id = 'pfws-v2-style';
    style.textContent = `
      #${OVERLAY_ID} {
        position: fixed; inset: 0; z-index: 2147483000;
        display: none; background: rgba(3,7,18,.72); color: var(--text, #f9fafb);
      }
      #${OVERLAY_ID}.open { display: block; }
      .pfws-v2-shell {
        position: absolute; inset: 24px; display: grid;
        grid-template-columns: 320px minmax(0, 1fr);
        border: 1px solid rgba(255,255,255,.14); border-radius: 18px;
        background: var(--surface, #0f172a);
        box-shadow: 0 24px 90px rgba(0,0,0,.55);
        overflow: hidden;
      }
      .pfws-v2-sidebar {
        border-right: 1px solid rgba(255,255,255,.12); padding: 16px; overflow: auto;
        background: rgba(255,255,255,.035);
      }
      .pfws-v2-main { display: grid; grid-template-rows: auto 1fr; min-width: 0; }
      .pfws-v2-header {
        padding: 14px 18px; display: flex; align-items: center; justify-content: space-between;
        border-bottom: 1px solid rgba(255,255,255,.12);
      }
      .pfws-v2-content {
        padding: 16px; overflow: auto; display: grid; gap: 14px;
      }
      .pfws-v2-grid {
        display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
      }
      .pfws-v2-card {
        border: 1px solid rgba(255,255,255,.12); border-radius: 14px; padding: 12px;
        background: rgba(255,255,255,.045);
      }
      .pfws-v2-title { font-weight: 800; margin-bottom: 8px; }
      .pfws-v2-muted { opacity: .72; font-size: 12px; }
      .pfws-v2-textarea {
        width: 100%; box-sizing: border-box; border-radius: 12px; padding: 10px;
        border: 1px solid rgba(255,255,255,.16); background: rgba(0,0,0,.25);
        color: inherit; min-height: 120px; resize: vertical; font-family: inherit;
      }
      .pfws-v2-json { min-height: 320px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
      .pfws-v2-btn {
        border: 1px solid rgba(255,255,255,.18); border-radius: 10px;
        padding: 9px 12px; background: rgba(255,255,255,.08); color: inherit;
        cursor: pointer; margin: 3px;
      }
      .pfws-v2-btn.primary { background: #2563eb; border-color: #2563eb; color: #fff; }
      .pfws-v2-btn.danger { background: #7f1d1d; border-color: #991b1b; color: #fff; }
      .pfws-v2-history-item {
        width: 100%; text-align: left; margin: 5px 0; padding: 9px;
        border-radius: 10px; border: 1px solid rgba(255,255,255,.10);
        background: rgba(255,255,255,.05); color: inherit; cursor: pointer;
      }
      .pfws-v2-history-item:hover { background: rgba(255,255,255,.10); }
      .pfws-v2-pre {
        white-space: pre-wrap; overflow: auto; max-height: 260px;
        background: rgba(0,0,0,.24); border: 1px solid rgba(255,255,255,.12);
        border-radius: 12px; padding: 10px; font-size: 12px;
      }
      @media (max-width: 900px) {
        .pfws-v2-shell { inset: 8px; grid-template-columns: 1fr; }
        .pfws-v2-sidebar { border-right: 0; border-bottom: 1px solid rgba(255,255,255,.12); max-height: 240px; }
        .pfws-v2-grid { grid-template-columns: 1fr; }
      }
    `;
    document.head.appendChild(style);
  }

  function ensureOverlay() {
    ensureStyles();
    if (el(OVERLAY_ID)) return el(OVERLAY_ID);

    const overlay = document.createElement('div');
    overlay.id = OVERLAY_ID;
    overlay.innerHTML = `
      <div class="pfws-v2-shell" role="dialog" aria-modal="true" aria-label="ProjectForge Workspace">
        <aside class="pfws-v2-sidebar">
          <div class="pfws-v2-title">Workspace History</div>
          <button class="pfws-v2-btn primary" id="pfws-v2-new">New Request</button>
          <button class="pfws-v2-btn" id="pfws-v2-refresh">Refresh</button>
          <div class="pfws-v2-muted" style="margin:10px 0;">Local-only task packets and guard plans.</div>
          <div id="pfws-v2-history"></div>
        </aside>
        <main class="pfws-v2-main">
          <header class="pfws-v2-header">
            <div>
              <strong>my.ai Workspace</strong>
              <div class="pfws-v2-muted">Planner → Team → Task Packet → Guard Plan → Approval Marker. No automatic execution.</div>
            </div>
            <button class="pfws-v2-btn" id="pfws-v2-close">Close</button>
          </header>
          <section class="pfws-v2-content">
            <div class="pfws-v2-card">
              <div class="pfws-v2-title">Prompt Intake</div>
              <textarea id="pfws-v2-prompt" class="pfws-v2-textarea" placeholder="Describe what you want my.ai to plan..."></textarea>
              <div style="margin-top:8px;">
                <button class="pfws-v2-btn primary" id="pfws-v2-build-team">Build Team</button>
                <button class="pfws-v2-btn" id="pfws-v2-load-latest">Load Latest</button>
                <button class="pfws-v2-btn primary" id="pfws-static-load-approved" type="button">Load Latest Approved</button>
                <button class="pfws-v2-btn" id="pfws-static-prepare-run" type="button">Prepare Run Envelope</button>
              </div>
            </div>

            <div class="pfws-v2-grid">
              <div class="pfws-v2-card">
                <div class="pfws-v2-title">Classification + Team</div>
                <pre class="pfws-v2-pre" id="pfws-v2-summary">No active request.</pre>
              </div>
              <div class="pfws-v2-card">
                <div class="pfws-v2-title">Evidence Checklist</div>
                <div id="pfws-v2-evidence" class="pfws-v2-muted">No evidence requirements yet.</div>
              </div>
            </div>

            <div class="pfws-v2-grid">
              <div class="pfws-v2-card">
                <div class="pfws-v2-title">Editable Task Packet</div>
                <textarea id="pfws-v2-task-packet" class="pfws-v2-textarea pfws-v2-json"></textarea>
                <button class="pfws-v2-btn" id="pfws-v2-save-task">Save Task Packet</button>
              </div>
              <div class="pfws-v2-card">
                <div class="pfws-v2-title">Editable Guard Plan</div>
                <textarea id="pfws-v2-guard-plan" class="pfws-v2-textarea pfws-v2-json"></textarea>
                <button class="pfws-v2-btn" id="pfws-v2-save-guard">Save Guard Plan</button>
              </div>
            </div>

            <div class="pfws-v2-card">
              <div class="pfws-v2-title">Approval Gate</div>
              <div class="pfws-v2-muted">Creates an approval marker only. It does not run agents or shell commands.</div>
              <textarea id="pfws-v2-approval-note" class="pfws-v2-textarea" style="min-height:70px;" placeholder="Optional operator approval note..."></textarea>
              <button class="pfws-v2-btn danger" id="pfws-v2-approve">Approve Guarded Run Preparation</button>
              <pre class="pfws-v2-pre" id="pfws-v2-status">Ready.</pre>
            </div>
          </section>
        </main>
      </div>
    `;
    document.body.appendChild(overlay);

    el('pfws-v2-close').addEventListener('click', () => overlay.classList.remove('open'));
    el('pfws-v2-new').addEventListener('click', newRequest);
    el('pfws-v2-refresh').addEventListener('click', loadHistory);
    el('pfws-v2-build-team').addEventListener('click', buildTeam);
    el('pfws-v2-load-latest').addEventListener('click', loadLatest);

    const staticLoadApproved = el('pfws-static-load-approved');
    if (staticLoadApproved) {
      staticLoadApproved.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        const api = window.ProjectForgeWorkspaceLatestApproved;
        if (api && typeof api.loadLatestApproved === 'function') {
          api.loadLatestApproved().catch(err => setStatus(`Load Latest Approved failed: ${err.message || err}`));
        } else {
          setStatus('Load Latest Approved handler is unavailable. Hard refresh and reopen Workspace.');
        }
      });
    }

    const staticPrepareRun = el('pfws-static-prepare-run');
    if (staticPrepareRun) {
      staticPrepareRun.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        const api = window.ProjectForgeWorkspaceLatestApproved;
        if (api && typeof api.prepareRunEnvelope === 'function') {
          api.prepareRunEnvelope().catch(err => setStatus(`Prepare Run Envelope failed: ${err.message || err}`));
        } else {
          setStatus('Prepare Run Envelope handler is unavailable. Hard refresh and reopen Workspace.');
        }
      });
    }
    el('pfws-v2-save-task').addEventListener('click', saveTaskPacket);
    el('pfws-v2-save-guard').addEventListener('click', saveGuardPlan);
    el('pfws-v2-approve').addEventListener('click', approveGuardedRun);

    return overlay;
  }

  function setStatus(msg, obj) {
    const out = el('pfws-v2-status');
    if (!out) return;
    out.textContent = obj ? `${msg}\n\n${pretty(obj)}` : msg;
  }

  function renderRequest(record) {
    activeRequest = record;
    if (!record) {
      el('pfws-v2-summary').textContent = 'No active request.';
      el('pfws-v2-evidence').textContent = 'No evidence requirements yet.';
      el('pfws-v2-task-packet').value = '';
      el('pfws-v2-guard-plan').value = '';
      return;
    }

    const summary = {
      id: record.id,
      owner: record.owner,
      classification: record.classification,
      selected_skills: record.selected_skills,
      local_only: record.local_only,
      git_sync_allowed: record.git_sync_allowed,
      approval_status: record.approval_status || null
    };
    el('pfws-v2-summary').textContent = pretty(summary);
    el('pfws-v2-task-packet').value = pretty(record.task_packet || {});
    el('pfws-v2-guard-plan').value = pretty(record.guard_plan || {});

    const reqs = record.evidence_requirements || [];
    el('pfws-v2-evidence').innerHTML = reqs.length
      ? `<ul>${reqs.map(x => `<li><label><input type="checkbox"> ${escapeHtml(String(x))}</label></li>`).join('')}</ul>`
      : 'No evidence requirements.';
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  async function openWorkspaceV2() {
    ensureOverlay().classList.add('open');
    await loadHistory();
  }

  function newRequest() {
    activeRequest = null;
    el('pfws-v2-prompt').value = '';
    renderRequest(null);
    setStatus('Ready for a new request.');
  }

  async function buildTeam() {
    const prompt = (el('pfws-v2-prompt')?.value || '').trim();
    if (!prompt) {
      setStatus('Enter a prompt first.');
      return;
    }
    setStatus('Building ProjectForge Workspace team and task packet...');
    try {
      const record = await apiJson('/api/workspace/plan', {
        method: 'POST',
        body: JSON.stringify({ prompt })
      });
      renderRequest(record);
      setStatus('Workspace team built and persisted.', { id: record.id, classification: record.classification });
      await loadHistory(false);
    } catch (err) {
      setStatus(`Build Team failed: ${err.message || err}`);
    }
  }

  async function loadHistory(updateStatus = true) {
    try {
      const data = await apiJson('/api/workspace/requests');
      const box = el('pfws-v2-history');
      if (!box) return;
      const items = data.items || [];
      if (!items.length) {
        box.innerHTML = '<div class="pfws-v2-muted">No Workspace requests yet.</div>';
      } else {
        box.innerHTML = items.map(item => `
          <button class="pfws-v2-history-item" data-pfws-id="${escapeHtml(item.id)}">
            <div><strong>${escapeHtml(item.classification?.request_type || 'request')}</strong></div>
            <div class="pfws-v2-muted">${escapeHtml(item.id || '')}</div>
            <div class="pfws-v2-muted">${escapeHtml(item.prompt_preview || '')}</div>
          </button>
        `).join('');
        box.querySelectorAll('[data-pfws-id]').forEach(btn => {
          btn.addEventListener('click', () => loadRequest(btn.getAttribute('data-pfws-id')));
        });
      }
      if (updateStatus) setStatus(`Loaded ${items.length} Workspace request(s).`);
    } catch (err) {
      setStatus(`Load history failed: ${err.message || err}`);
    }
  }

  async function loadRequest(id) {
    if (!id) return;
    setStatus(`Loading ${id}...`);
    try {
      const record = await apiJson(`/api/workspace/requests/${encodeURIComponent(id)}`);
      renderRequest(record);
      setStatus(`Loaded ${id}.`);
    } catch (err) {
      setStatus(`Load request failed: ${err.message || err}`);
    }
  }

  async function loadLatest() {
    try {
      const data = await apiJson('/api/workspace/requests');
      const first = (data.items || [])[0];
      if (!first) {
        setStatus('No requests found.');
        return;
      }
      await loadRequest(first.id);
    } catch (err) {
      setStatus(`Load latest failed: ${err.message || err}`);
    }
  }

  async function saveTaskPacket() {
    if (!activeRequest?.id) {
      setStatus('No active request to save.');
      return;
    }
    try {
      const taskPacket = parseJsonTextarea('pfws-v2-task-packet');
      const data = await apiJson(`/api/workspace/requests/${encodeURIComponent(activeRequest.id)}/task_packet`, {
        method: 'PUT',
        body: JSON.stringify({ task_packet: taskPacket })
      });
      activeRequest.task_packet = data.task_packet;
      setStatus('Task packet saved.', { id: activeRequest.id });
    } catch (err) {
      setStatus(`Save task packet failed: ${err.message || err}`);
    }
  }

  async function saveGuardPlan() {
    if (!activeRequest?.id) {
      setStatus('No active request to save.');
      return;
    }
    try {
      const guardPlan = parseJsonTextarea('pfws-v2-guard-plan');
      const data = await apiJson(`/api/workspace/requests/${encodeURIComponent(activeRequest.id)}/guard_plan`, {
        method: 'PUT',
        body: JSON.stringify({ guard_plan: guardPlan })
      });
      activeRequest.guard_plan = data.guard_plan;
      setStatus('Guard plan saved.', { id: activeRequest.id });
    } catch (err) {
      setStatus(`Save guard plan failed: ${err.message || err}`);
    }
  }

  async function approveGuardedRun() {
    if (!activeRequest?.id) {
      setStatus('No active request to approve.');
      return;
    }
    const note = el('pfws-v2-approval-note')?.value || '';
    try {
      const data = await apiJson(`/api/workspace/requests/${encodeURIComponent(activeRequest.id)}/approve`, {
        method: 'POST',
        body: JSON.stringify({ operator_note: note })
      });
      activeRequest.approval = data.approval;
      activeRequest.approval_status = data.approval.status;
      renderRequest(activeRequest);
      setStatus('Approval marker created. No agents executed.', data.approval);
      await loadHistory(false);
    } catch (err) {
      setStatus(`Approval failed: ${err.message || err}`);
    }
  }

  function installWorkspaceButtonIfMissing() {
    if (document.querySelector('[data-pfws-v2-launcher="true"]')) return;
    const existing = Array.from(document.querySelectorAll('button, a, [role="button"]'))
      .find(x => (x.textContent || '').trim().toLowerCase() === 'workspace');
    if (existing) return;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = 'Workspace';
    btn.setAttribute('data-pfws-v2-launcher', 'true');
    btn.className = 'pfws-v2-btn';
    btn.addEventListener('click', openWorkspaceV2);

    const sidebar = document.getElementById('sidebar')
      || document.querySelector('.sidebar')
      || document.querySelector('[data-sidebar]')
      || document.querySelector('nav')
      || document.body;
    sidebar.appendChild(btn);
  }

  // Capture phase fixes the current dead Build Team click path and routes Workspace opens to V2.
  document.addEventListener('click', function (event) {
    const target = event.target.closest('button, a, [role="button"]');
    if (!target) return;
    const text = (target.textContent || '').trim();
    const id = target.id || '';
    const isWorkspaceLauncher = id === 'projectforge-workspace-planner-btn'
      || target.getAttribute('data-pfws-v2-launcher') === 'true'
      || text.toLowerCase() === 'workspace';
    const isBuildTeam = id === 'pfws-plan-btn'
      || id === 'pfws-v2-build-team'
      || /^(review\s*&?\s*build\s*team|build\s*team)$/i.test(text);

    if (isWorkspaceLauncher) {
      event.preventDefault();
      event.stopImmediatePropagation();
      openWorkspaceV2();
    } else if (isBuildTeam) {
      event.preventDefault();
      event.stopImmediatePropagation();
      ensureOverlay();
      buildTeam();
    }
  }, true);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installWorkspaceButtonIfMissing);
  } else {
    installWorkspaceButtonIfMissing();
  }

  window.ProjectForgeWorkspaceV2 = {
    open: openWorkspaceV2,
    loadHistory,
    buildTeam
  };
  window.ProjectForgeWorkspacePlanner = window.ProjectForgeWorkspacePlanner || {};
  window.ProjectForgeWorkspacePlanner.open = openWorkspaceV2;
})();


// ProjectForge Workspace V2 responsive approval cleanup
(function () {
  function installWorkspaceResponsiveApprovalCleanup() {
    if (document.getElementById('pfws-v2-responsive-approval-cleanup-style')) return;

    const style = document.createElement('style');
    style.id = 'pfws-v2-responsive-approval-cleanup-style';
    style.textContent = `
      /* Workspace V2 responsive hardening */
      #pfws-v2-overlay {
        overflow: auto !important;
        padding: 12px !important;
        box-sizing: border-box !important;
      }

      #pfws-v2-overlay *,
      #pfws-v2-overlay *::before,
      #pfws-v2-overlay *::after {
        box-sizing: border-box !important;
        min-width: 0 !important;
      }

      #pfws-v2-overlay.open {
        display: block !important;
      }

      #pfws-v2-overlay .pfws-v2-shell {
        position: relative !important;
        inset: auto !important;
        width: min(1500px, calc(100vw - 24px)) !important;
        height: calc(100dvh - 24px) !important;
        max-height: calc(100dvh - 24px) !important;
        margin: 0 auto !important;
        display: grid !important;
        grid-template-columns: minmax(260px, 340px) minmax(0, 1fr) !important;
        grid-template-rows: minmax(0, 1fr) !important;
        overflow: hidden !important;
      }

      #pfws-v2-overlay .pfws-v2-sidebar {
        min-height: 0 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
      }

      #pfws-v2-overlay .pfws-v2-main {
        min-height: 0 !important;
        min-width: 0 !important;
        overflow: hidden !important;
        display: grid !important;
        grid-template-rows: auto minmax(0, 1fr) !important;
      }

      #pfws-v2-overlay .pfws-v2-header {
        gap: 12px !important;
        align-items: flex-start !important;
        flex-wrap: wrap !important;
      }

      #pfws-v2-overlay .pfws-v2-content {
        min-height: 0 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        padding-bottom: 110px !important;
      }

      #pfws-v2-overlay .pfws-v2-grid {
        display: grid !important;
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 14px !important;
      }

      #pfws-v2-overlay .pfws-v2-card {
        min-width: 0 !important;
        overflow: hidden !important;
      }

      #pfws-v2-overlay .pfws-v2-title,
      #pfws-v2-overlay .pfws-v2-muted,
      #pfws-v2-overlay .pfws-v2-pre,
      #pfws-v2-overlay textarea,
      #pfws-v2-overlay button {
        overflow-wrap: anywhere !important;
        word-break: normal !important;
      }

      #pfws-v2-overlay .pfws-v2-textarea {
        width: 100% !important;
        max-width: 100% !important;
        min-height: 110px !important;
      }

      #pfws-v2-overlay .pfws-v2-json {
        min-height: 260px !important;
        max-height: 50dvh !important;
        overflow: auto !important;
        white-space: pre !important;
        overflow-wrap: normal !important;
      }

      #pfws-v2-overlay .pfws-v2-pre {
        max-width: 100% !important;
        overflow: auto !important;
        white-space: pre-wrap !important;
      }

      #pfws-v2-overlay .pfws-v2-history-item {
        overflow: hidden !important;
      }

      #pfws-v2-approval-sticky-bar {
        position: sticky !important;
        bottom: 0 !important;
        z-index: 20 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 10px !important;
        padding: 10px 12px !important;
        margin-top: -96px !important;
        border: 1px solid rgba(255,255,255,.14) !important;
        border-radius: 14px !important;
        background: rgba(15, 23, 42, .96) !important;
        backdrop-filter: blur(10px) !important;
        box-shadow: 0 -10px 30px rgba(0,0,0,.25) !important;
      }

      #pfws-v2-approval-sticky-bar .pfws-v2-sticky-copy {
        min-width: 0 !important;
        font-size: 12px !important;
        opacity: .82 !important;
      }

      #pfws-v2-approval-sticky-bar .pfws-v2-btn {
        white-space: normal !important;
      }

      @media (max-width: 1100px) {
        #pfws-v2-overlay .pfws-v2-shell {
          grid-template-columns: minmax(220px, 290px) minmax(0, 1fr) !important;
        }

        #pfws-v2-overlay .pfws-v2-grid {
          grid-template-columns: 1fr !important;
        }
      }

      @media (max-width: 760px) {
        #pfws-v2-overlay {
          padding: 6px !important;
        }

        #pfws-v2-overlay .pfws-v2-shell {
          width: calc(100vw - 12px) !important;
          height: calc(100dvh - 12px) !important;
          max-height: calc(100dvh - 12px) !important;
          grid-template-columns: 1fr !important;
          grid-template-rows: auto minmax(0, 1fr) !important;
        }

        #pfws-v2-overlay .pfws-v2-sidebar {
          max-height: 220px !important;
          border-right: 0 !important;
          border-bottom: 1px solid rgba(255,255,255,.12) !important;
        }

        #pfws-v2-overlay .pfws-v2-header {
          padding: 10px 12px !important;
        }

        #pfws-v2-overlay .pfws-v2-content {
          padding: 10px !important;
          padding-bottom: 130px !important;
        }

        #pfws-v2-overlay .pfws-v2-card {
          padding: 10px !important;
        }

        #pfws-v2-approval-sticky-bar {
          flex-direction: column !important;
          align-items: stretch !important;
          margin-top: -120px !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function ensureApprovalStickyBar() {
    const overlay = document.getElementById('pfws-v2-overlay');
    const content = overlay ? overlay.querySelector('.pfws-v2-content') : null;
    if (!content || document.getElementById('pfws-v2-approval-sticky-bar')) return;

    const bar = document.createElement('div');
    bar.id = 'pfws-v2-approval-sticky-bar';
    bar.innerHTML = `
      <div class="pfws-v2-sticky-copy">
        <strong>Approval Gate</strong><br>
        Creates an approval marker only. No agents or shell commands execute.
      </div>
      <button class="pfws-v2-btn danger" id="pfws-v2-approve-sticky" type="button">
        Approve Guarded Run Preparation
      </button>
    `;
    content.appendChild(bar);

    const stickyButton = document.getElementById('pfws-v2-approve-sticky');
    stickyButton.addEventListener('click', function () {
      const realButton = document.getElementById('pfws-v2-approve');
      if (realButton) {
        realButton.click();
      } else {
        const status = document.getElementById('pfws-v2-status');
        if (status) {
          status.textContent = 'Approval button is not mounted yet. Close and reopen Workspace, then load a request.';
        }
      }
    });
  }

  function cleanupWorkspaceAfterOpen() {
    installWorkspaceResponsiveApprovalCleanup();

    const run = () => {
      installWorkspaceResponsiveApprovalCleanup();
      ensureApprovalStickyBar();

      const overlay = document.getElementById('pfws-v2-overlay');
      const content = overlay ? overlay.querySelector('.pfws-v2-content') : null;
      if (overlay) overlay.style.overflow = 'auto';
      if (content) content.style.overflowY = 'auto';
    };

    run();
    setTimeout(run, 100);
    setTimeout(run, 500);
  }

  document.addEventListener('click', function (event) {
    const target = event.target.closest('button, a, [role="button"]');
    if (!target) return;
    const text = (target.textContent || '').trim().toLowerCase();
    const id = target.id || '';

    if (
      text === 'workspace' ||
      id === 'projectforge-workspace-planner-btn' ||
      id === 'pfws-v2-build-team' ||
      /build\s*team/i.test(text)
    ) {
      cleanupWorkspaceAfterOpen();
    }
  }, true);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installWorkspaceResponsiveApprovalCleanup);
  } else {
    installWorkspaceResponsiveApprovalCleanup();
  }

  window.ProjectForgeWorkspaceResponsiveCleanup = {
    install: cleanupWorkspaceAfterOpen
  };
})();


// ProjectForge Workspace V2 layout cleanup
(function () {
  function installWorkspaceV2LayoutCleanup() {
    if (document.getElementById('pfws-v2-layout-cleanup-style')) return;

    const style = document.createElement('style');
    style.id = 'pfws-v2-layout-cleanup-style';
    style.textContent = `
      /* Workspace V2 layout cleanup: prioritize prompt/build area */
      #pfws-v2-overlay {
        overflow: auto !important;
        padding: 8px !important;
      }

      #pfws-v2-overlay .pfws-v2-shell {
        width: calc(100vw - 16px) !important;
        height: calc(100dvh - 16px) !important;
        max-height: calc(100dvh - 16px) !important;
        margin: 0 auto !important;
        grid-template-columns: 150px minmax(0, 1fr) !important;
        overflow: hidden !important;
      }

      /* Left column: title only, no busy history list/buttons */
      #pfws-v2-overlay .pfws-v2-sidebar {
        padding: 12px 10px !important;
        overflow: hidden !important;
        display: flex !important;
        align-items: flex-start !important;
        justify-content: center !important;
      }

      #pfws-v2-overlay .pfws-v2-sidebar .pfws-v2-title {
        display: block !important;
        writing-mode: vertical-rl !important;
        transform: rotate(180deg) !important;
        letter-spacing: .04em !important;
        margin: 0 !important;
        opacity: .86 !important;
        white-space: nowrap !important;
      }

      #pfws-v2-overlay .pfws-v2-sidebar button,
      #pfws-v2-overlay .pfws-v2-sidebar .pfws-v2-muted,
      #pfws-v2-overlay #pfws-v2-history {
        display: none !important;
      }

      #pfws-v2-overlay .pfws-v2-main {
        min-width: 0 !important;
        min-height: 0 !important;
        display: grid !important;
        grid-template-rows: auto minmax(0, 1fr) !important;
        overflow: hidden !important;
      }

      #pfws-v2-overlay .pfws-v2-header {
        padding: 10px 14px !important;
        min-height: auto !important;
      }

      #pfws-v2-overlay .pfws-v2-header strong {
        font-size: 15px !important;
      }

      #pfws-v2-overlay .pfws-v2-header .pfws-v2-muted {
        font-size: 11px !important;
        line-height: 1.25 !important;
      }

      #pfws-v2-overlay .pfws-v2-content {
        display: block !important;
        min-height: 0 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        padding: 12px !important;
        padding-bottom: 96px !important;
      }

      #pfws-v2-overlay .pfws-v2-content > .pfws-v2-card:first-child {
        position: sticky !important;
        top: 0 !important;
        z-index: 12 !important;
        margin-bottom: 12px !important;
        background: rgba(15, 23, 42, .98) !important;
        border-color: rgba(96, 165, 250, .35) !important;
        box-shadow: 0 12px 30px rgba(0,0,0,.24) !important;
      }

      #pfws-v2-overlay #pfws-v2-prompt {
        min-height: 92px !important;
        max-height: 140px !important;
        height: 112px !important;
        overflow-y: auto !important;
      }

      #pfws-v2-overlay #pfws-v2-build-team,
      #pfws-v2-overlay #pfws-v2-load-latest,
      #pfws-v2-overlay #pfws-static-load-approved,
      #pfws-v2-overlay #pfws-static-prepare-run {
        margin-top: 6px !important;
      }

      #pfws-v2-overlay .pfws-v2-grid {
        grid-template-columns: 1fr !important;
        gap: 12px !important;
        margin-bottom: 12px !important;
      }

      #pfws-v2-overlay .pfws-v2-card {
        margin-bottom: 12px !important;
        overflow: visible !important;
      }

      #pfws-v2-overlay .pfws-v2-json {
        min-height: 220px !important;
        height: 260px !important;
        max-height: 42dvh !important;
      }

      #pfws-v2-overlay .pfws-v2-pre {
        max-height: 220px !important;
      }

      #pfws-v2-approval-sticky-bar {
        margin-top: 10px !important;
      }

      @media (max-width: 900px) {
        #pfws-v2-overlay .pfws-v2-shell {
          grid-template-columns: 1fr !important;
          grid-template-rows: 42px minmax(0, 1fr) !important;
        }

        #pfws-v2-overlay .pfws-v2-sidebar {
          max-height: 42px !important;
          min-height: 42px !important;
          height: 42px !important;
          padding: 8px 12px !important;
          justify-content: flex-start !important;
          align-items: center !important;
          border-right: 0 !important;
          border-bottom: 1px solid rgba(255,255,255,.12) !important;
        }

        #pfws-v2-overlay .pfws-v2-sidebar .pfws-v2-title {
          writing-mode: horizontal-tb !important;
          transform: none !important;
          white-space: nowrap !important;
        }

        #pfws-v2-overlay .pfws-v2-content {
          padding: 10px !important;
          padding-bottom: 110px !important;
        }

        #pfws-v2-overlay #pfws-v2-prompt {
          height: 96px !important;
          min-height: 80px !important;
          max-height: 120px !important;
        }
      }

      @media (max-width: 560px) {
        #pfws-v2-overlay {
          padding: 4px !important;
        }

        #pfws-v2-overlay .pfws-v2-shell {
          width: calc(100vw - 8px) !important;
          height: calc(100dvh - 8px) !important;
          max-height: calc(100dvh - 8px) !important;
          border-radius: 12px !important;
        }

        #pfws-v2-overlay .pfws-v2-header {
          padding: 8px 10px !important;
        }

        #pfws-v2-overlay .pfws-v2-card {
          padding: 9px !important;
        }

        #pfws-v2-overlay #pfws-v2-prompt {
          height: 82px !important;
        }

        #pfws-v2-overlay .pfws-v2-json {
          height: 220px !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function simplifyHistoryRail() {
    const sidebar = document.querySelector('#pfws-v2-overlay .pfws-v2-sidebar');
    if (!sidebar || sidebar.getAttribute('data-layout-cleaned') === 'true') return;
    sidebar.setAttribute('data-layout-cleaned', 'true');

    const title = sidebar.querySelector('.pfws-v2-title');
    if (title) title.textContent = 'History';
  }

  function runLayoutCleanup() {
    installWorkspaceV2LayoutCleanup();
    simplifyHistoryRail();

    const content = document.querySelector('#pfws-v2-overlay .pfws-v2-content');
    if (content) {
      content.style.overflowY = 'auto';
      content.style.overflowX = 'hidden';
    }
  }

  document.addEventListener('click', function (event) {
    const target = event.target.closest('button, a, [role="button"]');
    if (!target) return;
    const text = (target.textContent || '').trim().toLowerCase();
    const id = target.id || '';

    if (
      text === 'workspace' ||
      id === 'projectforge-workspace-planner-btn' ||
      id === 'pfws-v2-build-team' ||
      /build\s*team/i.test(text)
    ) {
      setTimeout(runLayoutCleanup, 0);
      setTimeout(runLayoutCleanup, 100);
      setTimeout(runLayoutCleanup, 500);
    }
  }, true);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runLayoutCleanup);
  } else {
    runLayoutCleanup();
  }

  window.ProjectForgeWorkspaceLayoutCleanup = {
    install: runLayoutCleanup
  };
})();


// ProjectForge Workspace load latest approved UI
(function () {
  function el(id) { return document.getElementById(id); }

  function status(msg, obj) {
    const out = el('pfws-v2-status');
    if (out) out.textContent = obj ? `${msg}\n\n${JSON.stringify(obj, null, 2)}` : msg;
  }

  async function apiJson(url, options = {}) {
    const res = await fetch(url, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options
    });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; }
    catch { data = { raw: text }; }
    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}: ${data.detail ? JSON.stringify(data.detail) : data.raw || 'request failed'}`);
    }
    return data;
  }

  function pretty(obj) {
    return JSON.stringify(obj || {}, null, 2);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function renderRecord(record) {
    if (!record || !record.id) {
      status('No request record loaded.');
      return;
    }

    const summary = {
      id: record.id,
      owner: record.owner,
      classification: record.classification,
      selected_skills: record.selected_skills,
      local_only: record.local_only,
      git_sync_allowed: record.git_sync_allowed,
      approval_status: record.approval_status || null,
      run_envelope_status: record.run_envelope_status || null
    };

    const summaryBox = el('pfws-v2-summary');
    if (summaryBox) summaryBox.textContent = pretty(summary);

    const taskBox = el('pfws-v2-task-packet');
    if (taskBox) taskBox.value = pretty(record.task_packet || {});

    const guardBox = el('pfws-v2-guard-plan');
    if (guardBox) guardBox.value = pretty(record.guard_plan || {});

    const promptBox = el('pfws-v2-prompt');
    if (promptBox && record.prompt) promptBox.value = record.prompt;

    const evidence = el('pfws-v2-evidence');
    const reqs = record.evidence_requirements || [];
    if (evidence) {
      evidence.innerHTML = reqs.length
        ? `<ul>${reqs.map(x => `<li><label><input type="checkbox"> ${escapeHtml(x)}</label></li>`).join('')}</ul>`
        : 'No evidence requirements.';
    }

    window.ProjectForgeWorkspaceActiveRequestId = record.id;
    status('Loaded latest approved Workspace request.', {
      id: record.id,
      approval_status: record.approval_status,
      run_envelope_status: record.run_envelope_status || null
    });
  }

  async function loadLatestApproved() {
    status('Loading latest approved Workspace request...');
    const list = await apiJson('/api/workspace/requests');
    const items = list.items || [];

    for (const item of items) {
      if (!item || !item.id) continue;
      const record = await apiJson(`/api/workspace/requests/${encodeURIComponent(item.id)}`);
      if (record.approval_status === 'approved_for_guarded_run_preparation') {
        renderRecord(record);
        return;
      }
    }

    status('No approved Workspace request found. Build a request and click Approve Guarded Run Preparation first.');
  }

  function getActiveRequestId() {
    if (window.ProjectForgeWorkspaceActiveRequestId) return window.ProjectForgeWorkspaceActiveRequestId;

    const summary = el('pfws-v2-summary');
    if (!summary) return null;
    try {
      const data = JSON.parse(summary.textContent || '{}');
      return data.id || null;
    } catch {
      const match = (summary.textContent || '').match(/ws_[A-Za-z0-9T_]+/);
      return match ? match[0] : null;
    }
  }

  async function prepareRunEnvelope() {
    const requestId = getActiveRequestId();
    if (!requestId) {
      status('No active request selected. Click Load Latest Approved first.');
      return;
    }

    status('Preparing run envelope from approved request. No agents or preflight will run...');
    try {
      const data = await apiJson(`/api/workspace/requests/${encodeURIComponent(requestId)}/prepare_run_envelope`, {
        method: 'POST',
        body: JSON.stringify({})
      });

      status('Run envelope prepared. No execution occurred.', {
        request_id: requestId,
        run_dir: data.run_dir,
        preflight_command: data.preflight_command,
        automatic_execution: data.automatic_execution,
        message: data.message
      });
    } catch (err) {
      status(`Prepare run envelope failed: ${err.message || err}`);
    }
  }

  function installButtons() {
    const promptCard = el('pfws-v2-prompt')?.closest('.pfws-v2-card');
    if (!promptCard) return;

    let row = el('pfws-approved-actions-row');
    if (!row) {
      row = document.createElement('div');
      row.id = 'pfws-approved-actions-row';
      row.style.marginTop = '8px';
      row.style.display = 'flex';
      row.style.flexWrap = 'wrap';
      row.style.gap = '8px';
      promptCard.appendChild(row);
    }

    if (!el('pfws-load-latest-approved')) {
      const btn = document.createElement('button');
      btn.id = 'pfws-load-latest-approved';
      btn.type = 'button';
      btn.className = 'pfws-v2-btn primary';
      btn.textContent = 'Load Latest Approved';
      btn.title = 'Loads the newest approved Workspace request into the page.';
      btn.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        loadLatestApproved().catch(err => status(`Load latest approved failed: ${err.message || err}`));
      });
      row.appendChild(btn);
    }

    if (!el('pfws-prepare-run-envelope-top')) {
      const btn = document.createElement('button');
      btn.id = 'pfws-prepare-run-envelope-top';
      btn.type = 'button';
      btn.className = 'pfws-v2-btn';
      btn.textContent = 'Prepare Run Envelope';
      btn.title = 'Creates local run envelope files only. Does not execute agents or preflight.';
      btn.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        prepareRunEnvelope();
      });
      row.appendChild(btn);
    }
  }

  function install() {
    installButtons();
  }

  document.addEventListener('click', function (event) {
    const target = event.target.closest('button, a, [role="button"]');
    if (!target) return;
    const text = (target.textContent || '').trim().toLowerCase();
    const id = target.id || '';
    if (
      text === 'workspace' ||
      id === 'projectforge-workspace-planner-btn' ||
      id === 'pfws-v2-build-team' ||
      /build\s*team/i.test(text)
    ) {
      setTimeout(install, 100);
      setTimeout(install, 500);
      setTimeout(install, 1000);
    }
  }, true);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install);
  } else {
    install();
  }

  window.ProjectForgeWorkspaceLatestApproved = {
    install,
    loadLatestApproved,
    prepareRunEnvelope
  };
})();

// ProjectForge Workspace V3 Phase F deterministic lifecycle
(function () {
  const READY_EVENT = 'projectforge:workspace-v2-ready';
  const SHELL_SELECTOR = '.pfws-v2-shell';

  const state = {
    observer: null
  };

  function isWorkspaceLauncher(target) {
    const el = target && target.closest ? target.closest('button, a, [role="button"]') : null;
    if (!el) return false;
    const id = el.id || '';
    const text = (el.textContent || '').trim().toLowerCase();
    return id === 'projectforge-workspace-planner-btn' ||
      text === 'workspace' ||
      text === 'build team';
  }

  function dispatchReady(shell) {
    if (!shell || shell.dataset.pfwsLifecycleReady === '1') return shell || null;
    shell.dataset.pfwsLifecycleReady = '1';
    try {
      document.dispatchEvent(new CustomEvent(READY_EVENT, { detail: { shell } }));
    } catch (_) {}
    return shell;
  }

  function notifyReady() {
    const shell = document.querySelector(SHELL_SELECTOR);
    return dispatchReady(shell);
  }

  function observeUntilReady() {
    const ready = notifyReady();
    if (ready) return ready;

    if (state.observer || typeof MutationObserver === 'undefined') return null;

    const root = document.body || document.documentElement;
    if (!root) return null;

    state.observer = new MutationObserver(() => {
      const shell = notifyReady();
      if (shell && state.observer) {
        state.observer.disconnect();
        state.observer = null;
      }
    });

    state.observer.observe(root, { childList: true, subtree: true });
    return null;
  }

  document.addEventListener('DOMContentLoaded', observeUntilReady);

  document.addEventListener('click', (ev) => {
    if (isWorkspaceLauncher(ev.target)) observeUntilReady();
  }, true);

  window.ProjectForgeWorkspaceLifecycle = {
    READY_EVENT,
    SHELL_SELECTOR,
    observeUntilReady,
    notifyReady
  };
})();

// ProjectForge Workspace V3 Phase C run-envelope history panel
(() => {
  const PANEL_ID = 'pfws-run-envelope-panel';
  let latestEnvelope = null;

  async function apiJson(url, options = {}) {
    const res = await fetch(url, {
      credentials: 'same-origin',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });

    if (!res.ok) {
      let detail = '';
      try {
        const data = await res.json();
        detail = data.detail || JSON.stringify(data);
      } catch {
        detail = await res.text();
      }
      throw new Error(detail || `HTTP ${res.status}`);
    }

    return res.json();
  }

  function setWorkspaceStatus(message) {
    const status = document.getElementById('pfws-v2-status');
    if (status) status.textContent = message;
  }

  function getOutputEl() {
    return document.getElementById('pfws-run-envelope-output');
  }

  function setCopyButtonsEnabled(enabled) {
    ['pfws-copy-run-dir', 'pfws-copy-preflight', 'pfws-copy-post-run-guard'].forEach((id) => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = !enabled;
    });
  }

  function renderRunEnvelopes(data) {
    const out = getOutputEl();
    if (!out) return;

    const items = Array.isArray(data && data.items) ? data.items : [];
    latestEnvelope = items[0] || null;

    if (!latestEnvelope) {
      out.textContent = 'No run envelopes found yet.';
      setCopyButtonsEnabled(false);
      return;
    }

    const lines = [
      `Latest: ${latestEnvelope.id || '(missing id)'}`,
      `Request: ${latestEnvelope.request_id || '(missing request id)'}`,
      `Status: ${latestEnvelope.status || '(missing status)'}`,
      `Created: ${latestEnvelope.created_at || '(unknown)'}`,
      '',
      `automatic_execution: ${latestEnvelope.automatic_execution}`,
      `local_only: ${latestEnvelope.local_only}`,
      `git_sync_allowed: ${latestEnvelope.git_sync_allowed}`,
      '',
      'Manual Commands:',
      latestEnvelope.preflight_command || '(missing preflight command)',
      latestEnvelope.post_run_guard_command || '(missing post-run guard command)',
      '',
      `Run directory: ${latestEnvelope.run_dir || '(missing run dir)'}`,
    ];

    if (items.length > 1) {
      lines.push('', 'Recent envelopes:');
      items.slice(0, 10).forEach((item, idx) => {
        lines.push(`${idx + 1}. ${item.id || '(missing id)'} — ${item.status || 'unknown'}`);
      });
    }

    out.textContent = lines.join('\n');
    setCopyButtonsEnabled(true);
  }

  async function refreshRunEnvelopes() {
    const out = getOutputEl();
    if (out) out.textContent = 'Loading run-envelope history...';

    try {
      const data = await apiJson('/api/workspace/run_envelopes');
      renderRunEnvelopes(data);
      setWorkspaceStatus('Run-envelope history refreshed. No commands executed.');
    } catch (err) {
      if (out) out.textContent = `Run-envelope history failed: ${err && err.message ? err.message : err}`;
      setCopyButtonsEnabled(false);
    }
  }

  async function copyText(value, label) {
    if (!value) {
      setWorkspaceStatus(`Nothing to copy for ${label}.`);
      return;
    }

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const box = document.createElement('textarea');
        box.value = value;
        box.setAttribute('readonly', 'readonly');
        box.style.position = 'fixed';
        box.style.left = '-9999px';
        document.body.appendChild(box);
        box.select();
        document.execCommand('copy');
        document.body.removeChild(box);
      }

      setWorkspaceStatus(`Copied ${label}. Nothing executed.`);
    } catch (err) {
      setWorkspaceStatus(`Copy failed for ${label}: ${err && err.message ? err.message : err}`);
    }
  }

  function installRunEnvelopePanel() {
    if (document.getElementById(PANEL_ID)) return true;

    const prompt = document.getElementById('pfws-v2-prompt');
    const promptCard = prompt ? prompt.closest('.pfws-v2-card') : null;
    if (!promptCard) return false;

    const panel = document.createElement('div');
    panel.id = PANEL_ID;
    panel.className = 'pfws-v2-card';
    panel.innerHTML = `
      <div class="pfws-v2-section-title">Run Envelopes</div>
      <div class="pfws-v2-muted">
        Read-only history and copyable manual commands. The browser does not execute shell commands, agents, preflight, post-run guards, or Git operations.
      </div>
      <div class="pfws-v2-actions" style="margin-top:10px;flex-wrap:wrap;">
        <button class="pfws-v2-btn" id="pfws-refresh-run-envelopes" type="button">Refresh Run Envelopes</button>
        <button class="pfws-v2-btn" id="pfws-copy-run-dir" type="button" disabled>Copy Run Directory</button>
        <button class="pfws-v2-btn" id="pfws-copy-preflight" type="button" disabled>Copy Preflight Command</button>
        <button class="pfws-v2-btn" id="pfws-copy-post-run-guard" type="button" disabled>Copy Post-Run Guard Command</button>
      </div>
      <pre class="pfws-pre" id="pfws-run-envelope-output">Run-envelope history not loaded yet.</pre>
    `;

    promptCard.insertAdjacentElement('afterend', panel);

    panel.querySelector('#pfws-refresh-run-envelopes')?.addEventListener('click', refreshRunEnvelopes);
    panel.querySelector('#pfws-copy-run-dir')?.addEventListener('click', () => copyText(latestEnvelope && latestEnvelope.run_dir, 'run directory'));
    panel.querySelector('#pfws-copy-preflight')?.addEventListener('click', () => copyText(latestEnvelope && latestEnvelope.preflight_command, 'preflight command'));
    panel.querySelector('#pfws-copy-post-run-guard')?.addEventListener('click', () => copyText(latestEnvelope && latestEnvelope.post_run_guard_command, 'post-run guard command'));

    return true;
  }

  function installAndRefreshRunEnvelopePanel() {
    if (installRunEnvelopePanel()) {
      refreshRunEnvelopes();
    }
  }

  // Phase F: mount via Workspace lifecycle. No browser commands execute.
  function installSoonRunEnvelope() {
    const lifecycle = window.ProjectForgeWorkspaceLifecycle;
    if (lifecycle && typeof lifecycle.observeUntilReady === 'function') {
      lifecycle.observeUntilReady();
    }
    installAndRefreshRunEnvelopePanel();
  }

  document.addEventListener('DOMContentLoaded', installSoonRunEnvelope);
  document.addEventListener('projectforge:workspace-v2-ready', () => {
    installSoonRunEnvelope();
    refreshRunEnvelopes();
  });

  document.addEventListener('click', (event) => {
    const target = event.target && event.target.closest ? event.target.closest('button, [role="button"], a') : null;
    if (!target) return;

    const id = target.id || '';
    const text = (target.textContent || '').trim().toLowerCase();

    const opensWorkspace =
      id === 'projectforge-workspace-planner-btn' ||
      text === 'workspace' ||
      text === 'build team' ||
      text === 'review & build team';

    if (opensWorkspace) {
      installSoonRunEnvelope();
    }

    if (id === 'pfws-static-prepare-run') {
    }
  }, true);

  window.ProjectForgeWorkspaceRunEnvelopePanel = {
    install: installRunEnvelopePanel,
    refresh: refreshRunEnvelopes
  };
})();
// ProjectForge Workspace V3 Phase D manual execution checklist + metadata only
(() => {
  let latestEnvelope = null;

  async function apiJson(url, options = {}) {
    const res = await fetch(url, {
      credentials: 'same-origin',
      cache: 'no-store',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });

    if (!res.ok) {
      let detail = '';
      try {
        const data = await res.json();
        detail = data.detail || JSON.stringify(data);
      } catch {
        detail = await res.text();
      }
      throw new Error(detail || `HTTP ${res.status}`);
    }

    return res.json();
  }

  function status(message) {
    const el = document.getElementById('pfws-v2-status');
    if (el) el.textContent = message;
  }

  async function copyText(value, label) {
    if (!value) {
      status(`Nothing to copy for ${label}.`);
      return;
    }

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const box = document.createElement('textarea');
        box.value = value;
        box.setAttribute('readonly', 'readonly');
        box.style.position = 'fixed';
        box.style.left = '-9999px';
        document.body.appendChild(box);
        box.select();
        document.execCommand('copy');
        document.body.removeChild(box);
      }
      status(`Copied ${label}. Nothing executed.`);
    } catch (err) {
      status(`Copy failed for ${label}: ${err && err.message ? err.message : err}`);
    }
  }

  function findRunEnvelopePanel() {
    return document.getElementById('pfws-run-envelope-panel') ||
      document.getElementById('pfws-phase-c-output')?.closest('.pfws-v2-card');
  }

  function ensurePanel() {
    let panel = document.getElementById('pfws-phase-d-manual-panel');
    if (panel) return panel;

    const anchor = findRunEnvelopePanel();
    if (!anchor) return null;

    panel = document.createElement('div');
    panel.id = 'pfws-phase-d-manual-panel';
    panel.className = 'pfws-v2-card';
    panel.style.marginTop = '12px';
    panel.innerHTML = `
      <div class="pfws-v2-section-title">Manual Execution Checklist</div>
      <div class="pfws-v2-muted">
        Metadata and copy-only controls. This panel does not execute shell commands, agents, preflight, post-run guard, implementation commands, or Git operations.
      </div>
      <div class="pfws-v2-actions" style="margin-top:10px;flex-wrap:wrap;">
        <button class="pfws-v2-btn" id="pfws-phase-d-refresh" type="button">Refresh Checklist</button>
        <button class="pfws-v2-btn" id="pfws-phase-d-copy-checklist" type="button" disabled>Copy Checklist</button>
        <button class="pfws-v2-btn" id="pfws-phase-d-copy-block" type="button" disabled>Copy Manual Command Block</button>
        <button class="pfws-v2-btn" id="pfws-phase-d-status-not-started" type="button" disabled>Mark Not Started</button>
        <button class="pfws-v2-btn" id="pfws-phase-d-status-started" type="button" disabled>Mark Started</button>
        <button class="pfws-v2-btn" id="pfws-phase-d-status-completed" type="button" disabled>Mark Completed</button>
      </div>
      <pre class="pfws-pre" id="pfws-phase-d-output">Manual execution checklist not loaded yet.</pre>
    `;

    anchor.insertAdjacentElement('afterend', panel);

    panel.querySelector('#pfws-phase-d-refresh')?.addEventListener('click', refresh);
    panel.querySelector('#pfws-phase-d-copy-checklist')?.addEventListener('click', () => {
      const checklist = Array.isArray(latestEnvelope?.manual_execution_checklist) ? latestEnvelope.manual_execution_checklist : [];
      copyText(checklist.map((x, i) => `${i + 1}. ${x}`).join('\n'), 'manual execution checklist');
    });
    panel.querySelector('#pfws-phase-d-copy-block')?.addEventListener('click', () => {
      copyText(latestEnvelope && latestEnvelope.manual_command_block, 'manual command block');
    });
    panel.querySelector('#pfws-phase-d-status-not-started')?.addEventListener('click', () => setManualStatus('manual_run_not_started'));
    panel.querySelector('#pfws-phase-d-status-started')?.addEventListener('click', () => setManualStatus('manual_run_started'));
    panel.querySelector('#pfws-phase-d-status-completed')?.addEventListener('click', () => setManualStatus('manual_run_completed'));

    return panel;
  }

  function outputEl() {
    ensurePanel();
    return document.getElementById('pfws-phase-d-output');
  }

  function setEnabled(enabled) {
    [
      'pfws-phase-d-copy-checklist',
      'pfws-phase-d-copy-block',
      'pfws-phase-d-status-not-started',
      'pfws-phase-d-status-started',
      'pfws-phase-d-status-completed'
    ].forEach((id) => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = !enabled;
    });
  }

  function render() {
    const out = outputEl();
    if (!out) return;

    if (!latestEnvelope) {
      out.textContent = 'No run envelope loaded yet.';
      setEnabled(false);
      return;
    }

    const checklist = Array.isArray(latestEnvelope.manual_execution_checklist)
      ? latestEnvelope.manual_execution_checklist
      : [];

    out.textContent = [
      `Run: ${latestEnvelope.id || '(missing id)'}`,
      `Manual status: ${latestEnvelope.manual_status || 'manual_run_not_started'}`,
      `Browser executes commands: ${latestEnvelope.browser_executes_commands === true ? 'true' : 'false'}`,
      '',
      'Checklist:',
      ...checklist.map((item, index) => `${index + 1}. ${item}`),
      '',
      'Manual command block preview:',
      latestEnvelope.manual_command_block || '(missing manual command block)'
    ].join('\n');

    setEnabled(true);
  }

  async function refresh() {
    ensurePanel();

    const out = outputEl();
    if (out) out.textContent = 'Loading manual execution checklist...';

    try {
      const data = await apiJson('/api/workspace/run_envelopes');
      const items = Array.isArray(data && data.items) ? data.items : [];
      latestEnvelope = items[0] || null;
      render();
      status('Manual execution checklist refreshed. No commands executed.');
    } catch (err) {
      if (out) out.textContent = `Manual checklist refresh failed: ${err && err.message ? err.message : err}`;
      setEnabled(false);
      status('Manual checklist refresh failed.');
    }
  }

  async function setManualStatus(manualStatus) {
    if (!latestEnvelope || !latestEnvelope.id) {
      status('No run envelope loaded.');
      return;
    }

    try {
      const data = await apiJson(`/api/workspace/run_envelopes/${encodeURIComponent(latestEnvelope.id)}/manual_status`, {
        method: 'PUT',
        body: JSON.stringify({
          manual_status: manualStatus,
          note: 'Updated from Workspace Phase D metadata-only UI.'
        })
      });

      latestEnvelope.manual_status = data.manual_status;
      render();
      status(`Manual status set to ${data.manual_status}. No commands executed.`);
    } catch (err) {
      status(`Manual status update failed: ${err && err.message ? err.message : err}`);
    }
  }

  function install() {
    const ok = !!ensurePanel();
    if (ok) refresh();
    return ok;
  }

  function installSoon() {
    const lifecycle = window.ProjectForgeWorkspaceLifecycle;
    if (lifecycle && typeof lifecycle.observeUntilReady === 'function') {
      lifecycle.observeUntilReady();
    }
    install();
  }

  document.addEventListener('DOMContentLoaded', installSoon);
  document.addEventListener('projectforge:workspace-v2-ready', installSoon);

  document.addEventListener('click', (event) => {
    const target = event.target && event.target.closest ? event.target.closest('button, [role="button"], a') : null;
    if (!target) return;

    const id = target.id || '';
    const text = (target.textContent || '').trim().toLowerCase();

    if (
      id === 'projectforge-workspace-planner-btn' ||
      text === 'workspace' ||
      text === 'build team' ||
      text === 'review & build team' ||
      id === 'pfws-phase-c-refresh'
    ) {
      installSoon();
    }
  }, true);

  window.ProjectForgeWorkspacePhaseDManualExecution = {
    install,
    refresh
  };
})();

// ProjectForge Workspace V3 Phase F Part 3 read-only run history console
(() => {
  const CONSOLE_ID = 'pfws-run-history-console';
  const LIST_ID = 'pfws-run-history-list';
  const DETAIL_ID = 'pfws-run-history-detail';
  const STATUS_ID = 'pfws-run-history-status';

  let selectedEnvelope = null;
  let selectedEnvelopeJson = '';

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[c]));
  }

  async function apiJson(url, options = {}) {
    const res = await fetch(url, {
      credentials: 'same-origin',
      cache: 'no-store',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });

    const text = await res.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { raw: text };
    }

    if (!res.ok) {
      throw new Error(data.detail || data.raw || `HTTP ${res.status}`);
    }

    return data;
  }

  function status(message) {
    const el = document.getElementById(STATUS_ID) || document.getElementById('pfws-v2-status');
    if (el) el.textContent = message;
  }

  async function copyText(value, label) {
    if (!value) {
      status(`Nothing to copy for ${label}.`);
      return;
    }

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const box = document.createElement('textarea');
        box.value = value;
        box.setAttribute('readonly', 'readonly');
        box.style.position = 'fixed';
        box.style.left = '-9999px';
        document.body.appendChild(box);
        box.select();
        document.execCommand('copy');
        document.body.removeChild(box);
      }

      status(`Copied ${label}. Nothing executed.`);
    } catch (err) {
      status(`Copy failed for ${label}: ${err && err.message ? err.message : err}`);
    }
  }

  function summarizeEnvelope(item) {
    const parts = [
      item.id || '(missing id)',
      item.status || item.run_status || 'unknown',
      item.manual_status || 'manual status unknown'
    ];

    if (item.request_id) parts.push(`request ${item.request_id}`);
    return parts.join(' · ');
  }

  function collectArtifactHints(env) {
    const hints = [];

    [
      'run_dir',
      'report_dir',
      'workspace_dir',
      'trajectory_path',
      'final_diff_path',
      'result_path',
      'summary_path',
      'artifact_path',
      'archive_dir',
      'request_path',
      'envelope_path'
    ].forEach((key) => {
      if (env && env[key]) hints.push(`${key}: ${env[key]}`);
    });

    if (Array.isArray(env && env.artifacts)) {
      env.artifacts.forEach((item, idx) => {
        if (typeof item === 'string') {
          hints.push(`artifacts[${idx}]: ${item}`);
        } else if (item && typeof item === 'object') {
          hints.push(`artifacts[${idx}]: ${item.path || item.url || JSON.stringify(item)}`);
        }
      });
    }

    if (env && env.summary && typeof env.summary === 'object') {
      ['run_dir', 'workspace', 'trajectory_path', 'final_diff_path', 'result_path', 'archive_dir'].forEach((key) => {
        if (env.summary[key]) hints.push(`summary.${key}: ${env.summary[key]}`);
      });
    }

    return Array.from(new Set(hints.filter(Boolean)));
  }

  function formatEnvelopeDetail(env) {
    const checklist = Array.isArray(env.manual_execution_checklist)
      ? env.manual_execution_checklist
      : [];

    const artifactHints = collectArtifactHints(env);

    const lines = [
      `Run ID: ${env.id || '(missing)'}`,
      `Request ID: ${env.request_id || '(missing)'}`,
      `Status: ${env.status || env.run_status || '(missing)'}`,
      `Manual status: ${env.manual_status || 'manual_run_not_started'}`,
      `Created: ${env.created_at || '(unknown)'}`,
      '',
      'Safety:',
      `automatic_execution: ${env.automatic_execution === true ? 'true' : 'false'}`,
      `local_only: ${env.local_only === false ? 'false' : 'true'}`,
      `git_sync_allowed: ${env.git_sync_allowed === true ? 'true' : 'false'}`,
      `browser_executes_commands: ${env.browser_executes_commands === true ? 'true' : 'false'}`,
      '',
      'Paths:',
      `run_dir: ${env.run_dir || '(missing)'}`,
      '',
      'Manual commands:',
      `preflight_command: ${env.preflight_command || '(missing)'}`,
      `post_run_guard_command: ${env.post_run_guard_command || '(missing)'}`,
      '',
      'Manual execution checklist:',
      ...(checklist.length ? checklist.map((item, index) => `${index + 1}. ${item}`) : ['(missing or empty)']),
      '',
      'Manual command block:',
      env.manual_command_block || '(missing)',
      '',
      'Artifact/path hints:',
      ...(artifactHints.length ? artifactHints : ['(no additional artifact paths found in metadata)'])
    ];

    return lines.join('\n');
  }

  function renderList(items) {
    const list = document.getElementById(LIST_ID);
    if (!list) return;

    if (!items.length) {
      list.innerHTML = '<div class="pfws-v2-muted">No run envelopes found yet.</div>';
      return;
    }

    list.innerHTML = items.slice(0, 20).map((item, idx) => {
      const id = item && item.id ? String(item.id) : '';
      const label = summarizeEnvelope(item || {});
      const created = item && item.created_at ? String(item.created_at) : '';
      return `
        <button class="pfws-v2-history-item" type="button" data-pfws-run-id="${escapeHtml(id)}" data-pfws-run-index="${idx}">
          <div><strong>${escapeHtml(label)}</strong></div>
          <div class="pfws-v2-muted">${escapeHtml(created)}</div>
        </button>
      `;
    }).join('');
  }

  function renderDetail(env) {
    const detail = document.getElementById(DETAIL_ID);
    if (!detail) return;

    selectedEnvelope = env || null;
    selectedEnvelopeJson = selectedEnvelope ? JSON.stringify(selectedEnvelope, null, 2) : '';

    if (!selectedEnvelope) {
      detail.textContent = 'No run selected.';
      setCopyButtonsEnabled(false);
      return;
    }

    detail.textContent = formatEnvelopeDetail(selectedEnvelope);
    setCopyButtonsEnabled(true);
  }

  function setCopyButtonsEnabled(enabled) {
    [
      'pfws-run-history-copy-id',
      'pfws-run-history-copy-dir',
      'pfws-run-history-copy-json',
      'pfws-run-history-copy-command-block'
    ].forEach((id) => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = !enabled;
    });
  }

  async function selectEnvelope(runId, fallback) {
    if (!runId) {
      renderDetail(fallback || null);
      return;
    }

    status(`Loading run detail for ${runId}...`);

    try {
      const detail = await apiJson(`/api/workspace/run_envelopes/${encodeURIComponent(runId)}/manual_status`);
      renderDetail({ ...(fallback || {}), ...(detail || {}) });
      status(`Loaded run detail for ${runId}. No commands executed.`);
    } catch (err) {
      renderDetail(fallback || { id: runId });
      status(`Loaded list metadata for ${runId}; detail fetch failed: ${err && err.message ? err.message : err}`);
    }
  }

  async function refreshConsole() {
    const panel = installConsole();
    if (!panel) return false;

    const list = document.getElementById(LIST_ID);
    if (list) list.innerHTML = '<div class="pfws-v2-muted">Loading run history...</div>';

    try {
      const data = await apiJson('/api/workspace/run_envelopes');
      const items = Array.isArray(data && data.items) ? data.items : [];

      renderList(items);

      const listEl = document.getElementById(LIST_ID);
      if (listEl) {
        listEl.querySelectorAll('[data-pfws-run-id]').forEach((btn) => {
          btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-pfws-run-id') || '';
            const idx = Number(btn.getAttribute('data-pfws-run-index') || '0');
            selectEnvelope(id, items[idx] || null);
          });
        });
      }

      if (items[0]) {
        await selectEnvelope(items[0].id, items[0]);
      } else {
        renderDetail(null);
      }

      status(`Run history console refreshed (${items.length} envelope${items.length === 1 ? '' : 's'}). No commands executed.`);
      return true;
    } catch (err) {
      if (list) list.innerHTML = `<div class="pfws-v2-muted">Run history failed: ${escapeHtml(err && err.message ? err.message : err)}</div>`;
      renderDetail(null);
      status('Run history console refresh failed.');
      return false;
    }
  }

  function installConsole() {
    const runPanel = document.getElementById('pfws-run-envelope-panel');
    if (!runPanel) return null;

    let consoleEl = document.getElementById(CONSOLE_ID);
    if (consoleEl) return consoleEl;

    consoleEl = document.createElement('div');
    consoleEl.id = CONSOLE_ID;
    consoleEl.className = 'pfws-v2-card';
    consoleEl.style.marginTop = '12px';
    consoleEl.innerHTML = `
      <div class="pfws-v2-section-title">Run History Console</div>
      <div class="pfws-v2-muted">
        Read-only local run metadata. Select a run to inspect request linkage, manual status, guarded commands, and artifact path hints. Copy buttons only copy text; nothing executes.
      </div>
      <div class="pfws-v2-actions" style="margin-top:10px;flex-wrap:wrap;">
        <button class="pfws-v2-btn" id="pfws-run-history-refresh" type="button">Refresh Run History</button>
        <button class="pfws-v2-btn" id="pfws-run-history-copy-id" type="button" disabled>Copy Run ID</button>
        <button class="pfws-v2-btn" id="pfws-run-history-copy-dir" type="button" disabled>Copy Run Directory</button>
        <button class="pfws-v2-btn" id="pfws-run-history-copy-json" type="button" disabled>Copy Run JSON</button>
        <button class="pfws-v2-btn" id="pfws-run-history-copy-command-block" type="button" disabled>Copy Manual Command Block</button>
      </div>
      <div class="pfws-v2-grid" style="margin-top:10px;">
        <div class="pfws-v2-card" style="margin:0;">
          <div class="pfws-v2-section-title">Recent Runs</div>
          <div id="${LIST_ID}" class="pfws-v2-muted">Run history not loaded yet.</div>
        </div>
        <div class="pfws-v2-card" style="margin:0;">
          <div class="pfws-v2-section-title">Selected Run Detail</div>
          <pre class="pfws-pre" id="${DETAIL_ID}">No run selected.</pre>
        </div>
      </div>
      <pre class="pfws-pre" id="${STATUS_ID}" style="margin-top:10px;">Run history console ready. No commands executed.</pre>
    `;

    runPanel.insertAdjacentElement('afterend', consoleEl);

    consoleEl.querySelector('#pfws-run-history-refresh')?.addEventListener('click', refreshConsole);
    consoleEl.querySelector('#pfws-run-history-copy-id')?.addEventListener('click', () => copyText(selectedEnvelope && selectedEnvelope.id, 'run ID'));
    consoleEl.querySelector('#pfws-run-history-copy-dir')?.addEventListener('click', () => copyText(selectedEnvelope && selectedEnvelope.run_dir, 'run directory'));
    consoleEl.querySelector('#pfws-run-history-copy-json')?.addEventListener('click', () => copyText(selectedEnvelopeJson, 'run JSON'));
    consoleEl.querySelector('#pfws-run-history-copy-command-block')?.addEventListener('click', () => copyText(selectedEnvelope && selectedEnvelope.manual_command_block, 'manual command block'));

    return consoleEl;
  }

  function installSoon() {
    const lifecycle = window.ProjectForgeWorkspaceLifecycle;
    if (lifecycle && typeof lifecycle.observeUntilReady === 'function') {
      lifecycle.observeUntilReady();
    }

    if (installConsole()) {
      refreshConsole();
    }
  }

  document.addEventListener('DOMContentLoaded', installSoon);
  document.addEventListener('projectforge:workspace-v2-ready', installSoon);

  document.addEventListener('click', (event) => {
    const target = event.target && event.target.closest ? event.target.closest('button, [role="button"], a') : null;
    if (!target) return;

    const id = target.id || '';
    const text = (target.textContent || '').trim().toLowerCase();

    if (
      id === 'projectforge-workspace-planner-btn' ||
      text === 'workspace' ||
      text === 'build team' ||
      text === 'review & build team' ||
      id === 'pfws-refresh-run-envelopes' ||
      id === 'pfws-phase-d-refresh'
    ) {
      installSoon();
    }
  }, true);

  window.ProjectForgeWorkspaceRunHistoryConsole = {
    install: installConsole,
    refresh: refreshConsole,
    select: selectEnvelope
  };
})();

// ProjectForge Workspace V3 Phase F Part 4 read-only artifact/result ingestion
(() => {
  const PANEL_ID = 'pfws-artifact-ingestion-panel';
  const LIST_ID = 'pfws-artifact-ingestion-list';
  const DETAIL_ID = 'pfws-artifact-ingestion-detail';
  const STATUS_ID = 'pfws-artifact-ingestion-status';

  let latestPayload = null;
  let selectedArtifact = null;

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[c]));
  }

  async function apiJson(url, options = {}) {
    const res = await fetch(url, {
      credentials: 'same-origin',
      cache: 'no-store',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });

    const text = await res.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { raw: text };
    }

    if (!res.ok) {
      throw new Error(data.detail || data.raw || `HTTP ${res.status}`);
    }

    return data;
  }

  function status(message) {
    const el = document.getElementById(STATUS_ID) || document.getElementById('pfws-v2-status');
    if (el) el.textContent = message;
  }

  async function copyText(value, label) {
    if (!value) {
      status(`Nothing to copy for ${label}.`);
      return;
    }

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const box = document.createElement('textarea');
        box.value = value;
        box.setAttribute('readonly', 'readonly');
        box.style.position = 'fixed';
        box.style.left = '-9999px';
        document.body.appendChild(box);
        box.select();
        document.execCommand('copy');
        document.body.removeChild(box);
      }
      status(`Copied ${label}. Nothing executed.`);
    } catch (err) {
      status(`Copy failed for ${label}: ${err && err.message ? err.message : err}`);
    }
  }

  function getSelectedRunId() {
    const detail = document.getElementById('pfws-run-history-detail');
    const detailText = detail ? detail.textContent || '' : '';
    let match = detailText.match(/Run ID:\s*([A-Za-z0-9_.:-]+)/);
    if (match) return match[1];

    const out = document.getElementById('pfws-run-envelope-output');
    const outText = out ? out.textContent || '' : '';
    match = outText.match(/Latest:\s*([A-Za-z0-9_.:-]+)/);
    if (match) return match[1];

    return null;
  }

  function renderArtifactList(items) {
    const list = document.getElementById(LIST_ID);
    if (!list) return;

    if (!items.length) {
      list.innerHTML = '<div class="pfws-v2-muted">No artifact/result files found for this run.</div>';
      return;
    }

    list.innerHTML = items.map((item, idx) => `
      <button class="pfws-v2-history-item" type="button" data-pfws-artifact-index="${idx}">
        <div><strong>${escapeHtml(item.kind || 'artifact')}</strong> · ${escapeHtml(item.path || item.name || '')}</div>
        <div class="pfws-v2-muted">${escapeHtml(String(item.size_bytes || 0))} bytes · copy-only · read-only</div>
      </button>
    `).join('');

    list.querySelectorAll('[data-pfws-artifact-index]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.getAttribute('data-pfws-artifact-index') || '0');
        renderArtifactDetail(items[idx] || null);
      });
    });
  }

  function renderArtifactDetail(item) {
    const detail = document.getElementById(DETAIL_ID);
    if (!detail) return;

    selectedArtifact = item || null;

    if (!selectedArtifact) {
      detail.textContent = 'No artifact selected.';
      setCopyButtonsEnabled(false);
      return;
    }

    const preview = selectedArtifact.preview == null
      ? '(no text preview available; file may be binary, too large, or unsupported)'
      : selectedArtifact.preview;

    detail.textContent = [
      `Path: ${selectedArtifact.path || '(missing)'}`,
      `Kind: ${selectedArtifact.kind || 'artifact'}`,
      `Size: ${selectedArtifact.size_bytes || 0} bytes`,
      `Preview truncated: ${selectedArtifact.preview_truncated ? 'true' : 'false'}`,
      `Copy-only: ${selectedArtifact.copy_only === false ? 'false' : 'true'}`,
      '',
      'Preview:',
      preview
    ].join('\n');

    setCopyButtonsEnabled(true);
  }

  function setCopyButtonsEnabled(enabled) {
    [
      'pfws-artifact-copy-path',
      'pfws-artifact-copy-preview',
      'pfws-artifact-copy-json',
      'pfws-artifact-copy-run-dir'
    ].forEach((id) => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = !enabled && id !== 'pfws-artifact-copy-run-dir';
    });
  }

  async function refreshArtifacts() {
    const panel = installPanel();
    if (!panel) return false;

    const runId = getSelectedRunId();
    if (!runId) {
      status('No selected run found. Refresh Run History first.');
      return false;
    }

    const list = document.getElementById(LIST_ID);
    if (list) list.innerHTML = '<div class="pfws-v2-muted">Loading artifact/result inventory...</div>';

    try {
      const data = await apiJson(`/api/workspace/run_envelopes/${encodeURIComponent(runId)}/artifacts`);
      latestPayload = data;
      const items = Array.isArray(data.items) ? data.items : [];

      renderArtifactList(items);
      renderArtifactDetail(items[0] || null);

      status(`Artifact/result inventory refreshed for ${runId}: ${items.length} item(s). No commands executed.`);
      return true;
    } catch (err) {
      if (list) list.innerHTML = `<div class="pfws-v2-muted">Artifact inventory failed: ${escapeHtml(err && err.message ? err.message : err)}</div>`;
      renderArtifactDetail(null);
      status('Artifact/result inventory refresh failed.');
      return false;
    }
  }

  function installPanel() {
    const anchor =
      document.getElementById('pfws-run-history-console') ||
      document.getElementById('pfws-phase-d-manual-panel') ||
      document.getElementById('pfws-run-envelope-panel');

    if (!anchor) return null;

    let panel = document.getElementById(PANEL_ID);
    if (panel) return panel;

    panel = document.createElement('div');
    panel.id = PANEL_ID;
    panel.className = 'pfws-v2-card';
    panel.style.marginTop = '12px';
    panel.innerHTML = `
      <div class="pfws-v2-section-title">Artifact / Result Ingestion</div>
      <div class="pfws-v2-muted">
        Read-only inventory of local files inside the selected run envelope. This panel previews text metadata and copies paths/text only. It never executes scripts, agents, preflight, post-run guards, or Git operations.
      </div>
      <div class="pfws-v2-actions" style="margin-top:10px;flex-wrap:wrap;">
        <button class="pfws-v2-btn" id="pfws-artifact-refresh" type="button">Refresh Artifacts</button>
        <button class="pfws-v2-btn" id="pfws-artifact-copy-path" type="button" disabled>Copy Artifact Path</button>
        <button class="pfws-v2-btn" id="pfws-artifact-copy-preview" type="button" disabled>Copy Preview</button>
        <button class="pfws-v2-btn" id="pfws-artifact-copy-json" type="button" disabled>Copy Artifact JSON</button>
        <button class="pfws-v2-btn" id="pfws-artifact-copy-run-dir" type="button">Copy Run Directory</button>
      </div>
      <div class="pfws-v2-grid" style="margin-top:10px;">
        <div class="pfws-v2-card" style="margin:0;">
          <div class="pfws-v2-section-title">Artifact Inventory</div>
          <div id="${LIST_ID}" class="pfws-v2-muted">Artifact inventory not loaded yet.</div>
        </div>
        <div class="pfws-v2-card" style="margin:0;">
          <div class="pfws-v2-section-title">Selected Artifact Preview</div>
          <pre class="pfws-pre" id="${DETAIL_ID}">No artifact selected.</pre>
        </div>
      </div>
      <pre class="pfws-pre" id="${STATUS_ID}" style="margin-top:10px;">Artifact ingestion ready. No commands executed.</pre>
    `;

    anchor.insertAdjacentElement('afterend', panel);

    panel.querySelector('#pfws-artifact-refresh')?.addEventListener('click', refreshArtifacts);
    panel.querySelector('#pfws-artifact-copy-path')?.addEventListener('click', () => copyText(selectedArtifact && selectedArtifact.path, 'artifact path'));
    panel.querySelector('#pfws-artifact-copy-preview')?.addEventListener('click', () => copyText(selectedArtifact && selectedArtifact.preview, 'artifact preview'));
    panel.querySelector('#pfws-artifact-copy-json')?.addEventListener('click', () => copyText(selectedArtifact ? JSON.stringify(selectedArtifact, null, 2) : '', 'artifact JSON'));
    panel.querySelector('#pfws-artifact-copy-run-dir')?.addEventListener('click', () => copyText(latestPayload && latestPayload.run_dir, 'run directory'));

    return panel;
  }

  function installSoon() {
    const lifecycle = window.ProjectForgeWorkspaceLifecycle;
    if (lifecycle && typeof lifecycle.observeUntilReady === 'function') {
      lifecycle.observeUntilReady();
    }

    if (installPanel()) {
      refreshArtifacts();
    }
  }

  document.addEventListener('DOMContentLoaded', installSoon);
  document.addEventListener('projectforge:workspace-v2-ready', installSoon);

  document.addEventListener('click', (event) => {
    const target = event.target && event.target.closest ? event.target.closest('button, [role="button"], a') : null;
    if (!target) return;

    const id = target.id || '';
    const text = (target.textContent || '').trim().toLowerCase();

    if (
      id === 'projectforge-workspace-planner-btn' ||
      text === 'workspace' ||
      text === 'build team' ||
      text === 'review & build team' ||
      id === 'pfws-run-history-refresh' ||
      id === 'pfws-refresh-run-envelopes'
    ) {
      installSoon();
    }
  }, true);

  window.ProjectForgeWorkspaceArtifactIngestion = {
    install: installPanel,
    refresh: refreshArtifacts
  };
})();


// Sandbox Build — generate + build + test a change in an isolated per-session
// dev-mirror, then hand off to patch review. Self-contained IIFE.
(function () {
  const MODAL_ID = 'pfsb-modal';
  const BTN_ID = 'pfsb-open-btn';
  const POLL_MS = 2000;
  let pollTimer = null;

  function ensureStyles() {
    if (document.getElementById('pfsb-style')) return;
    const style = document.createElement('style');
    style.id = 'pfsb-style';
    style.textContent = `
      #${MODAL_ID} { position: fixed; inset: 0; z-index: 10000; display: none;
        align-items: center; justify-content: center; background: rgba(0,0,0,.45); }
      #${MODAL_ID}.open { display: flex; }
      .pfsb-panel { width: min(860px, 94vw); max-height: 90vh; overflow: auto;
        background: var(--surface, #111827); color: var(--text, #f9fafb);
        border: 1px solid rgba(255,255,255,.14); border-radius: 16px;
        box-shadow: 0 24px 80px rgba(0,0,0,.45); }
      .pfsb-head, .pfsb-foot { padding: 14px 18px; display: flex; align-items: center;
        justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,.12); }
      .pfsb-foot { border-top: 1px solid rgba(255,255,255,.12); border-bottom: 0; }
      .pfsb-body { padding: 18px; display: grid; gap: 14px; }
      .pfsb-ta { width: 100%; min-height: 130px; resize: vertical; box-sizing: border-box;
        border-radius: 12px; border: 1px solid rgba(255,255,255,.16);
        background: rgba(255,255,255,.06); color: inherit; padding: 12px; font: inherit; }
      .pfsb-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
      .pfsb-btn { border: 1px solid rgba(255,255,255,.18); border-radius: 10px;
        padding: 9px 12px; background: rgba(255,255,255,.08); color: inherit; cursor: pointer; }
      .pfsb-btn.primary { background: #2563eb; border-color: #2563eb; color: #fff; }
      .pfsb-btn:disabled { opacity: .5; cursor: default; }
      .pfsb-status { font-size: 13px; opacity: .9; min-height: 20px; }
      .pfsb-runs { display: grid; gap: 6px; font-size: 12px; }
      .pfsb-run { display: flex; gap: 10px; align-items: center; justify-content: space-between;
        padding: 8px 10px; border: 1px solid rgba(255,255,255,.12); border-radius: 10px; }
      .pfsb-pill { font-size: 11px; padding: 2px 8px; border-radius: 999px;
        border: 1px solid rgba(255,255,255,.2); }
      .pfsb-pill.done { background: rgba(34,197,94,.18); border-color: rgba(34,197,94,.5); }
      .pfsb-pill.error { background: rgba(239,68,68,.18); border-color: rgba(239,68,68,.5); }
      .pfsb-link { color: #60a5fa; cursor: pointer; text-decoration: underline; }
      #${BTN_ID} { width: calc(100% - 16px); margin: 8px; justify-content: flex-start; }
    `;
    document.head.appendChild(style);
  }

  const RUNNING = new Set(['queued', 'mirroring', 'coding', 'checking', 'packaging']);

  function describe(st) {
    const s = (st && st.state) || 'unknown';
    if (s === 'done') {
      const ck = st.checks_status || '';
      const changed = (st.changed_file_count != null) ? st.changed_file_count : '?';
      const green = /PASS/.test(ck);
      return `Done · ${changed} file(s) changed · checks ${green ? 'PASS' : (ck || 'n/a')}`;
    }
    if (s === 'error') return `Error: ${st.error_status || st.coding_error || 'failed'}`;
    const r = (st.rounds != null) ? ` · round ${st.rounds}` : '';
    return `${s}…${r}`;
  }

  function reviewLink(st) {
    if (st && st.review_url && st.patch_file && st.changed_file_count) {
      const a = document.createElement('a');
      a.className = 'pfsb-link';
      a.textContent = 'Open patch review →';
      a.href = st.review_url;
      a.target = '_blank';
      a.rel = 'noopener';
      return a;
    }
    return null;
  }

  function ensureModal() {
    ensureStyles();
    let modal = document.getElementById(MODAL_ID);
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = MODAL_ID;
    modal.innerHTML = `
      <div class="pfsb-panel" role="dialog" aria-modal="true" aria-label="Sandbox Build">
        <div class="pfsb-head">
          <strong>Sandbox Build</strong>
          <button class="pfsb-btn" data-pfsb-close>Close</button>
        </div>
        <div class="pfsb-body">
          <div style="font-size:13px;opacity:.78;">
            Describe a code change. It is generated, built and tested in an isolated
            per-session dev-mirror — nothing touches the live repo until you review and
            approve the resulting patch.
          </div>
          <textarea class="pfsb-ta" id="pfsb-prompt" placeholder="Example: add a retry decorator to src/http_client.py and a unit test for it"></textarea>
          <div class="pfsb-actions">
            <button class="pfsb-btn primary" id="pfsb-build-btn">Build in Sandbox</button>
            <button class="pfsb-btn" id="pfsb-refresh-btn">Refresh runs</button>
          </div>
          <div class="pfsb-status" id="pfsb-status">Idle.</div>
          <div id="pfsb-review"></div>
          <div style="font-size:12px;opacity:.7;margin-top:4px;">Recent runs</div>
          <div class="pfsb-runs" id="pfsb-runs"></div>
        </div>
        <div class="pfsb-foot">
          <span style="font-size:12px;opacity:.72;">Local-only · sandboxed · review-gated · no push</span>
        </div>
      </div>`;
    document.body.appendChild(modal);
    modal.querySelector('[data-pfsb-close]')?.addEventListener('click', () => {
      modal.classList.remove('open');
      if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    });
    modal.querySelector('#pfsb-build-btn')?.addEventListener('click', startBuild);
    modal.querySelector('#pfsb-refresh-btn')?.addEventListener('click', loadRuns);
    return modal;
  }

  function $(id) { return document.getElementById(id); }

  async function startBuild() {
    const modal = ensureModal();
    const prompt = ($('pfsb-prompt')?.value || '').trim();
    const statusEl = $('pfsb-status');
    const reviewEl = $('pfsb-review');
    reviewEl.innerHTML = '';
    if (!prompt) { statusEl.textContent = 'Enter a prompt first.'; return; }
    const btn = $('pfsb-build-btn');
    btn.disabled = true;
    statusEl.textContent = 'Starting sandbox build…';
    let sessionId = null;
    try { sessionId = (window.sessionModule && window.sessionModule.getCurrentSessionId)
      ? window.sessionModule.getCurrentSessionId() : null; } catch (_) {}
    try {
      const res = await fetch('/api/workspace/sandbox/build', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, session_id: sessionId || undefined })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.tracking_id) {
        statusEl.textContent = `Could not start: ${data.detail || res.status}`;
        btn.disabled = false; return;
      }
      statusEl.textContent = 'Queued…';
      pollRun(data.tracking_id);
    } catch (err) {
      statusEl.textContent = `Build request failed: ${err && err.message ? err.message : err}`;
      btn.disabled = false;
    }
  }

  async function pollRun(trackingId) {
    const statusEl = $('pfsb-status');
    const reviewEl = $('pfsb-review');
    try {
      const res = await fetch(`/api/workspace/sandbox/runs/${encodeURIComponent(trackingId)}`,
        { credentials: 'same-origin' });
      const st = await res.json().catch(() => ({}));
      if (res.ok) {
        statusEl.textContent = describe(st);
        if (st.state === 'done' || st.state === 'error') {
          $('pfsb-build-btn').disabled = false;
          reviewEl.innerHTML = '';
          const link = reviewLink(st);
          if (link) reviewEl.appendChild(link);
          loadRuns();
          return;
        }
      }
    } catch (_) { /* transient; keep polling */ }
    pollTimer = setTimeout(() => pollRun(trackingId), POLL_MS);
  }

  async function loadRuns() {
    const wrap = $('pfsb-runs');
    if (!wrap) return;
    try {
      const res = await fetch('/api/workspace/sandbox/runs', { credentials: 'same-origin' });
      const data = await res.json().catch(() => ({}));
      const items = (data && data.items) || [];
      wrap.innerHTML = '';
      if (!items.length) { wrap.innerHTML = '<div style="opacity:.6">No runs yet.</div>'; return; }
      items.forEach((st) => {
        const row = document.createElement('div');
        row.className = 'pfsb-run';
        const left = document.createElement('div');
        left.style.cssText = 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:60%';
        left.textContent = (st.prompt || st.tracking_id || '').slice(0, 80);
        const right = document.createElement('div');
        right.style.cssText = 'display:flex;gap:8px;align-items:center';
        const pill = document.createElement('span');
        pill.className = 'pfsb-pill' + (st.state === 'done' ? ' done' : st.state === 'error' ? ' error' : '');
        pill.textContent = st.state || '?';
        right.appendChild(pill);
        const link = reviewLink(st);
        if (link) { link.textContent = 'review →'; right.appendChild(link); }
        row.appendChild(left); row.appendChild(right);
        wrap.appendChild(row);
      });
    } catch (_) { wrap.innerHTML = '<div style="opacity:.6">Could not load runs.</div>'; }
  }

  function open() { ensureModal().classList.add('open'); loadRuns(); }

  function installButton() {
    if (document.getElementById(BTN_ID)) return;
    ensureStyles();
    const btn = document.createElement('button');
    btn.id = BTN_ID;
    btn.className = 'pfsb-btn';
    btn.type = 'button';
    btn.textContent = 'Sandbox Build';
    btn.addEventListener('click', open);
    const sidebar = document.getElementById('sidebar')
      || document.querySelector('.sidebar')
      || document.querySelector('[data-sidebar]')
      || document.body;
    sidebar.appendChild(btn);
  }

  // Sandbox Build button removed from the sidebar (UI cleanup) — installer not
  // auto-mounted. installButton()/open() are retained but no longer invoked.
  window.ProjectForgeSandboxBuild = { open };
})();
