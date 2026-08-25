# Milestone 8 — Marrow-Grade Student Native & Web Application Experience

## 1. Executive Summary & Design Philosophy

### Objective
Build a **state-of-the-art, high-performance, Marrow-grade Student Mobile and Web Application** for the DocEdge Medical Exam Platform.

Milestone 8 consumes the identity, assessment, and selection foundations built in Milestones 5–7 and transforms them into an **aesthetic, lightning-fast native mobile (`apps/student-native`) and responsive web (`apps/web`) interface**.

### Visual & UX Standards
* **Richer than Marrow & Prepladder**: Clean dark-mode aesthetics, subtle glassmorphism cards, medical slate palettes, fluid micro-animations, and zero visual clutter.
* **Designed for High-Pressure Medical Study**: Ultra-readable typography (Inter / Plus Jakarta Sans), high contrast ratios for clinical micrographs/vignettes, and distraction-free testing modes.
* **Shared Monorepo Architecture**:
  * Unified TypeScript contracts (`packages/shared`)
  * Common API Client (`packages/api-client`)
  * Identical exam simulation logic across Web and Native Mobile WebViews.

---

## 2. Shared Multi-Platform Architecture

```
                                DOCEDGE BACKEND API
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
      [ Next.js Web App ]                             [ React Native / Expo ]
        (`apps/web`)                                    (`apps/student-native`)
  ├── Desktop / Tablet Chrome & Safari            ├── iOS & Android Native Shell
  ├── Responsive Glassmorphism Canvas             ├── Native Biometric Login (FaceID)
  └── HttpOnly Cookie Auth                        └── Expo SecureStore + Auth Bearer
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                       [ Shared Packages & Design System ]
                        ├── `@medical/shared` (Types & Enums)
                        ├── `@medical/api-client` (Axios / Fetch Client)
                        └── `@medical/ui-tokens` (Color & Typography)
```

---

