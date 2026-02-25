/**
 * AdaptiFocus Popup — Google Sign-In + Dashboard
 */

const API_BASE = "https://adaptifocus.onrender.com"; // Production

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
    chrome.tabs.create({ url: "http://localhost:5173" });
  });

  // Show dev login button on localhost
  if (API_BASE.includes("localhost")) {
    document.getElementById("dev-login-btn").style.display = "block";
  }
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
  try {
    const res = await fetch(`${API_BASE}/auth/dev-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "dev@test.local", username: "Developer" }),
    });
    if (!res.ok) return showError("Dev login failed");
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
    showError("Cannot connect to server. Is backend running?");
  }
}

// ── Auth State ──────────────────────────────────────────────────────────

async function checkAuth() {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) { await handleLogout(); return; }

    const profile = await res.json();
    if (!profile.consent_given) {
      showView("consent");
      const consentUser = document.getElementById("consent-user");
      consentUser.innerHTML = `<strong>${profile.username}</strong><br><span style="color:#888">${profile.email}</span>`;
    } else {
      showView("main");
      document.getElementById("user-name").textContent = user?.username || "User";
      if (user?.picture || profile.picture) {
        const avatar = document.getElementById("user-avatar");
        avatar.src = profile.picture || user.picture;
        avatar.style.display = "block";
      }
      loadStats();
      loadCurrentTab();
    }
  } catch (e) {
    showView("login");
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
  try {
    const res = await fetch(`${API_BASE}/analytics/focus-summary?days=1`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("focus-score").textContent = `${data.focus_percentage || 0}%`;
    const mins = Math.round((data.focus_seconds || 0) / 60);
    document.getElementById("focus-time").textContent = mins > 60 ? `${Math.floor(mins/60)}h` : `${mins}m`;
    document.getElementById("distractions").textContent = data.distraction_events || "0";
    document.getElementById("interventions").textContent = data.interventions_today || "0";
  } catch (e) { /* stats unavailable */ }
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

async function startSession() {
  const topic = document.getElementById("study-topic").value || "General Study";
  try {
    await fetch(`${API_BASE}/sessions/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ study_topic: topic }),
    });
  } catch (e) {}
  sessionStart = Date.now();
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
    await fetch(`${API_BASE}/sessions/stop`, {
      method: "POST", headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {}
  document.getElementById("start-session").style.display = "block";
  document.getElementById("stop-session").style.display = "none";
  document.getElementById("session-timer").style.display = "none";
  loadStats();
}
