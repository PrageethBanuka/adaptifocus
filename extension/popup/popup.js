/**
 * AdaptiFocus Popup — Google Sign-In + Dashboard
 */

const API_BASE = "https://adaptifocus.onrender.com"; // Change for production

let token = null;
let user = null;

// ── Init ────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  const stored = await chrome.storage.local.get(["auth_token", "user_data"]);
  if (stored.auth_token) {
    token = stored.auth_token;
    user = stored.user_data;
    await checkAuth();
  } else {
    showView("login");
  }

  // Buttons
  document.getElementById("google-signin-btn").addEventListener("click", googleSignIn);
  document.getElementById("dev-login-btn").addEventListener("click", devLogin);
  document.getElementById("consent-btn").addEventListener("click", handleConsent);
  document.getElementById("start-session").addEventListener("click", startSession);
  document.getElementById("stop-session").addEventListener("click", stopSession);
  document.getElementById("logout-btn").addEventListener("click", handleLogout);
  document.getElementById("delete-data").addEventListener("click", handleDeleteData);
  document.getElementById("open-dashboard").addEventListener("click", (e) => {
    e.preventDefault();
    if (token) {
      chrome.tabs.create({ url: `https://adaptifocus-dashboard.onrender.com?token=${token}` });
    } else {
      chrome.tabs.create({ url: "https://adaptifocus-dashboard.onrender.com" });
    }
  });

  // Always show dev login (backend DEV_MODE controls whether it works)
  document.getElementById("dev-login-btn").style.display = "block";
  document.getElementById("dev-submit-btn").addEventListener("click", devSubmit);
});

function showView(name) {
  document.querySelectorAll(".view").forEach((v) => (v.style.display = "none"));
  document.getElementById(`${name}-view`).style.display = "block";
}

function showError(msg) {
  const el = document.getElementById("auth-error");
  el.textContent = msg;
  el.style.display = "block";
  setTimeout(() => (el.style.display = "none"), 5000);
}

// ── Google Sign-In ──────────────────────────────────────────────────────

async function googleSignIn() {
  try {
    // Use chrome.identity to get a Google auth token
    const authToken = await new Promise((resolve, reject) => {
      chrome.identity.getAuthToken({ interactive: true }, (token) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(token);
        }
      });
    });

    // Send the token to our backend for verification
    const res = await fetch(`${API_BASE}/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: authToken }),
    });

    if (!res.ok) {
      const err = await res.json();
      return showError(err.detail || "Sign-in failed");
    }

    const data = await res.json();
    token = data.access_token;
    user = {
      id: data.user_id,
      username: data.username,
      email: data.email,
      group: data.experiment_group,
    };

    await chrome.storage.local.set({ auth_token: token, user_data: user });
    chrome.runtime.sendMessage({ type: "AUTH_UPDATE", token, user });

    if (data.is_new_user) {
      showView("consent");
      const consentUser = document.getElementById("consent-user");
      consentUser.innerHTML = `<strong>Welcome, ${user.username}!</strong><br><span style="color:#888">${user.email}</span>`;
    } else {
      await checkAuth();
    }
  } catch (e) {
    showError(e.message || "Google Sign-In failed");
  }
}

async function devLogin() {
  // Show the name/email fields
  const fields = document.getElementById("dev-login-fields");
  fields.style.display = "block";
  document.getElementById("dev-name").focus();
}

async function devSubmit() {
  const name = document.getElementById("dev-name").value.trim();
  const email = document.getElementById("dev-email").value.trim();
  if (!name || !email) return showError("Please enter your name and email");

  try {
    const res = await fetch(`${API_BASE}/auth/dev-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, username: name }),
    });
    if (!res.ok) return showError("Login failed — is the backend running?");
    const data = await res.json();
    token = data.access_token;
    user = { id: data.user_id, username: data.username, email: data.email, group: data.experiment_group };
    await chrome.storage.local.set({ auth_token: token, user_data: user });
    chrome.runtime.sendMessage({ type: "AUTH_UPDATE", token, user });
    showView("main");
    document.getElementById("user-name").textContent = user.username;
    loadStats();
    loadCurrentTab();
  } catch (e) {
    showError("Cannot connect to server. Try again in 30s (server may be waking up).");
  }
}

// ── Auth State ──────────────────────────────────────────────────────────

async function checkAuth() {
  // Show main view immediately from cached data
  if (token && user) {
    showView("main");
    document.getElementById("user-name").textContent = user.username || "User";
    loadStats();
    loadCurrentTab();
  }

  // Verify token in background (don't block UI)
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) {
      // Token is actually invalid — force re-login
      await handleLogout();
      return;
    }
    if (!res.ok) return; // Server error — keep cached session

    const profile = await res.json();
    if (!profile.consent_given) {
      showView("consent");
      const consentUser = document.getElementById("consent-user");
      consentUser.innerHTML = `<strong>${profile.username}</strong><br><span style="color:#888">${profile.email}</span>`;
    } else if (profile.picture) {
      const avatar = document.getElementById("user-avatar");
      avatar.src = profile.picture;
      avatar.style.display = "block";
    }
  } catch (e) {
    // Network error (cold start) — keep cached session, don't force login
    console.warn("[AdaptiFocus] Auth check failed (backend may be waking up):", e);
  }
}

