# Milestone 7a: UI Enrichment, Missing Flows & Student Hub Experience

## 1. Executive Summary

Milestone 7a enriches the web user interface (`apps/web`) with **all missing screens, flows, and interaction models** defined in Milestone 7. This bridges the backend authentication, guest merge, adaptive onboarding, daily quiz, and mistake review services into a **modern, state-of-the-art medical education experience**.

---

## 2. Screens & Flows Implemented

```
                                    LANDING PAGE
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
     [ "Try 5-Q Diagnostic" ]                          [ Direct Join / Sign In ]
     (Anonymous Guest Session)                         (Google / Email + Pass)
                 │                                               │
                 ▼                                               ▼
       5-Question Rapid Mock                                [ AuthModal ]
                 │                                   ├── Live Entropy Meter
                 ▼                                   ├── 1-Click Strong Pass
        Scorecard & Citations                        └── Google 1-Tap
                 │                                               │
                 ▼                                               ▼
    [ Guest Conversion Banner ]                       [ 3-Step Onboarding ]
  "Sign In to Save & Track Mastery"                  ├── Target Exam
                 │                                   ├── Target Year & Focus
                 ▼                                   └── Residency Stage & College
     Merge Guest History into DB                                 │
                 │                                               ▼
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                            [ Enriched Student Hub ]
                     ├── Exam Target & Countdown Banner
                     ├── Daily High-Yield Quiz Card (🔥 Streak)
                     ├── Circular Exam Readiness Dial (0–100%)
                     ├── In-Progress Attempt Resumption
                     ├── Weak Topic Pulse (1-Click Drill)
                     └── Smart Mistake Vault & Citations
```

---

## 3. UI Component Architecture

### A. Authentication & Identity Subsystem
1. **`apps/web/src/lib/auth-context.tsx`**:
   - Manages user profile, tokens (localStorage + isomorphic header injection), anonymous `guest_session_token`, and automatic guest merge trigger upon authentication.
2. **`apps/web/src/components/auth/auth-modal.tsx`**:
   - Modern glassmorphic dialog with **"Continue with Google"** integration.
   - Live **Password Entropy Meter** displaying strength tier (`WEAK`, `MODERATE`, `STRONG`, `VERY_STRONG`), bits of Shannon entropy, and dynamic color progression.
   - **1-Click "Suggest Strong Password"** generating 20-character crypto passwords and copying to clipboard with toast notification.
   - Post-Google prompt offering optional password setup.
3. **Dedicated Pages**:
   - `apps/web/src/app/login/page.tsx`
   - `apps/web/src/app/signup/page.tsx`
4. **`apps/web/src/components/navbar.tsx`**:
   - Dynamically adapts: shows "Sign In" and "Join Free" when logged out; displays user avatar, active streak badge (`🔥 4`), target exam badge (`NEET-SS`), and user dropdown when logged in.

---

### B. Guest Diagnostic Funnel
1. **`apps/web/src/app/page.tsx`**:
   - Added prominent **"Try 5-Question Diagnostic"** Hero CTA (zero sign-in required).
   - Generates guest session transparently in background and launches the 5-question test.
2. **`apps/web/src/app/student/results/[attemptId]/page.tsx`**:
   - Added **Guest Conversion Banner**: *"Sign in with Google or Email to save your diagnostic score, track topic mastery, and unlock personalized weak-topic remediation drills!"*
   - Merges attempt and answers into user profile immediately upon sign-in.

---

### C. 3-Step Adaptive Medical Onboarding Wizard
1. **`apps/web/src/app/onboarding/page.tsx`**:
   - **Step 1: Specialization Target**: NEET-SS Oncopathology, NEET-PG / INI-CET, MD/DNB Pathology Exit, MBBS 2nd Prof.
   - **Step 2: Timeline & Focus**: Target session year (2026, 2027, 2028) & subspecialty focus (Oncopathology, Hematopathology, Molecular Genetics, etc.).
   - **Step 3: Background**: Designation (JR, SR, Fellow, MBBS) & Medical College / Hospital.
   - Automatically redirects to the personalized Student Hub upon completion.

---

### D. Enriched Student Hub (`apps/web/src/app/student/page.tsx`)
1. **Exam Target & Countdown Banner**:
   - Dynamic greeting (*"Welcome back, Dr. Raghul"*) with active target exam badge and 1-click settings.
2. **Daily High-Yield Quiz Card**:
   - Displays today's rotating 5-question quiz, streak badge (`🔥 5-Day Streak`), and timer.
3. **Circular Exam Readiness Gauge**:
   - SVG circular progress arc showing composite score ($0\text{--}100\%$) and rating (`EXCELLENT`, `GOOD`, `NEEDS_FOCUS`) with curriculum coverage and Laplace accuracy breakdown.
4. **Continue Learning & In-Progress Attempts Carousel**:
   - Displays active in-progress mock exams with answered count and 1-click "Resume Mock Test" button.
5. **Weak Topic Pulse & Remediation Launcher**:
   - Directly displays top 3 weak areas from Milestone 6's `UserMastery` with instant 1-click targeted drills.

---

### E. Smart Mistake Review Vault (`apps/web/src/app/student/review/page.tsx`)
1. **Error History & Spaced Remediation**:
   - Filter by "All Mistakes" vs "Repeated Errors (2+ times)".
   - Question cards showing user choice vs ground truth with checkmarks/crosses.
   - High-yield ground truth clinical rationale.
   - 1-Click **"Remediate Weak Spots"** button creating a targeted spaced remediation drill.

---

## 4. Verification & Type Safety

```bash
bun run typecheck
```
- `@medical/shared`: 0 errors
- `@medical/api-client`: 0 errors
- `student-native`: 0 errors
- `web`: 0 errors

```bash
python -m unittest discover tests
```
- `Ran 59 tests in 3.897s — OK (100% Green)`

---

## 5. Acceptance Criteria

* [x] Google Sign-In & Email/Password modal with live password entropy bar.
* [x] 1-Click "Suggest Strong Password" tool with clipboard copy.
* [x] Guest diagnostic test launch without login barrier.
* [x] Post-test guest conversion banner merging session data upon authentication.
* [x] 3-Step adaptive onboarding wizard (`/onboarding`).
* [x] Dynamic student dashboard with exam countdown, daily quiz card, and circular readiness dial.
* [x] In-progress mock exam resumption card.
* [x] High-yield weak topic pulse with 1-click drill generation.
* [x] Smart mistake review vault with ground truth explanations (`/student/review`).
* [x] Clean TypeScript build across all packages.
