/**
 * AdaptiFocus — Background Service Worker
 *
 * Tracks active tab changes, measures time on each page,
 * sends events to the backend, and checks for intervention decisions.
 */

const API_BASE = "https://adaptifocus.onrender.com"; // Production

// ── State ───────────────────────────────────────────────────────────────────

let currentTab = {
  url: null,
  domain: null,
  title: null,
  startTime: Date.now(),
  sessionId: null,
  classification: null,
};

let pendingEvents = [];
let authToken = null;

// ── Restore state from storage on startup ───────────────────────────────────

chrome.storage.local.get(["auth_token", "active_session_id", "pending_events"], (result) => {
  authToken = result.auth_token || null;
  if (result.active_session_id) {
    currentTab.sessionId = result.active_session_id;
  }
  if (result.pending_events && Array.isArray(result.pending_events)) {
    pendingEvents = result.pending_events;
  }
  console.log("[AdaptiFocus] Restored state — token:", !!authToken, "session:", currentTab.sessionId, "events:", pendingEvents.length);
});

// ── Listen for auth updates from popup ──────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "AUTH_UPDATE") {
    authToken = message.token;
    console.log("[AdaptiFocus] Auth token updated:", !!authToken);
  }

  if (message.type === "SESSION_STARTED") {
    currentTab.sessionId = message.sessionId;
    chrome.storage.local.set({ active_session_id: message.sessionId });
    console.log("[AdaptiFocus] Session started:", message.sessionId);
  }

  if (message.type === "SESSION_ENDED") {
    currentTab.sessionId = null;
    chrome.storage.local.remove("active_session_id");
    console.log("[AdaptiFocus] Session ended");
  }

  if (message.type === "GET_STATUS") {
    const timeOnCurrent = Math.round(
      (Date.now() - currentTab.startTime) / 1000
    );
    sendResponse({
      currentDomain: currentTab.domain,
      timeOnCurrent,
      sessionActive: currentTab.sessionId !== null,
      sessionId: currentTab.sessionId,
    });
    return true;
  }
});

// ── Tab tracking ────────────────────────────────────────────────────────────

function extractDomain(url) {
  try {
    const hostname = new URL(url).hostname;
    return hostname.startsWith("www.") ? hostname.slice(4) : hostname;
  } catch {
    return null;
  }
}

