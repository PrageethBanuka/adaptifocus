# 🎯 AdaptiFocus — AI-Driven Adaptive Attention Management

An intelligent Chrome extension that helps students stay focused during online study sessions using AI-powered context-aware classification and graduated micro-interventions.

> **Research Project** — Built as part of an academic study on adaptive attention management for digital wellbeing.

## ✨ Key Features

- **Context-Aware AI Classification** — Unlike simple domain blockers, AdaptiFocus analyzes page content to distinguish between educational YouTube lectures and distraction videos
- **Multi-Agent System** — Context Agent, Pattern Agent, and Intervention Agent work together for intelligent decision-making
- **Graduated Interventions** — Gentle nudges → stronger reminders → focus prompts, adapting to your behavior
- **Real-Time Analytics** — Track focus time, distraction patterns, and study session progress
- **Privacy-First** — Only tracks domains and time, never page content

## 🏗️ Architecture

```
┌──────────────────┐     ┌──────────────────────────────────┐
│  Chrome Extension │ ←→  │     FastAPI Backend               │
│  (Manifest V3)   │     │  ┌──────────┐ ┌───────────────┐  │
│  • Tab Tracking   │     │  │ Context  │ │ Pattern       │  │
│  • Popup UI       │     │  │ Agent    │ │ Classifier    │  │
│  • Interventions  │     │  │ (NLP)    │ │ (Random Forest│  │
│  • Google Auth    │     │  └──────────┘ │  94.3% acc)   │  │
└──────────────────┘     │               └───────────────┘  │
                          │  ┌──────────┐ ┌───────────────┐  │
┌──────────────────┐     │  │Interven- │ │ Analytics     │  │
│  React Dashboard  │ ←→  │  │tion Agent│ │ Engine        │  │
│  (Vite + Charts)  │     │  └──────────┘ └───────────────┘  │
└──────────────────┘     └──────────────────────────────────┘
```

## 📁 Project Structure

```
research_project/
├── backend/               # FastAPI server
│   ├── agents/           # Multi-agent system (Context, Pattern, Intervention)
│   ├── api/              # REST API routes (auth, events, analytics)
│   ├── database/         # SQLAlchemy models (PostgreSQL/SQLite)
│   ├── ml/               # ML pipeline (Random Forest, feature extraction)
│   └── tests/            # pytest test suite (28 tests)
├── extension/            # Chrome Extension (Manifest V3)
│   ├── background.js     # Service worker (tab tracking, event flush)
│   ├── content.js        # Intervention overlay injection
│   ├── popup/            # Extension popup (login, stats, session control)
│   └── manifest.json     # Extension manifest
├── dashboard/            # React + Vite analytics dashboard
│   └── src/components/   # Charts, timeline, focus metrics
├── paper/                # LaTeX research paper
└── docs/                 # Guides & documentation
```

## 🚀 Quick Start

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Extension
1. Go to `chrome://extensions/` → Enable Developer Mode
2. Click **Load Unpacked** → Select `extension/` folder
3. Click the 🎯 icon → **Dev Login** (for local testing)

### Dashboard
```bash
cd dashboard
npm install && npm run dev
```

## 🧠 Context-Aware Classification

AdaptiFocus uses title-based keyword analysis to override domain classification:

| Scenario | Traditional Blocker | AdaptiFocus |
|---|---|---|
| YouTube → MIT Lecture | ❌ Blocked | ✅ Study |
| YouTube → Cat Videos | ❌ Blocked | ❌ Distraction |
| Reddit → Python Tutorial | ❌ Blocked | ✅ Study |
| Reddit → Memes | ❌ Blocked | ❌ Distraction |

## 🧪 Experiment Design

Users are randomly assigned to one of three groups:
- **Adaptive** — Full AI-powered graduated interventions
- **Static Block** — Simple domain blocking
- **Control** — Tracking only, no interventions

## 🔐 Authentication

- **Production**: Google Sign-In via `chrome.identity`
- **Local Dev**: Dev Login endpoint (`/auth/dev-login`)
- Session management via JWT

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy |
| ML | scikit-learn (Random Forest, 94.3% CV accuracy) |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Extension | Chrome Manifest V3, vanilla JS |
| Dashboard | React, Vite, Recharts |
| Auth | Google OAuth + JWT |
| Deployment | Railway, Docker |

## 📊 ML Performance

Trained on Kaggle browsing behavior dataset:
- **Model**: Random Forest (100 trees, max depth 10)
- **Cross-Validation Accuracy**: 94.3%
- **Features**: 10 behavioral features (distraction ratio, session patterns, etc.)

## 📄 License

MIT

## 🧭 Product and architecture plan

- [Notion-ready product and delivery plan](docs/notion_plan.md)
- [Current system, target architecture, and startup strategy](docs/current_system_and_startup_strategy.md)

## 👤 Author

Banuka Rajapaksha
