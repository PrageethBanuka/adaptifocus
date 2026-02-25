# Research Proposal: AdaptiFocus

## Title
**AdaptiFocus: AI-Driven Adaptive Attention Management for Academic Digital Wellbeing**

## Problem Statement
University students lose 2-4 hours daily to digital distractions during study sessions. Current solutions employ binary blocking strategies that lack personalization, context awareness, and graduated responses — leading to user frustration and tool abandonment.

## Research Questions
1. **RQ1**: Can a multi-agent system that learns individual distraction patterns deliver more effective interventions than static blocking?
2. **RQ2**: Does a graduated intervention strategy (nudge → warn → soft-block → hard-block) improve study session focus compared to binary blocking?
3. **RQ3**: How does context-aware intervention (considering study topic, session state, and browsing trajectory) affect intervention acceptance rates?

## Methodology
- **System development**: Multi-agent pipeline with Pattern, Context, and Intervention agents
- **Feature engineering**: 20 behavioral features extracted from browsing events
- **ML classification**: Random Forest classifier for browsing pattern recognition
- **Graduated interventions**: 4-level escalation with pattern-adjusted thresholds
- **Evaluation**: User study with N participants over M weeks
  - Conditions: No tool (baseline) vs. Static blocker vs. AdaptiFocus
  - Metrics: Focus time ratio, distraction episodes, intervention effectiveness, SUS score

## Expected Outcomes
- Significant improvement in study session focus time
- Higher user acceptance of graduated interventions vs. binary blocking
- Actionable pattern insights (e.g., vulnerable hours, distraction chains)

## Timeline
16 weeks total — see implementation plan for detailed breakdown.

## Target Venues
- IEEE ICSE Student Research Competition
- ACM CHI Student Research Competition
- IEEE TENCON
- Local university research symposiums
