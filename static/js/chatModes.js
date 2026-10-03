// Per-chat modes: Chat / Agent / Agent + "Ask first".
//
// The Agent/Chat toggle stays the source of truth for the mode (a dozen
// modules read #mode-agent-btn.active). This adds:
//   * an "Ask first" switch, shown in Agent mode only. When on, each turn asks
//     the server for approval_mode=all (every action tool pauses for an
//     Allow / Allow for this chat / Deny card) and the agent proposes a plan
//     with clickable choices before acting. The server can only make this
//     stricter than the operator's setting, never looser.
//   * memory per chat: switching chats restores that chat's mode + switch;
//     a new chat inherits whatever is currently selected.
import Storage from './storage.js';

const MAP_KEY = 'odysseus-chat-modes';
const MAX_ENTRIES = 300;

let _currentSid = null;
let _restoring = false;

function _loadMap() {
  const m = Storage.getJSON(MAP_KEY, {});
  return (m && typeof m === 'object') ? m : {};
}

function _saveMap(m) {
  const ids = Object.keys(m);
  if (ids.length > MAX_ENTRIES) {
    ids.sort((a, b) => (m[a].t || 0) - (m[b].t || 0));
    ids.slice(0, ids.length - MAX_ENTRIES).forEach((id) => { delete m[id]; });
  }
  Storage.setJSON(MAP_KEY, m);
}

function _isAgent() {
  const b = document.getElementById('mode-agent-btn');
  return !!(b && b.classList.contains('active'));
}

export function getAskFirst() {
  return !!Storage.getToggle('askFirst', false);
}

/** approval_mode to send with a turn: 'all' in Agent + Ask first, else ''. */
export function getApprovalMode() {
  return (_isAgent() && getAskFirst()) ? 'all' : '';
}

function _paint() {
  const btn = document.getElementById('ask-first-btn');
  if (!btn) return;
  const on = getAskFirst();
  btn.classList.toggle('active', on);
  btn.setAttribute('aria-pressed', String(on));
  btn.title = on
    ? 'Ask first is ON — the agent proposes a plan and asks before every action. Click to let it act on its own.'
    : 'Ask first is OFF — the agent acts on its own. Click to approve each action and see a plan first.';
  btn.style.display = _isAgent() ? '' : 'none';
}

function _remember() {
  if (_restoring || !_currentSid) return;
  const m = _loadMap();
  m[_currentSid] = { mode: _isAgent() ? 'agent' : 'chat', ask: getAskFirst(), t: Date.now() };
  _saveMap(m);
}

function setAskFirst(on) {
  Storage.setToggle('askFirst', !!on);
  _paint();
  _remember();
}

/** Called by sessions.selectSession — restore this chat's mode + switch. */
export function restoreForSession(sid) {
  _currentSid = sid || null;
  const saved = sid ? _loadMap()[sid] : null;
  if (!saved) { _remember(); _paint(); return; }
  _restoring = true;
  try {
    const wantAgent = saved.mode === 'agent';
    if (wantAgent !== _isAgent()) {
      const target = document.getElementById(wantAgent ? 'mode-agent-btn' : 'mode-chat-btn');
      // Respect a hidden Agent button (user lacks the agent privilege).
      if (target && target.style.display !== 'none') target.click();
    }
    Storage.setToggle('askFirst', !!saved.ask);
  } finally {
    _restoring = false;
  }
  _paint();
}

/** Called when a turn is sent, so a brand-new chat remembers its mode. */
export function noteSent(sid) {
  if (sid) _currentSid = sid;
  _remember();
}

export function init() {
  const toggle = document.querySelector('.chat-input-right .mode-toggle');
  const agentBtn = document.getElementById('mode-agent-btn');
  if (!toggle || !agentBtn || document.getElementById('ask-first-btn')) return;
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.id = 'ask-first-btn';
  btn.className = 'ask-first-btn';
  btn.innerHTML =
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>' +
    '<path d="m9 12 2 2 4-4"/></svg><span>Ask first</span>';
  btn.addEventListener('click', () => setAskFirst(!getAskFirst()));
  toggle.parentNode.insertBefore(btn, toggle);
  // Follow the Agent/Chat toggle, whoever flips it (button, slash command,
  // model-capability fallback, document auto-escalation).
  new MutationObserver(() => { _paint(); _remember(); })
    .observe(agentBtn, { attributes: true, attributeFilter: ['class'] });
  _paint();
}

const chatModes = { init, getAskFirst, getApprovalMode, restoreForSession, noteSent };
window.chatModes = chatModes;
export default chatModes;
