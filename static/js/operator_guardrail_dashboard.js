(function () {
  "use strict";

  var VERSION = "S5E_left_menu_guardrails_readonly";
  var PANEL_ID = "myai-operator-guardrail-dashboard";
  var GUARDRAILS_NAV_ID = "myai-left-nav-guardrails";
  var LIFECYCLE_NAV_ID = "myai-left-nav-proposal-lifecycle";

  function hasGlobal(name) {
    return typeof window[name] !== "undefined" && window[name] !== null;
  }

  function statusValue(ok) {
    return ok ? "OK" : "CHECK";
  }

  function badge(label, ok) {
    var span = document.createElement("span");
    span.textContent = label + ": " + statusValue(ok);
    span.style.cssText = [
      "display:inline-flex",
      "align-items:center",
      "gap:4px",
      "padding:4px 7px",
      "border-radius:999px",
      "border:1px solid " + (ok ? "rgba(80,130,80,.35)" : "rgba(160,120,40,.45)"),
      "background:" + (ok ? "rgba(235,248,235,.96)" : "rgba(255,248,225,.96)"),
      "color:#222",
      "font-size:12px",
      "white-space:nowrap"
    ].join(";");
    return span;
  }

  function row(title, text, ok) {
    var item = document.createElement("div");
    item.style.cssText = "padding:8px 0;border-top:1px solid rgba(120,120,120,.18);";

    var head = document.createElement("div");
    head.style.cssText = "display:flex;justify-content:space-between;gap:10px;align-items:center;";

    var strong = document.createElement("strong");
    strong.textContent = title;
    strong.style.cssText = "font-size:13px;";

    head.appendChild(strong);
    head.appendChild(badge(ok ? "Ready" : "Review", ok));

    var body = document.createElement("div");
    body.textContent = text;
    body.style.cssText = "margin-top:4px;color:#444;font-size:12px;line-height:1.35;";

    item.appendChild(head);
    item.appendChild(body);
    return item;
  }

  function currentState() {
    return {
      version: VERSION,
      readonly: true,
      leftMenuIntegrated: true,
      floatingChipDisabled: true,
      fieldModeUx: hasGlobal("MYAI_FIELD_MODE_STATUS_UX"),
      guestDenialUx: hasGlobal("MYAI_GUEST_TOOL_DENIAL_UX"),
      protectedSurfaceClassifier: hasGlobal("MYAI_PROTECTED_SURFACE_CLASSIFIER"),
      proposalLifecycleStatus: hasGlobal("MYAI_PROPOSAL_LIFECYCLE_STATUS"),
      fieldModeExpected: "field_disabled",
      guestExpected: "Guest remains restricted: no agent, bash, shell, terminal, admin/operator controls, or memory/RAG management.",
      approvalGateExpected: "Protected surfaces require explicit scope-limited approval before mutation or execution guidance.",
      modelEndpointExpected: "Raw LAN model endpoint isolation remains required; local model access should remain local-only.",
      remotePushExpected: "Remote push requires separate explicit approval."
    };
  }

  function removeFloatingArtifacts() {
    var oldButton = document.getElementById("myai-operator-guardrail-button");
    if (oldButton) oldButton.remove();

    var legacyButtons = Array.prototype.slice.call(document.querySelectorAll("button"));
    legacyButtons.forEach(function (button) {
      var text = (button.textContent || "").trim();
      var style = button.getAttribute("style") || "";
      if (text === "Guardrails" && /position:\s*fixed/i.test(style)) {
        button.remove();
      }
    });
  }

  function ensurePanel() {
    if (!document.body) return null;

    removeFloatingArtifacts();

    var existing = document.getElementById(PANEL_ID);
    if (existing) return existing;

    var state = currentState();

    var panel = document.createElement("section");
    panel.id = PANEL_ID;
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Read-only guardrail visibility");
    panel.setAttribute("data-version", VERSION);
    panel.style.cssText = [
      "position:fixed",
      "left:min(280px, calc(100vw - 380px))",
      "top:72px",
      "z-index:2147481999",
      "width:min(380px, calc(100vw - 24px))",
      "max-height:min(620px, calc(100vh - 96px))",
      "overflow:auto",
      "box-sizing:border-box",
      "padding:12px",
      "border:1px solid rgba(120,120,120,.32)",
      "border-radius:14px",
      "background:rgba(250,250,250,.98)",
      "box-shadow:0 10px 30px rgba(0,0,0,.18)",
      "color:#222",
      "font:13px/1.35 system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif"
    ].join(";");

    var header = document.createElement("div");
    header.style.cssText = "display:flex;justify-content:space-between;align-items:flex-start;gap:10px;";

    var titleWrap = document.createElement("div");
    var title = document.createElement("strong");
    title.textContent = "Operator Guardrails";
    title.style.cssText = "display:block;font-size:14px;";

    var subtitle = document.createElement("div");
    subtitle.textContent = "Read-only visibility. No permissions or runtime controls are changed here.";
    subtitle.style.cssText = "margin-top:3px;color:#555;font-size:12px;";

    titleWrap.appendChild(title);
    titleWrap.appendChild(subtitle);

    var close = document.createElement("button");
    close.type = "button";
    close.textContent = "Close";
    close.style.cssText = [
      "border:0",
      "background:transparent",
      "text-decoration:underline",
      "cursor:pointer",
      "color:#444",
      "font:12px system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif",
      "padding:0"
    ].join(";");

    header.appendChild(titleWrap);
    header.appendChild(close);

    var badges = document.createElement("div");
    badges.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px;";
    badges.appendChild(badge("Field UI", state.fieldModeUx));
    badges.appendChild(badge("Guest UX", state.guestDenialUx));
    badges.appendChild(badge("Classifier", state.protectedSurfaceClassifier));
    badges.appendChild(badge("Lifecycle", state.proposalLifecycleStatus));
    badges.appendChild(badge("Read-only", state.readonly));

    panel.appendChild(header);
    panel.appendChild(badges);
    panel.appendChild(row(
      "Field Mode",
      "Expected baseline: field_disabled / local-only. Keep disabled unless explicitly approved.",
      state.fieldModeUx
    ));
    panel.appendChild(row(
      "Guest restrictions",
      state.guestExpected,
      state.guestDenialUx
    ));
    panel.appendChild(row(
      "Approval gates",
      state.approvalGateExpected,
      state.protectedSurfaceClassifier
    ));
    panel.appendChild(row(
      "Model endpoint isolation",
      state.modelEndpointExpected,
      true
    ));
    panel.appendChild(row(
      "Remote push",
      state.remotePushExpected,
      true
    ));

    var footer = document.createElement("div");
    footer.textContent = "Visibility only. Protected surfaces still require explicit approval and separate validation.";
    footer.style.cssText = [
      "margin-top:10px",
      "padding-top:8px",
      "border-top:1px solid rgba(120,120,120,.18)",
      "color:#555",
      "font-size:12px"
    ].join(";");
    panel.appendChild(footer);

    close.addEventListener("click", function () {
      setOpen(false);
    });

    document.body.appendChild(panel);
    return panel;
  }

  function setOpen(open) {
    var panel = ensurePanel();
    if (!panel) return;

    panel.hidden = !open;

    [GUARDRAILS_NAV_ID, LIFECYCLE_NAV_ID].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  function openPanel() {
    setOpen(true);
  }

  function togglePanel() {
    var panel = ensurePanel();
    if (!panel) return;
    setOpen(panel.hidden);
  }

  function navItem(label, id, sublabel) {
    var button = document.createElement("button");
    button.id = id;
    button.type = "button";
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("data-myai-left-menu-item", "true");
    button.setAttribute("data-version", VERSION);
    button.style.cssText = [
      "width:100%",
      "display:flex",
      "align-items:center",
      "justify-content:space-between",
      "gap:8px",
      "box-sizing:border-box",
      "border:0",
      "border-radius:10px",
      "background:transparent",
      "color:inherit",
      "padding:8px 10px",
      "margin:2px 0",
      "font:inherit",
      "text-align:left",
      "cursor:pointer"
    ].join(";");

    var textWrap = document.createElement("span");
    textWrap.style.cssText = "display:flex;flex-direction:column;gap:1px;min-width:0;";

    var main = document.createElement("span");
    main.textContent = label;
    main.style.cssText = "font-size:14px;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";

    textWrap.appendChild(main);

    if (sublabel) {
      var sub = document.createElement("span");
      sub.textContent = sublabel;
      sub.style.cssText = "font-size:11px;line-height:1.2;color:rgba(110,110,110,.9);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";
      textWrap.appendChild(sub);
    }

    var dot = document.createElement("span");
    dot.textContent = "●";
    dot.setAttribute("aria-hidden", "true");
    dot.style.cssText = "font-size:9px;color:rgba(80,130,80,.9);flex:0 0 auto;";

    button.appendChild(textWrap);
    button.appendChild(dot);

    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      togglePanel();
    });

    button.addEventListener("mouseenter", function () {
      button.style.background = "rgba(120,120,120,.10)";
    });

    button.addEventListener("mouseleave", function () {
      button.style.background = "transparent";
    });

    return button;
  }

  function elementText(el) {
    return ((el && el.textContent) || "").replace(/\s+/g, " ").trim();
  }

  function scoreSidebarCandidate(el) {
    if (!el || el.nodeType !== 1) return 0;
    var text = elementText(el);
    var score = 0;
    ["New Chat", "Search", "Brain", "Calendar", "Compare", "Cookbook", "Deep Research", "Gallery", "Library", "Notes", "Tasks", "Theme"].forEach(function (label) {
      if (text.indexOf(label) !== -1) score += 1;
    });
    return score;
  }

  function findSidebar() {
    var selectors = [
      "aside",
      "nav",
      "[role='navigation']",
      "[class*='sidebar']",
      "[class*='side-bar']",
      "[class*='left']",
      "[class*='menu']"
    ];

    var best = null;
    var bestScore = 0;

    selectors.forEach(function (selector) {
      Array.prototype.slice.call(document.querySelectorAll(selector)).forEach(function (el) {
        var score = scoreSidebarCandidate(el);
        if (score > bestScore) {
          best = el;
          bestScore = score;
        }
      });
    });

    if (best && bestScore >= 2) return best;

    Array.prototype.slice.call(document.body ? document.body.querySelectorAll("div,section") : []).forEach(function (el) {
      var score = scoreSidebarCandidate(el);
      var rect = el.getBoundingClientRect ? el.getBoundingClientRect() : null;
      var looksLeft = rect && rect.left < 80 && rect.width > 120 && rect.width < 360 && rect.height > 300;
      if (looksLeft && score > bestScore) {
        best = el;
        bestScore = score;
      }
    });

    return bestScore >= 2 ? best : null;
  }

  function findInsertionAnchor(sidebar) {
    if (!sidebar) return null;

    var candidates = Array.prototype.slice.call(sidebar.querySelectorAll("a,button,[role='button'],div,span"));
    var theme = candidates.find(function (el) {
      return elementText(el) === "Theme";
    });
    if (theme) {
      var node = theme;
      while (node && node.parentElement && node.parentElement !== sidebar) {
        var parentText = elementText(node.parentElement);
        if (parentText.length < 80) node = node.parentElement;
        else break;
      }
      return node;
    }

    var tasks = candidates.find(function (el) {
      return elementText(el) === "Tasks";
    });
    if (tasks) {
      var taskNode = tasks;
      while (taskNode && taskNode.parentElement && taskNode.parentElement !== sidebar) {
        var taskParentText = elementText(taskNode.parentElement);
        if (taskParentText.length < 80) taskNode = taskNode.parentElement;
        else break;
      }
      return taskNode;
    }

    return null;
  }

  function ensureLeftMenuItems() {
    if (!document.body) return;

    removeFloatingArtifacts();
    ensurePanel();

    if (document.getElementById(GUARDRAILS_NAV_ID) && document.getElementById(LIFECYCLE_NAV_ID)) return;

    var sidebar = findSidebar();
    if (!sidebar) return;

    var anchor = findInsertionAnchor(sidebar);
    var guardrails = document.getElementById(GUARDRAILS_NAV_ID) || navItem("Guardrails", GUARDRAILS_NAV_ID, "read-only");
    var lifecycle = document.getElementById(LIFECYCLE_NAV_ID) || navItem("Proposal lifecycle", LIFECYCLE_NAV_ID, "audit preserved");

    var container = document.createElement("div");
    container.id = "myai-left-nav-guardrail-group";
    container.setAttribute("data-version", VERSION);
    container.style.cssText = "margin-top:4px;";

    if (!guardrails.parentElement) container.appendChild(guardrails);
    if (!lifecycle.parentElement) container.appendChild(lifecycle);

    if (anchor && anchor.parentElement) {
      anchor.parentElement.insertBefore(container, anchor.nextSibling);
    } else {
      sidebar.appendChild(container);
    }
  }

  window.MYAI_OPERATOR_GUARDRAIL_DASHBOARD = {
    version: VERSION,
    readonly: true,
    leftMenuIntegrated: true,
    floatingChipDisabled: true,
    panelId: PANEL_ID,
    guardrailsNavId: GUARDRAILS_NAV_ID,
    lifecycleNavId: LIFECYCLE_NAV_ID,
    currentState: currentState,
    open: openPanel,
    close: function () { setOpen(false); },
    toggle: togglePanel,
    ensureLeftMenuItems: ensureLeftMenuItems
  };

  function boot() {
    ensureLeftMenuItems();
    var observer = new MutationObserver(function () {
      ensureLeftMenuItems();
    });
    if (document.documentElement) {
      observer.observe(document.documentElement, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
