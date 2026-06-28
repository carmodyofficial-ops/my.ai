(function () {
  "use strict";

  var VERSION = "S5C_protected_surface_command_classifier";
  var WARNING_CLASS = "myai-protected-surface-warning";
  var DECORATED_ATTR = "data-myai-protected-surface-decorated";

  var SURFACES = [
    {
      id: "docker_runtime",
      label: "Docker runtime",
      patterns: [
        /\bdocker\s+(compose\s+)?(up|down|restart|stop|start|rm|rmi|exec|run|build|pull|push|system|volume|network)\b/i,
        /\bdocker-compose\s+(up|down|restart|stop|start|rm|build|pull)\b/i
      ]
    },
    {
      id: "systemd_services",
      label: "systemd services",
      patterns: [
        /\bsystemctl\s+(start|stop|restart|reload|enable|disable|daemon-reload|reset-failed)\b/i,
        /\bservice\s+\S+\s+(start|stop|restart|reload)\b/i
      ]
    },
    {
      id: "firewall_rules",
      label: "firewall rules",
      patterns: [
        /\biptables\b/i,
        /\bufw\s+(allow|deny|enable|disable|delete|reset)\b/i,
        /\bnft\s+(add|delete|flush|insert|replace)\b/i,
        /\bfirewall-cmd\b/i
      ]
    },
    {
      id: "router_network_settings",
      label: "router/network settings",
      patterns: [
        /\b(router|gateway|port\s*forward|nat|dns|dhcp)\b/i,
        /\b(ip\s+route|ip\s+addr|nmcli|ifconfig|iwconfig)\b/i,
        /\b(bind|listen)\b.*\b(0\.0\.0\.0|\*|11434|7000|7001)\b/i
      ]
    },
    {
      id: "auth_guest_permissions",
      label: "auth policy or Guest permissions",
      patterns: [
        /\b(Guest|guest)\b.*\b(admin|operator|permission|role|grant|enable|elevate|sudo|agent|bash|shell|terminal|memory|rag)\b/i,
        /\b(can_use_agent|can_use_bash|can_manage_memory|is_admin)\b/i,
        /\b(auth|authorization|login|password|role)\b.*\b(change|grant|enable|disable|bypass|elevate)\b/i
      ]
    },
    {
      id: "model_endpoint_routing",
      label: "model endpoint bind/routing",
      patterns: [
        /\b(model|ollama|endpoint|routing|route)\b.*\b(bind|listen|expose|proxy|11434|host\.docker\.internal)\b/i,
        /\b\/v1\/chat\/completions\b/i,
        /\b\/api\/tags\b/i
      ]
    },
    {
      id: "memory_rag_writes",
      label: "memory/RAG writes",
      patterns: [
        /\b(memory|rag|RAG|knowledge|vector|embedding|corpus)\b.*\b(write|delete|update|insert|sync|ingest|purge|reset|reindex)\b/i
      ]
    },
    {
      id: "shell_bash_terminal",
      label: "shell/bash/terminal execution",
      patterns: [
        /\b(bash|sh|zsh|terminal|shell|subprocess|exec|spawn|sudo)\b/i,
        /\b(chmod|chown|rm\s+-rf|curl\s+.*\|\s*(bash|sh)|wget\s+.*\|\s*(bash|sh))\b/i
      ]
    },
    {
      id: "git_commit",
      label: "git commit",
      patterns: [
        /\bgit\s+add\b/i,
        /\bgit\s+commit\b/i,
        /\bgit\s+reset\b/i,
        /\bgit\s+checkout\b/i
      ]
    },
    {
      id: "remote_push",
      label: "remote push",
      patterns: [
        /\bgit\s+push\b/i,
        /\bremote\s+(push|sync)\b/i,
        /\borigin\b.*\bpush\b/i,
        /\bGitHub\b.*\b(push|sync|publish)\b/i
      ]
    }
  ];

  function classify(text) {
    var value = String(text || "");
    var matches = [];

    for (var i = 0; i < SURFACES.length; i += 1) {
      var surface = SURFACES[i];
      for (var j = 0; j < surface.patterns.length; j += 1) {
        if (surface.patterns[j].test(value)) {
          matches.push({
            id: surface.id,
            label: surface.label
          });
          break;
        }
      }
    }

    return {
      version: VERSION,
      protected: matches.length > 0,
      requiresApproval: matches.length > 0,
      matchedSurfaces: matches,
      guidance: matches.length > 0
        ? "Approval required before protected-surface mutation or execution guidance. Do not proceed until an explicit approval statement limits scope and preserves Guest/auth/network/model/memory safeguards."
        : "No protected surface detected by the local advisory classifier."
    };
  }

  function warningText(result) {
    var names = result.matchedSurfaces.map(function (m) { return m.label; }).join(", ");
    return "Approval required: this appears to touch protected surface(s): " + names +
      ". Do not execute or provide mutation guidance until explicit scope-limited approval is recorded.";
  }

  function createWarning(result) {
    var box = document.createElement("div");
    box.className = WARNING_CLASS;
    box.setAttribute("role", "note");
    box.style.cssText = [
      "box-sizing:border-box",
      "margin-top:8px",
      "padding:9px 10px",
      "border:1px solid rgba(140,120,40,.45)",
      "border-radius:10px",
      "background:rgba(255,250,230,.98)",
      "color:#3d3211",
      "font:13px/1.4 system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif"
    ].join(";");
    box.innerHTML = "<strong>Protected surface classifier:</strong> " + warningText(result);
    return box;
  }

  function nearestContainer(el) {
    if (!el) return null;
    return el.closest("form") || el.parentElement || el;
  }

  function removeExisting(container) {
    if (!container || !container.querySelectorAll) return;
    var boxes = container.querySelectorAll("." + WARNING_CLASS);
    for (var i = 0; i < boxes.length; i += 1) {
      boxes[i].remove();
    }
    container.removeAttribute(DECORATED_ATTR);
  }

  function decorateInput(el) {
    if (!el || !("value" in el)) return false;
    var container = nearestContainer(el);
    if (!container) return false;

    var result = classify(el.value || "");
    removeExisting(container);

    if (!result.requiresApproval) return false;

    container.appendChild(createWarning(result));
    container.setAttribute(DECORATED_ATTR, "true");
    return true;
  }

  function installInputWatcher() {
    if (!document.body) return;

    var selector = [
      "textarea",
      "input[type='text']",
      "input[type='search']",
      "[contenteditable='true']"
    ].join(",");

    document.addEventListener("input", function (event) {
      var target = event.target;
      if (!target || !target.matches || !target.matches(selector)) return;
      decorateInput(target);
    }, true);

    var nodes = document.querySelectorAll(selector);
    for (var i = 0; i < nodes.length; i += 1) {
      decorateInput(nodes[i]);
    }
  }

  window.MYAI_PROTECTED_SURFACE_CLASSIFIER = {
    version: VERSION,
    surfaces: SURFACES.map(function (s) { return { id: s.id, label: s.label }; }),
    classify: classify,
    decorateInput: decorateInput,
    advisoryOnly: true,
    approvalRequiredMessage: "Explicit approval is required before protected-surface mutation or execution guidance."
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installInputWatcher);
  } else {
    installInputWatcher();
  }
})();