## 3. Personalized Student Hub (Home Dashboard)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  👋 Good Evening, Dr. Raghul | NEET-SS Oncopathology 2026 (182 Days Left)    │
└──────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────┬───────────────────────────────────────┐
│  ⚡ DAILY HIGH-YIELD QUIZ             │  🎯 EXAM READINESS INDEX              │
│  5 Pathology Vignettes for Today     │                                       │
│  [  Start Daily Quiz (5 Mins)  ]     │               [  78%  ]               │
│  🔥 5-Day Streak  |  👥 1,420 Doctors │  Coverage: 84% | Accuracy: 72%        │
└──────────────────────────────────────┴───────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────┐
│  🔄 CONTINUE LEARNING & RESUME ATTEMPTS                                      │
│  ├── [Resume] DM Oncopath Mock 1 (Q42/100) — 45m left                        │
│  └── [Resume] Breast IHC Practice (Q8/20)                                    │
└──────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────┬───────────────────────────────────────┐
│  ⚠️ WEAK TOPIC PULSE (M6 Remediation) │  📚 SMART MISTAKE VAULT               │
│  1. HER2 IHC Equivocal Scoring (28%) │  • 14 Unresolved Mistakes             │
│  2. Burkitt vs DLBCL IHC (40%)       │  • 3 Repeated Errors (High Priority)  │
│  [  Launch 10-Q Weak Topic Drill  ]  │  [  Start Mistake Review Drill  ]     │
└──────────────────────────────────────┴───────────────────────────────────────┘
```

### Key Hub Components:
1. **Target Exam Countdown Header**: Dynamic countdown to the student's target session (e.g. *NEET-SS November 2026*).
2. **Daily High-Yield Quiz Card**: 1-click access to today's 5 curated vignettes with streak counter and peer cohort participation metrics.
3. **Exam Readiness Dial**: Visual gauge combining topic coverage, Laplace-smoothed accuracy, and recent mock performance.
4. **Resumable Attempts Carousel**: 1-tap resumption for interrupted exam sessions with zero lost time or answers.
5. **Weak Topic Pulse**: Surfaces top 3 weak areas directly from Milestone 6's `UserMastery` table with 1-click instant remediation.
6. **Smart Mistake Vault**: Direct gateway to unmastered errors and bookmarked high-yield questions.

---

## 4. Practice & Mock Exam Configuration UX

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  NEW ASSESSMENT CONFIGURATION                                                │
│                                                                              │
│  Mode:  (•) Learning Mode    ( ) Practice Mode    ( ) Full Timed Mock        │
│                                                                              │
│  Subject / Topic Selection:                                                  │
│  ├── [x] Breast Pathology (Mastery: 74%)                                     │
│  │   ├── [x] Invasive Carcinoma Subtypes                                     │
│  │   └── [x] HER2 / Hormone Receptor Testing (Mastery: 32% ⚠️)               │
│  ├── [x] Hematopathology (Mastery: 68%)                                      │
│  └── [ ] Gastrointestinal Pathology                                          │
│                                                                              │
│  Question Pool:                                                              │
│  (•) All Eligible    ( ) Unattempted Only    ( ) Mistakes Only               │
│                                                                              │
│  Question Count:  [ 25 Questions ] (Slider: 5 — 100)                         │
│  Time Limit:      [ 30 Minutes ]   (Auto-calculated or Custom)                │
│                                                                              │
│  [  Preview Question Pool (142 Eligible)  ]   [  Start Assessment  ]         │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Native Real-Time Exam Runner & Prometric Palette

### 5.1 The Testing Canvas
* **Prometric 5-State Question Grid**:
  * ⚪ `NOT_VISITED`: Question not yet viewed.
  * 🔴 `NOT_ANSWERED`: Viewed but no option selected.
  * 🟢 `ANSWERED`: Option selected and confirmed.
  * 🟣 `MARKED_FOR_REVIEW`: Flagged for later review without answer.
  * 🟣🟢 `ANSWERED_AND_MARKED`: Answered but flagged for double check.
* **Distractor Strike-Through Tool**:
  * Tap the strike tool icon or right-click any distractor to cross out eliminated options with a clean strikethrough animation.
* **Font Zoom & Visual Comfort**:
  * Standard / Large / Extra Large typography modes.
  * High-contrast dark theme optimized for viewing high-magnification histopathology micrographs.
* **Resilient Autosave**:
  * Auto-syncs drafts to the backend every 10 seconds; persists locally to SQLite / AsyncStorage in case of network drops.

---

## 6. Post-Exam Analytics & Deep Review Canvas

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  SCORECARD: DM Oncopathology Mock #1                                         │
│                                                                              │
│  Score: 312 / 400 (+4, -1 NEET Scheme)      Percentile: 94.2%                │
│  Accuracy: 81.2% (78 Correct, 12 Incorrect, 10 Unanswered)                   │
│  Avg Time / Question: 42s (Speed Rating: Optimal ⚡)                          │
└──────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────┐
│  DETAILED QUESTION REVIEW (Question #14)                                      │
│                                                                              │
│  Stem: A 45-year-old female presents with a breast mass...                   │
│                                                                              │
│  (A) HER2 IHC 2+ requires reflex FISH testing              [ ✓ Correct ]     │
│  (B) HER2 IHC 1+ requires reflex FISH testing              [ ✗ Your Answer ] │
│                                                                              │
│  💡 Clinical Explanation & Rationale:                                        │
│  Per ASCO/CAP 2023 guidelines, IHC score 2+ is equivocal and mandates reflex │
│  in-situ hybridization (FISH) testing...                                     │
│                                                                              │
│  📖 Verified Medical Sources:                                                │
│  • Robbins & Cotran Pathologic Basis of Disease (10th Ed), Chapter 23, p. 1045│
│  • WHO Classification of Breast Tumours (5th Ed), p. 112                    │
│                                                                              │
│  ℹ️ Selection Transparency: Selected for [Weak Topic: HER2 IHC, Difficulty: Hard]│
│                                                                              │
│  [  🚩 Report Question Error  ]      [  ⚡ Practice 5 Similar Questions  ]    │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Native Mobile Shell (`apps/student-native`)

1. **Biometric Quick Login**:
   - Touch ID / Face ID unlock using Expo LocalAuthentication.
2. **Native Push Notifications**:
   - Daily High-Yield Quiz morning alert.
   - Spaced repetition streak reminder.
3. **Offline Diagnostic & Question Caching**:
   - Cache active test session locally so students can test seamlessly in hospital elevators or low-connectivity duty rooms.

---

## 8. Acceptance Criteria

* [ ] Student Home Hub renders Target Exam countdown, Daily Quiz, Exam Readiness dial, and Weak Topic pulse.
* [ ] Daily Quiz runs smoothly on both Web and Native Mobile with instant score calculation.
* [ ] Practice & Mock configuration UI allows intuitive topic filtering, question count sliders, and pool preview.
* [ ] Real-time Exam Runner supports Prometric 5-state grid, distractor strike-through, font zoom, and timer.
* [ ] Draft answers auto-sync every 10 seconds and survive network disconnects.
* [ ] Scorecard displays NEET +4/-1 score, accuracy percentage, time pacing, and topic breakdown.
* [ ] Detailed review displays explanations, verified Robbins/WHO textbook citations, and "Why am I seeing this question?" metadata.
* [ ] 1-Click "Launch Weak Topic Remediation" creates targeted quiz from test results.
* [ ] Native mobile shell (`apps/student-native`) supports biometric login and WebView bridge.
* [ ] UI conforms to high-performance dark/light glassmorphic medical theme.
