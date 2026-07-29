// static/js/fileMention.js
// @-mention file picker for the composer.
//
// Typing `@` followed by part of a filename offers files from the bound
// workspace and inserts the project-relative path. Before this you could only
// describe a file in prose and hope the agent guessed the path — the upload
// button attaches a COPY of a document, which is a different thing entirely and
// no help for "look at the file that's already in my project".
//
// The inserted text is a plain relative path, which is exactly what read_file,
// grep and find_symbol take — so no protocol or parsing is needed on the server
// side, and pasting a path by hand keeps working identically.

import workspaceModule from './workspace.js';

const MAX_RESULTS = 8;
// Characters allowed in the token after '@'. Includes / . - _ so a partial path
// ("src/wid") keeps matching instead of ending the token at the separator.
const TOKEN_RE = /@([A-Za-z0-9_./-]*)$/;

let _popup = null;
let _items = [];
let _active = 0;
let _input = null;
let _tokenStart = -1;
let _seq = 0;          // guards against a slow response overwriting a newer one

function _esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function _close() {
  if (_popup) { _popup.remove(); _popup = null; }
  _items = [];
  _active = 0;
  _tokenStart = -1;
}

function _render() {
  if (!_items.length) { _close(); return; }
  if (!_popup) {
    _popup = document.createElement('div');
    _popup.className = 'file-mention-popup';
    _popup.setAttribute('role', 'listbox');
    // Mousedown, not click: click fires after blur, by which point the caret
    // position we need for the replacement is gone.
    _popup.addEventListener('mousedown', (e) => {
      const row = e.target.closest('.file-mention-item');
      if (!row) return;
      e.preventDefault();
      _choose(parseInt(row.dataset.idx, 10));
    });
    (_input.parentNode || document.body).appendChild(_popup);
  }
  _popup.innerHTML = _items.map((f, i) => {
    const slash = f.lastIndexOf('/');
    const dir = slash >= 0 ? f.slice(0, slash + 1) : '';
    const base = slash >= 0 ? f.slice(slash + 1) : f;
    return `<div class="file-mention-item${i === _active ? ' active' : ''}" data-idx="${i}" role="option">` +
           `<span class="fm-dir">${_esc(dir)}</span><span class="fm-base">${_esc(base)}</span></div>`;
  }).join('');
  const act = _popup.querySelector('.file-mention-item.active');
  if (act && act.scrollIntoView) act.scrollIntoView({ block: 'nearest' });
}

function _choose(idx) {
  if (idx < 0 || idx >= _items.length || _tokenStart < 0) return;
  const path = _items[idx];
  const val = _input.value;
  const caret = _input.selectionStart;
  // Replace the '@partial' the user typed with '@full/path ' and put the caret
  // after it, so they can keep typing the sentence.
  const before = val.slice(0, _tokenStart);
  const after = val.slice(caret);
  const insert = '@' + path + ' ';
  _input.value = before + insert + after;
  const pos = before.length + insert.length;
  _input.setSelectionRange(pos, pos);
  _close();
  _input.dispatchEvent(new Event('input', { bubbles: true }));
  _input.focus();
}

async function _search(term) {
  const ws = (workspaceModule.getWorkspace && workspaceModule.getWorkspace()) || '';
  if (!ws) return null;          // no project bound — nothing to offer
  const mine = ++_seq;
  try {
    const url = `/api/workspace/files?workspace=${encodeURIComponent(ws)}` +
                `&q=${encodeURIComponent(term)}&limit=${MAX_RESULTS}`;
    const r = await fetch(url, { credentials: 'same-origin' });
    if (!r.ok) return null;
    const j = await r.json();
    if (mine !== _seq) return null;   // a newer keystroke already superseded this
    return Array.isArray(j.files) ? j.files : null;
  } catch (e) {
    return null;
  }
}

async function _onInput() {
  const caret = _input.selectionStart;
  const upto = _input.value.slice(0, caret);
  const m = upto.match(TOKEN_RE);
  if (!m) { _close(); return; }
  // Require '@' to start a word, so an email address or a decorator mid-token
  // doesn't open the picker.
  const at = caret - m[0].length;
  if (at > 0 && /[A-Za-z0-9_./-]/.test(_input.value[at - 1])) { _close(); return; }
  _tokenStart = at;
  const files = await _search(m[1]);
  if (!files || !files.length) { _close(); return; }
  _items = files;
  _active = 0;
  _render();
}

function _onKeydown(e) {
  if (!_popup || !_items.length) return;
  if (e.key === 'ArrowDown') {
    e.preventDefault(); _active = (_active + 1) % _items.length; _render();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault(); _active = (_active - 1 + _items.length) % _items.length; _render();
  } else if (e.key === 'Enter' || e.key === 'Tab') {
    // Only swallow Enter while the picker is open — otherwise it would block
    // sending the message.
    e.preventDefault(); e.stopPropagation(); _choose(_active);
  } else if (e.key === 'Escape') {
    e.preventDefault(); e.stopPropagation(); _close();
  }
}

export function initFileMention() {
  _input = document.getElementById('message');
  if (!_input || _input._fileMentionBound) return;
  _input._fileMentionBound = true;
  _input.addEventListener('input', _onInput);
  // Capture phase: the composer's own Enter-to-send handler must not fire while
  // the picker is open and Enter means "accept this file".
  _input.addEventListener('keydown', _onKeydown, true);
  _input.addEventListener('blur', () => setTimeout(_close, 120));
}

export default { initFileMention };
