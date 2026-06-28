(function () {
  "use strict";

  var VERSION = "S5B_guest_tool_denial_ux";
  var GUIDANCE_CLASS = "myai-guest-tool-denial-guidance";
  var MARKER_ATTR = "data-myai-denial-ux";

  var SAFE_GUIDANCE = "This action is unavailable for Guest or restricted accounts. Guest access is intentionally limited: no agent mode, bash, shell, terminal, admin/operator controls, or memory/RAG management. Use a normal authorized account or request operator approval for protected work."; 

  var DENIAL_TERMS = [
    "denied", "not allowed", "forbidden", "unauthorized", "restricted",
    "permission", "unavailable", "disabled", "blocked", "cannot", "403"
  ];

  var TOOL_TERMS = [
    "guest", "agent", "agent mode", "tool", "bash", "shell", "terminal",
    "sudo", "subprocess", "admin", "operator", "memory", "rag", "knowledge"
  ];

  function lowerText(value) {
    return String(value || "").toLowerCase();
  }

  function hasAny(text, terms) {
    for (var i = 0; i < terms.length; i += 1) {
      if (text.indexOf(terms[i]) !== -1) return true;
    }
    return false;
  }

  function isLikelyDenialText(text) {
    var t = lowerText(text);
    if (t.length < 5 || t.length > 1200) return false;
    return hasAny(t, DENIAL_TERMS) && hasAny(t, TOOL_TERMS);
  }

  function alreadyDecorated(el) {
    if (!el || !el.children) return false;
    for (var i = 0; i < el.children.length; i += 1) {
      var child = el.children[i];
      if (child.classList && child.classList.contains(GUIDANCE_CLASS)) return true;
    }
    return false;
  }

  function createGuidance(actionLabel) {
    var box = document.createElement("div");
    box.className = GUIDANCE_CLASS;
    box.setAttribute("role", "note");
    box.style.cssText = [
      "box-sizing:border-box",
      "margin-top:8px",
      "padding:9px 10px",
      "border:1px solid rgba(120,120,120,.35)",
      "border-radius:10px",
      "background:rgba(245,245,245,.98)",
      "color:#333",
      "font:13px/1.4 system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif"
    ].join(";");
    box.innerHTML = "<strong>Access guidance:</strong> " + SAFE_GUIDANCE;
    if (actionLabel) {
      box.setAttribute("data-action", actionLabel);
    }
    return box;
  }

  function decorateElement(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.classList && el.classList.contains(GUIDANCE_CLASS)) return false;
    if (el.closest && el.closest("." + GUIDANCE_CLASS)) return false;
    if (el.getAttribute && el.getAttribute(MARKER_ATTR) === "true") return false;

    var text = el.innerText || el.textContent || "";
    if (!isLikelyDenialText(text)) return false;
    if (alreadyDecorated(el)) return false;

    el.appendChild(createGuidance("restricted_action"));
    el.setAttribute(MARKER_ATTR, "true");
    return true;
  }

  function scan() {
    if (!document.body) return 0;
    var selector = [
      "[role=\"alert\"]", ".alert", ".toast", ".error", ".notification",
      ".modal", ".banner", "[data-error]", "[data-denial]", "[data-restricted]"
    ].join(",");
    var nodes = document.querySelectorAll(selector);
    var count = 0;
    for (var i = 0; i < nodes.length; i += 1) {
      if (decorateElement(nodes[i])) count += 1;
    }
    return count;
  }

  function installObserver() {
    if (!document.body || !window.MutationObserver) return;
    var observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i += 1) {
        var added = mutations[i].addedNodes || [];
        for (var j = 0; j < added.length; j += 1) {
          var node = added[j];
          if (node && node.nodeType === 1) {
            decorateElement(node);
            if (node.querySelectorAll) scan();
          }
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  window.MYAI_GUEST_TOOL_DENIAL_UX = {
    version: VERSION,
    safeGuidance: SAFE_GUIDANCE,
    scan: scan,
    showGuidance: function (target, actionLabel) {
      if (!target || !target.appendChild) return false;
      if (alreadyDecorated(target)) return false;
      target.appendChild(createGuidance(actionLabel || "restricted_action"));
      return true;
    }
  };

  function ready() {
    scan();
    installObserver();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ready);
  } else {
    ready();
  }
})();
