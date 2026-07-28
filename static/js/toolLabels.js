// static/js/toolLabels.js
// Friendly present-tense verbs for agent tool steps, shared by the live stream
// (chat.js) and the reload/replay renderer (chatRenderer.js).
//
// Single source of truth on purpose: the two renderers previously disagreed —
// the live view showed "Writing" while the completed/reloaded view showed the
// raw tool name "write_file", so a step appeared to rename itself mid-run and
// again after a refresh. chat.js imports chatRenderer.js, so this map lives in
// its own module rather than being exported from either one (no import cycle).

export const TOOL_LABELS = {
  // search / web
  'web_search': 'Searching',
  'web_fetch': 'Fetching',
  'deep_research': 'Researching',
  // execution
  'bash': 'Running',
  'python': 'Running',
  'code_sandbox': 'Testing',
  'run_tests': 'Testing',
  'lint_format': 'Linting',
  // files — read
  'read_file': 'Reading',
  'read_document': 'Reading',
  'ls': 'Browsing',
  'list_files': 'Browsing',
  'glob': 'Finding',
  'grep': 'Searching',
  'get_workspace': 'Locating',
  // files — write
  'edit_file': 'Editing',
  'multi_edit': 'Editing',
  'apply_patch': 'Patching',
  'write_file': 'Writing',
  'create_document': 'Writing',
  'update_document': 'Writing',
  'delete_file': 'Deleting',
  'move_file': 'Moving',
  'git': 'Git',
  // agent bookkeeping
  'update_plan': 'Planning',
  'ask_user': 'Asking',
  'dispatch_subagents': 'Delegating',
  'manage_memory': 'Remembering',
  'save_memory': 'Remembering',
  'search_memory': 'Recalling',
  'manage_session': 'Organizing',
  'image_gen': 'Generating',
  'generate_image': 'Generating',
  'list_models': 'Browsing',
  'ui_control': 'Adjusting',
};

/** Friendly label for a tool name, falling back to the raw name. */
export function toolLabel(name) {
  return TOOL_LABELS[String(name || '').toLowerCase()] || name;
}

export default TOOL_LABELS;
