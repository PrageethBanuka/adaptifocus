# AdaptiFocus — Publishing Roadmap & Improvements

## 🎯 How to Publish This Research

### Target Venues (Ranked by Difficulty)

| Venue | Type | Deadline Style | Difficulty | Best For |
|-------|------|---------------|------------|----------|
| **University Symposium** | Local | Always open | ⭐ Easy | First publication, poster |
| **IEEE TENCON** | Regional | Annual (Jun-Aug) | ⭐⭐ Medium | Regional exposure |
| **IEEE ICIIS** | Regional | Annual | ⭐⭐ Medium | Sri Lanka/South Asia |
| **ACM CHI Late-Breaking Work** | Intl | Annual (Sep) | ⭐⭐⭐ Hard | Top HCI venue, 4 pages |
| **IEEE ICSE SRC** | Intl | Annual (Oct) | ⭐⭐⭐ Hard | Student Research Competition |
| **ACM UIST** | Intl | Annual (Apr) | ⭐⭐⭐⭐ Very Hard | Top UI/systems venue |

### Recommended Strategy
1. **Week 1-4**: Submit to **university symposium** (immediate credibility)
2. **Week 4-8**: Submit to **IEEE TENCON / ICIIS** (regional conference)
3. **Week 8-12**: Submit extended version to **ACM CHI LBW** (top venue)

---

## 📊 Real Datasets to Use

### 1. Browser History Dataset (Firefox) — ⭐ Best Fit
- **Source**: [Kaggle](https://www.kaggle.com/datasets/saloni1712/browser-history)
- **Size**: ~5,000+ URLs with timestamps, click counts, frecency
- **How to use**:
  ```bash
  cd backend
  source venv/bin/activate
  python -m ml.real_dataset_loader --source browser_history --path data/browser_history.csv
  ```

### 2. Mental Health & Digital Behavior Dataset
- **Source**: [Kaggle](https://www.kaggle.com/datasets/waqi786/mental-health-and-digital-behavior-2020-2024)
- **Features**: Screen time, app switches, social media time, focus scores
- **How to use**:
  ```bash
  python -m ml.real_dataset_loader --source digital_behavior --path data/mental_health.csv
  ```

### 3. Website Traffic Dataset
- **Source**: [Kaggle](https://www.kaggle.com/datasets/anthonytherrien/website-traffic)
- **Features**: Session duration, bounce rate, page views
- **How to use**:
  ```bash
  python -m ml.real_dataset_loader --source website_traffic --path data/website_traffic.csv
  ```

### 4. Collect Your Own (Batch Testing) — ⭐⭐ Most Valuable
- Deploy extension to your batch mates
- Collect 2-4 weeks of real browsing data
- This is the **strongest evidence** for your paper

---

## 🧪 Batch Testing Plan

### Deployment Steps
1. **Package the extension** as a `.crx` or share via zip
2. **Set up a cloud backend** (free tier):
   - Railway.app (free tier, FastAPI)
   - PythonAnywhere (free, limited)
   - Render.com (free tier with sleep)
3. **Recruit 15-30 participants** from your batch
4. **2-week data collection period**
5. **A/B testing**: Control (no intervention) vs AdaptiFocus

### Study Design for Paper
```
Group A (Control):     Extension with tracking only, no interventions
Group B (Static):      Extension with basic blocking (like existing tools)
Group C (AdaptiFocus): Full graduated intervention system
```

### IRB / Ethics
- Get **informed consent** from all participants
- **Anonymize** all browsing data (hash URLs, strip personal info)
- Provide data **opt-out** mechanism
- Check if your university requires ethics board approval

---

## 🔧 Improvements Needed Before Publishing

### Critical (Must Have)
1. **User Authentication** — Multi-user support for batch testing
2. **Data Anonymization** — Hash URLs, remove personal data before analysis
3. **HTTPS Backend** — Secure data transmission for deployed version
4. **Consent Flow** — Extension onboarding with clear data usage policy
5. **Pre/Post Survey** — SUS questionnaire integration

### Important (Should Have)
6. **A/B Testing Framework** — Toggle intervention modes per user
7. **Export Data** — Participants can export/delete their data (GDPR-friendly)
8. **Crash Recovery** — Handle extension errors gracefully
9. **Configurable Categories** — Let users mark domains as study/distraction
10. **Offline Mode** — Queue events when backend is unavailable

### Nice to Have
11. **LLM-based Classification** — Use Gemini/OpenAI for smarter context analysis
12. **Mobile Extension** — Firefox Android support
13. **Pomodoro Integration** — Built-in study timer
14. **Social Features** — Batch leaderboard (anonymous focus scores)
15. **Adaptive ML Model** — Online learning that improves over time

### Paper Strengthening
16. **Baseline Comparison** — Compare against Cold Turkey, LeechBlock
17. **Statistical Tests** — Paired t-tests, Wilcoxon signed-rank for results
18. **Effect Size** — Report Cohen's d alongside p-values
19. **Qualitative Data** — Post-study interviews (3-5 participants)
20. **Threat to Validity** — Address confounders in the paper

---

## 📝 Paper Checklist

- [ ] Abstract with concrete metrics (X% improvement)
- [ ] Lit review covering at least 15 papers
- [ ] Clear system architecture diagram
- [ ] Feature engineering table with all 20 features
- [ ] User study with ≥15 participants
- [ ] Results with statistical significance
- [ ] Comparison with at least 1 baseline
- [ ] Limitations and future work section
- [ ] All references in IEEE/ACM format