async function handleConsent() {
  await fetch(`${API_BASE}/auth/consent`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ consent_given: true }),
  });
  showView("main");
  document.getElementById("user-name").textContent = user?.username || "User";
  loadStats();
}

async function handleLogout(e) {
  if (e) e.preventDefault();
  // Revoke Google token
  try {
    const gToken = await new Promise((resolve) => {
      chrome.identity.getAuthToken({ interactive: false }, resolve);
    });
    if (gToken) {
      chrome.identity.removeCachedAuthToken({ token: gToken });
    }
  } catch (e) { /* ignore */ }

  token = null; user = null;
  await chrome.storage.local.remove(["auth_token", "user_data"]);
  chrome.runtime.sendMessage({ type: "AUTH_UPDATE", token: null, user: null });
  showView("login");
}

async function handleDeleteData(e) {
  e.preventDefault();
  if (!confirm("This will permanently delete ALL your data. Continue?")) return;
  await fetch(`${API_BASE}/auth/data`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  alert("All your data has been deleted.");
}

// ── Stats ───────────────────────────────────────────────────────────────

async function loadStats() {
  const loader = document.getElementById("server-loading");
  const timeoutId = setTimeout(() => {
    if (loader) loader.style.display = "inline";
  }, 1000); // Show loading if backend takes > 1s (Render cold start)

  try {
    const res = await fetch(`${API_BASE}/analytics/focus-summary?days=1`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    
    clearTimeout(timeoutId);
    if (loader) loader.style.display = "none";

    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("focus-score").textContent = `${data.focus_percentage || 0}%`;
    const mins = Math.round((data.focus_seconds || 0) / 60);
    document.getElementById("focus-time").textContent = mins > 60 ? `${Math.floor(mins/60)}h` : `${mins}m`;
    document.getElementById("distractions").textContent = data.distraction_events || "0";
    document.getElementById("interventions").textContent = data.interventions_today || "0";
  } catch (e) { 
    clearTimeout(timeoutId);
    if (loader) loader.style.display = "none";
  }
}

async function loadCurrentTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.url) return;

    const domain = new URL(tab.url).hostname.replace(/^www\./, "");
    document.getElementById("current-domain").textContent = domain;

    // Always classify the CURRENT tab directly — never use stale storage
    const res = await fetch(`${API_BASE}/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: tab.url,
        domain: domain,
        title: tab.title || "",
      }),
    });
    if (res.ok) {
      const result = await res.json();
      displayClassification(result);
    }
  } catch (e) { /* tab access or API failed */ }
}

function displayClassification(result) {
  const el = document.getElementById("classification");
  const cls = result.classification || "neutral";
  el.textContent = cls.charAt(0).toUpperCase() + cls.slice(1);
  el.className = "classification " + cls;
}

// ── Sessions ────────────────────────────────────────────────────────────

let sessionInterval = null, sessionStart = null;

// Restore active session on popup open
(async () => {
  const stored = await chrome.storage.local.get(["active_session_id", "session_start_time"]);
  if (stored.active_session_id) {
    sessionStart = stored.session_start_time || Date.now();
    document.getElementById("start-session").style.display = "none";
    document.getElementById("stop-session").style.display = "block";
    document.getElementById("session-timer").style.display = "block";
    sessionInterval = setInterval(updateTimer, 1000);
    updateTimer();
  }
})();

async function startSession() {
  const topic = document.getElementById("study-topic").value || "General Study";
  try {
    const res = await fetch(`${API_BASE}/sessions/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ study_topic: topic }),
    });
    if (res.ok) {
      const session = await res.json();
      // Tell background.js about the session
      chrome.runtime.sendMessage({ type: "SESSION_STARTED", sessionId: session.id });
      // Persist session state so it survives popup close
      sessionStart = Date.now();
      await chrome.storage.local.set({
        active_session_id: session.id,
        session_start_time: sessionStart,
      });
    }
  } catch (e) {
    console.warn("[AdaptiFocus] Session start failed:", e);
  }
  sessionStart = sessionStart || Date.now();
  document.getElementById("start-session").style.display = "none";
  document.getElementById("stop-session").style.display = "block";
  document.getElementById("session-timer").style.display = "block";
  sessionInterval = setInterval(updateTimer, 1000);
}

function updateTimer() {
  const s = Math.floor((Date.now() - sessionStart) / 1000);
  document.getElementById("timer-display").textContent =
    `${String(Math.floor(s/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;
}

async function stopSession() {
  clearInterval(sessionInterval);
  try {
    const stored = await chrome.storage.local.get(["active_session_id"]);
    if (stored.active_session_id) {
      await fetch(`${API_BASE}/sessions/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ session_id: stored.active_session_id }),
      });
    }
  } catch (e) {
    console.warn("[AdaptiFocus] Session end failed:", e);
  }
  // Tell background.js session ended
  chrome.runtime.sendMessage({ type: "SESSION_ENDED" });
  await chrome.storage.local.remove(["active_session_id", "session_start_time"]);
  document.getElementById("start-session").style.display = "block";
  document.getElementById("stop-session").style.display = "none";
  document.getElementById("session-timer").style.display = "none";
  loadStats();
}