async function classifyCurrentPage() {
  if (!currentTab.url || !currentTab.domain) return;
  try {
    const res = await fetch(`${API_BASE}/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: currentTab.url,
        domain: currentTab.domain,
        title: currentTab.title || "",
        session_active: currentTab.sessionId !== null,
      }),
    });
    if (res.ok) {
      const result = await res.json();
      currentTab.classification = result;
      chrome.storage.local.set({ current_classification: result });
      
      // Update extension icon badge
      if (result.classification === "study") {
        chrome.action.setBadgeText({ text: "FOCUS" });
        chrome.action.setBadgeBackgroundColor({ color: "#34A853" });
      } else if (result.classification === "distraction") {
        chrome.action.setBadgeText({ text: "⚠️" });
        chrome.action.setBadgeBackgroundColor({ color: "#EA4335" });
      } else {
        chrome.action.setBadgeText({ text: "" });
      }
    }
  } catch (e) {
    console.warn("[AdaptiFocus] Classification failed:", e);
    chrome.action.setBadgeText({ text: "" });
  }
}

function switchTab(newUrl, newTitle) {
  const now = Date.now();
  let durationSeconds = 0;
  if (currentTab.startTime) {
    durationSeconds = Math.round((now - currentTab.startTime) / 1000);
  }

  // Record the previous tab as an event
  if (currentTab.url && durationSeconds > 0) {
    pendingEvents.push({
      url: currentTab.url,
      domain: currentTab.domain,
      title: currentTab.title,
      duration_seconds: durationSeconds,
      session_id: currentTab.sessionId,
      timestamp: currentTab.startTime ? new Date(currentTab.startTime).toISOString() : new Date().toISOString(),
    });
    chrome.storage.local.set({ pending_events: pendingEvents });
  }

  // Update current tab
  currentTab = {
    url: newUrl,
    domain: extractDomain(newUrl),
    title: newTitle,
    startTime: now,
    sessionId: currentTab.sessionId,
    classification: null,
  };

  chrome.action.setBadgeText({ text: "..." });
  chrome.action.setBadgeBackgroundColor({ color: "#9AA0A6" });

  // Classify the new page
  classifyCurrentPage();
}

// Listen for tab switches
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab.url) {
      switchTab(tab.url, tab.title || "");
    }
  } catch (e) {
    console.error("[AdaptiFocus] Tab activation error:", e);
  }
});

// Listen for URL changes within the same tab
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url) {
    switchTab(changeInfo.url, tab.title || "");
  }
});

// ── Event flushing ──────────────────────────────────────────────────────────

async function getAuthToken() {
  if (authToken) return authToken;
  const stored = await chrome.storage.local.get(["auth_token"]);
  authToken = stored.auth_token || null;
  return authToken;
}

async function flushEvents() {
  if (pendingEvents.length === 0) return;

  const tok = await getAuthToken();
  if (!tok) return; // Can't send without auth

  const batch = [...pendingEvents];
  pendingEvents = [];
  chrome.storage.local.set({ pending_events: pendingEvents });

  for (const event of batch) {
    try {
      const res = await fetch(`${API_BASE}/events/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tok}`,
        },
        body: JSON.stringify(event),
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
    } catch (e) {
      console.warn("[AdaptiFocus] Failed to send event, discarding to avoid corrupted loop:", e);
      // We purposefully do not re-add to queue here. If the server is rejecting it (e.g. 422 Unprocessable)
      // due to a bad schema or invalid timestamp, re-adding it will permanently break the extension's sync queue.
    }
  }
}

// ── Intervention checking ───────────────────────────────────────────────────

async function checkIntervention() {
  // Always get the ACTUAL active tab from Chrome (don't rely on in-memory state
  // because the service worker gets killed/restarted by Chrome MV3)
  const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!activeTab?.url || activeTab.url.startsWith("chrome://") ||
      activeTab.url.startsWith("chrome-extension://") ||
      activeTab.url.startsWith("about:")) {
    return;
  }

  const domain = extractDomain(activeTab.url);
  if (!domain) return;

  const tok = await getAuthToken();

  // Use in-memory time if tab matches, otherwise assume 30s (one alarm cycle)
  let timeOnCurrent = 30;
  if (currentTab.url === activeTab.url) {
    timeOnCurrent = Math.round((Date.now() - currentTab.startTime) / 1000);
  }

  // Restore session from storage if needed
  let sessionId = currentTab.sessionId;
  if (!sessionId) {
    const stored = await chrome.storage.local.get(["active_session_id"]);
    sessionId = stored.active_session_id || null;
  }

  try {
    const headers = { "Content-Type": "application/json" };
    if (tok) {
      headers["Authorization"] = `Bearer ${tok}`;
    }

    const response = await fetch(`${API_BASE}/interventions/check`, {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        current_url: activeTab.url,
        current_domain: domain,
        current_title: activeTab.title || "",
        time_on_current_seconds: timeOnCurrent,
        session_id: sessionId,
      }),
    });

    const result = await response.json();
    console.log("[AdaptiFocus] Intervention check:", domain, "=>", result.should_intervene, result.level);

    if (result.should_intervene) {
      console.log("[AdaptiFocus] Intervention triggered! Sending to tab:", activeTab.id, activeTab.url);

      const msg = {
        type: "INTERVENTION",
        level: result.level,
        message: result.message,
        urgency: result.distraction_score,
      };

      // Always inject content script first to ensure it's loaded
      try {
        await chrome.scripting.executeScript({
          target: { tabId: activeTab.id },
          files: ["content.js"],
        });
        await chrome.scripting.insertCSS({
          target: { tabId: activeTab.id },
          files: ["intervention.css"],
        });
        console.log("[AdaptiFocus] Content script injected into tab:", activeTab.id);
      } catch (injectErr) {
        console.log("[AdaptiFocus] Injection skipped:", injectErr.message);
      }

      // Small delay to let content script initialize
      await new Promise(r => setTimeout(r, 200));

      // Now send the message
      try {
        await chrome.tabs.sendMessage(activeTab.id, msg);
        console.log("[AdaptiFocus] ✅ Intervention message sent!");
      } catch (sendErr) {
        console.error("[AdaptiFocus] ❌ Failed to send message:", sendErr);
      }
    }
  } catch (e) {
    console.warn("[AdaptiFocus] Intervention check failed:", e);
  }
}

// ── Alarms for periodic tasks ───────────────────────────────────────────────
// Chrome minimum alarm interval is 0.5 minutes (30 seconds)

chrome.alarms.create("flushEvents", {
  periodInMinutes: 0.5, // 30 seconds
});

chrome.alarms.create("checkIntervention", {
  periodInMinutes: 0.5, // 30 seconds (Chrome enforced minimum)
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "flushEvents") {
    flushEvents();
  } else if (alarm.name === "checkIntervention") {
    checkIntervention();
  }
});

console.log("[AdaptiFocus] Background service worker initialized");
