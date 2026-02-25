/**
 * AdaptiFocus — Content Script
 *
 * Receives intervention messages from the background worker
 * and renders graduated overlay UI on the page.
 */

// ── State ───────────────────────────────────────────────────────────────────

let currentOverlay = null;

// ── Intervention overlay rendering ──────────────────────────────────────────

function createOverlay(level, message) {
  // Remove existing overlay
  removeOverlay();

  const overlay = document.createElement("div");
  overlay.id = "adaptifocus-overlay";
  overlay.className = `adaptifocus-overlay adaptifocus-${level}`;

  const card = document.createElement("div");
  card.className = "adaptifocus-card";

  // Logo and title
  const header = document.createElement("div");
  header.className = "adaptifocus-header";
  header.innerHTML = `
    <span class="adaptifocus-logo">🎯</span>
    <span class="adaptifocus-title">AdaptiFocus</span>
  `;

  // Message
  const messageEl = document.createElement("p");
  messageEl.className = "adaptifocus-message";
  messageEl.textContent = message;

  // Actions
  const actions = document.createElement("div");
  actions.className = "adaptifocus-actions";

  if (level === "nudge") {
    const dismissBtn = createButton("Got it", "secondary", () => {
      respondToIntervention("dismissed");
      removeOverlay();
    });
    actions.appendChild(dismissBtn);

    const focusBtn = createButton("Back to study", "primary", () => {
      respondToIntervention("complied");
      removeOverlay();
      history.back();
    });
    actions.appendChild(focusBtn);

    // Auto-dismiss nudge after 8 seconds
    setTimeout(() => removeOverlay(), 8000);
  }

  if (level === "warn") {
    const dismissBtn = createButton("I need this", "secondary", () => {
      respondToIntervention("dismissed");
      removeOverlay();
    });
    actions.appendChild(dismissBtn);

    const focusBtn = createButton("Return to study", "primary", () => {
      respondToIntervention("complied");
      removeOverlay();
      history.back();
    });
    actions.appendChild(focusBtn);
  }

  if (level === "soft_block") {
    const timer = document.createElement("p");
    timer.className = "adaptifocus-timer";
    let countdown = 15;
    timer.textContent = `Access in ${countdown}s...`;

    const interval = setInterval(() => {
      countdown--;
      timer.textContent = `Access in ${countdown}s...`;
      if (countdown <= 0) {
        clearInterval(interval);
        timer.textContent = "";
        const continueBtn = createButton("Continue anyway", "secondary", () => {
          respondToIntervention("overrode");
          removeOverlay();
        });
        actions.appendChild(continueBtn);
      }
    }, 1000);

    card.appendChild(timer);

    const focusBtn = createButton("Return to study", "primary", () => {
      clearInterval(interval);
      respondToIntervention("complied");
      removeOverlay();
      history.back();
    });
    actions.appendChild(focusBtn);
  }

  if (level === "hard_block") {
    const overrideBtn = createButton("Override (I need this)", "danger", () => {
      respondToIntervention("overrode");
      removeOverlay();
    });
    actions.appendChild(overrideBtn);

    const focusBtn = createButton("Back to studying", "primary", () => {
      respondToIntervention("complied");
      removeOverlay();
      history.back();
    });
    actions.appendChild(focusBtn);
  }

  card.appendChild(header);
  card.appendChild(messageEl);
  card.appendChild(actions);
  overlay.appendChild(card);

  document.body.appendChild(overlay);
  currentOverlay = overlay;

  // Animate in
  requestAnimationFrame(() => {
    overlay.classList.add("adaptifocus-visible");
  });
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
    }, 300);
  }
}

function respondToIntervention(response) {
  chrome.runtime.sendMessage({
    type: "INTERVENTION_RESPONSE",
    response: response,
  });
}

// ── Listen for intervention messages ────────────────────────────────────────

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "INTERVENTION") {
    createOverlay(message.level, message.message);
  }
});
