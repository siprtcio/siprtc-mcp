(function () {
  const STORAGE_KEY = "siprtc_chat_history_v1";
  const MAX_ITEMS = 200;

  function getMessageNodes() {
    const selectors = [
      "[data-message-id]",
      "[data-testid='message']",
      ".cl-message",
      ".message",
    ];
    for (const sel of selectors) {
      const nodes = Array.from(document.querySelectorAll(sel));
      if (nodes.length) return nodes;
    }
    return [];
  }

  function getRole(node) {
    const roleAttr =
      node.getAttribute("data-message-author") ||
      node.getAttribute("data-author") ||
      node.getAttribute("data-role");
    if (roleAttr) return roleAttr;
    const text = node.innerText || "";
    if (text.startsWith("You:")) return "user";
    if (text.startsWith("Assistant:")) return "assistant";
    return "unknown";
  }

  function snapshotMessages() {
    const nodes = getMessageNodes();
    return nodes.map((node) => ({
      role: getRole(node),
      content: (node.innerText || "").trim(),
      ts: new Date().toISOString(),
    }));
  }

  function saveHistory() {
    try {
      const messages = snapshotMessages();
      const trimmed = messages.slice(-MAX_ITEMS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch (err) {
      console.warn("Failed to save chat history", err);
    }
  }

  function hidePreviousMessages() {
    const nodes = getMessageNodes();
    if (nodes.length <= 2) return;
    const keep = nodes.slice(-2);
    nodes.slice(0, -2).forEach((node) => {
      node.style.display = "none";
      node.setAttribute("data-siprtc-hidden", "true");
    });
    keep.forEach((node) => {
      node.style.display = "";
      node.removeAttribute("data-siprtc-hidden");
    });
  }

  function onChange() {
    hidePreviousMessages();
    saveHistory();
  }

  function start() {
    const observer = new MutationObserver((mutations) => {
      if (mutations.some((m) => m.addedNodes && m.addedNodes.length)) {
        onChange();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    onChange();
  }

  window.addEventListener("load", start);
})();
