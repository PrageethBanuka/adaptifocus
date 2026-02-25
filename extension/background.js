/**
 * AdaptiFocus — Background Service Worker
 *
 * Tracks active tab changes, measures time on each page,
 * sends events to the backend, and checks for intervention decisions.
 */

const API_BASE = "https://adaptifocus.onrender.com"; // Production
const CHECK_INTERVAL_MS = 10000; // Check every 10 seconds
const EVENT_FLUSH_INTERVAL_MS = 30000; // Flush events every 30 seconds

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

// Load auth token from storage
chrome.storage.local.get(["auth_token"], (result) => {
  authToken = result.auth_token || null;
});

// Listen for auth updates from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "AUTH_UPDATE") {
    authToken = message.token;
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
      // Store for popup to read
      chrome.storage.local.set({ current_classification: result });
    }
  } catch (e) {
    console.warn("[AdaptiFocus] Classification failed:", e);
  }
}

function switchTab(newUrl, newTitle) {
  const now = Date.now();
  const durationSeconds = Math.round((now - currentTab.startTime) / 1000);

  // Record the previous tab as an event
  if (currentTab.url && durationSeconds > 0) {
    pendingEvents.push({
      url: currentTab.url,
      domain: currentTab.domain,
      title: currentTab.title,
      duration_seconds: durationSeconds,
      session_id: currentTab.sessionId,
      timestamp: new Date(currentTab.startTime).toISOString(),
    });
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

async function flushEvents() {
  if (pendingEvents.length === 0) return;
  if (!authToken) {
    // Try to get token from storage
    const stored = await chrome.storage.local.get(["auth_token"]);
    authToken = stored.auth_token || null;
    if (!authToken) return; // Can't send without auth
  }

  const batch = [...pendingEvents];
  pendingEvents = [];

  for (const event of batch) {
    try {
      await fetch(`${API_BASE}/events/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authToken}`,
        },
        body: JSON.stringify(event),
      });
    } catch (e) {
      console.warn("[AdaptiFocus] Failed to send event:", e);
      // Re-queue failed events
      pendingEvents.push(event);
    }
  }
}

// ── Intervention checking ───────────────────────────────────────────────────

async function checkIntervention() {
  if (!currentTab.url || !currentTab.domain) return;

  const timeOnCurrent = Math.round(
    (Date.now() - currentTab.startTime) / 1000
  );

  try {
    const headers = { "Content-Type": "application/json" };
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${API_BASE}/interventions/check`, {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        current_url: currentTab.url,
        current_domain: currentTab.domain,
        current_title: currentTab.title,
        time_on_current_seconds: timeOnCurrent,
        session_id: currentTab.sessionId,
      }),
    });

    const result = await response.json();

    if (result.should_intervene) {
      // Send intervention to content script
      const [activeTab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });
      if (activeTab?.id) {
        chrome.tabs.sendMessage(activeTab.id, {
          type: "INTERVENTION",
          level: result.level,
          message: result.message,
          urgency: result.distraction_score,
        });
      }
    }
  } catch (e) {
    console.warn("[AdaptiFocus] Intervention check failed:", e);
  }
}

// ── Alarms for periodic tasks ───────────────────────────────────────────────

chrome.alarms.create("flushEvents", {
  periodInMinutes: EVENT_FLUSH_INTERVAL_MS / 60000,
});

chrome.alarms.create("checkIntervention", {
  periodInMinutes: CHECK_INTERVAL_MS / 60000,
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "flushEvents") {
    flushEvents();
  } else if (alarm.name === "checkIntervention") {
    checkIntervention();
  }
});

// ── Message handling (from popup/content scripts) ───────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "START_SESSION") {
    fetch(`${API_BASE}/sessions/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        study_topic: message.topic,
        planned_duration_minutes: message.duration || 45,
      }),
    })
      .then((r) => r.json())
      .then((session) => {
        currentTab.sessionId = session.id;
        sendResponse({ success: true, session });
      })
      .catch((e) => sendResponse({ success: false, error: e.message }));
    return true; // Keep channel open for async response
  }

  if (message.type === "END_SESSION") {
    if (currentTab.sessionId) {
      fetch(`${API_BASE}/sessions/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: currentTab.sessionId }),
      })
        .then((r) => r.json())
        .then((session) => {
          currentTab.sessionId = null;
          sendResponse({ success: true, session });
        })
        .catch((e) => sendResponse({ success: false, error: e.message }));
    } else {
      sendResponse({ success: false, error: "No active session" });
    }
    return true;
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

console.log("[AdaptiFocus] Background service worker initialized");
