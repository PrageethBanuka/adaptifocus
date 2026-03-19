/**
 * AdaptiFocus — Content Script
 *
 * Receives intervention messages from the background worker
 * and renders graduated overlay UI on the page.
 */

// ── SVG Icons (inline, no external deps in content scripts) ─────────────────

const ICONS = {
  focus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
  alertTriangle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>',
  shieldAlert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>',
  ban: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
  arrowLeft: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>',
  thumbsDown: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z"/></svg>',
};

const LEVEL_CONFIG = {
  nudge: { icon: 'alertTriangle', label: 'Gentle Reminder' },
  warn: { icon: 'alertTriangle', label: 'Focus Alert' },
  soft_block: { icon: 'shieldAlert', label: 'Focus Pause' },
  hard_block: { icon: 'ban', label: 'Blocked' },
};

// ── State ───────────────────────────────────────────────────────────────────

let currentOverlay = null;

// ── Intervention overlay rendering ──────────────────────────────────────────

function createOverlay(level, message) {
  removeOverlay();

  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.nudge;

  const overlay = document.createElement("div");
  overlay.id = "adaptifocus-overlay";
  overlay.className = `adaptifocus-overlay adaptifocus-${level}`;

  const card = document.createElement("div");
  card.className = "adaptifocus-card";

  // Header
  const header = document.createElement("div");
  header.className = "adaptifocus-header";
  header.innerHTML = `
    <div class="adaptifocus-logo">${ICONS.focus}</div>
    <span class="adaptifocus-title">AdaptiFocus</span>
  `;

  // Level badge
  const badge = document.createElement("div");
  badge.className = "adaptifocus-level-badge";
  badge.innerHTML = `${ICONS[config.icon]}${config.label}`;

  // Message
  const messageEl = document.createElement("p");
  messageEl.className = "adaptifocus-message";
  messageEl.textContent = message;

  // Actions
  const actions = document.createElement("div");
  actions.className = "adaptifocus-actions";

  if (level === "nudge") {
    actions.appendChild(createButton("Dismiss", "secondary", () => {
      respondToIntervention("dismissed");
      removeOverlay();
    }));
    actions.appendChild(createButton("Back to study", "primary", () => {
      respondToIntervention("complied");
      removeOverlay();
      history.back();
    }));
    setTimeout(() => removeOverlay(), 8000);
  }

  if (level === "warn") {
    actions.appendChild(createButton("Not a distraction", "secondary", reportFalsePositive));
    actions.appendChild(createButton("I need this", "secondary", () => {
      respondToIntervention("dismissed");
      removeOverlay();
    }));
    actions.appendChild(createButton("Return to study", "primary", () => {
      respondToIntervention("complied");
      removeOverlay();
      history.back();
    }));
  }

  if (level === "soft_block") {
    const timer = document.createElement("p");
    timer.className = "adaptifocus-timer";
    let countdown = 15;
    timer.innerHTML = `${ICONS.clock} Access in ${countdown}s`;

    const interval = setInterval(() => {
      countdown--;
      timer.innerHTML = `${ICONS.clock} Access in ${countdown}s`;
      if (countdown <= 0) {
        clearInterval(interval);
        timer.textContent = "";
        actions.appendChild(createButton("Continue anyway", "secondary", () => {
          respondToIntervention("overrode");
          removeOverlay();
        }));
      }
    }, 1000);

    card.appendChild(header);
    card.appendChild(badge);
    card.appendChild(timer);
    card.appendChild(messageEl);

    actions.appendChild(createButton("Not a distraction", "secondary", reportFalsePositive));
    actions.appendChild(createButton("Return to study", "primary", () => {
      clearInterval(interval);
      respondToIntervention("complied");
      removeOverlay();
      history.back();
    }));

    card.appendChild(actions);
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    currentOverlay = overlay;
    requestAnimationFrame(() => overlay.classList.add("adaptifocus-visible"));
    return;
  }

  if (level === "hard_block") {
    actions.appendChild(createButton("Not a distraction", "secondary", reportFalsePositive));
    actions.appendChild(createButton("Override", "danger", () => {
      respondToIntervention("overrode");
      removeOverlay();
    }));
    actions.appendChild(createButton("Back to studying", "primary", () => {
      respondToIntervention("complied");
      removeOverlay();
      history.back();
    }));
  }

  card.appendChild(header);
  if (level !== "nudge") card.appendChild(badge);
  card.appendChild(messageEl);
  card.appendChild(actions);
  overlay.appendChild(card);

  document.body.appendChild(overlay);
  currentOverlay = overlay;

  requestAnimationFrame(() => overlay.classList.add("adaptifocus-visible"));
}

function createButton(text, variant, onClick) {
  const btn = document.createElement("button");
  btn.className = `adaptifocus-btn adaptifocus-btn-${variant}`;
  btn.textContent = text;
  btn.addEventListener("click", onClick);
  return btn;
}

function removeOverlay() {
  if (currentOverlay) {
    currentOverlay.classList.remove("adaptifocus-visible");
    setTimeout(() => {
      currentOverlay?.remove();
      currentOverlay = null;
    }, 350);
  }
}

function respondToIntervention(response) {
  chrome.runtime.sendMessage({
    type: "INTERVENTION_RESPONSE",
    response: response,
  });
}

function reportFalsePositive() {
  chrome.runtime.sendMessage({
    type: "SUBMIT_FEEDBACK",
    url: window.location.href,
    domain: window.location.hostname,
  });
  respondToIntervention("dismissed");
  removeOverlay();
}

// ── Listen for intervention messages ────────────────────────────────────────

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "INTERVENTION") {
    createOverlay(message.level, message.message);
  }
});
