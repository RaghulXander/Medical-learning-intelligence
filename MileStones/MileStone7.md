# Milestone 7 — Core Identity, Guest Funnel, Adaptive Onboarding & Common Assessment Backend

## 1. Executive Summary & Milestone Objective

### Objective
Build the **enterprise-grade identity, authentication, guest conversion funnel, adaptive medical onboarding, and core backend service layer** for the DocEdge Medical Exam Platform.

Milestone 7 establishes the **secure, resilient backend infrastructure and common platform services** that power both the Web platform (`apps/web`) and the upcoming Native Mobile App (`apps/student-native`, detailed in [MileStones/MileStone8.md](file:///r:/Repositories/medical-learning-intelligence/MileStones/MileStone8.md)).

---

## 2. Authentication & Identity Architecture

```
                                AUTHENTICATION GATEWAY
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
         [ Google Sign-In ]                              [ Direct Email / Pass ]
    (OAuth2 / OIDC / 1-Tap)                         (Native Form + Entropy Meter)
                  │                                               │
                  ▼                                               ▼
       Verify Google ID Token                           Verify Argon2id / bcrypt
                  │                                               │
                  ▼                                               ▼
         User Exists in DB?                              User Exists in DB?
           ├── YES ──► Issue Session                       ├── YES ──► Issue Session
           └── NO  ──► Provision User                      └── NO  ──► Register User
                  │                                               │
                  ▼                                               ▼
       [ Optional Password Setup ]                     [ Adaptive Onboarding ]
     (Custom or Auto-Strong Pass)                    (Target Exam, Stage, College)
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                               [ Issue JWT Keypair ]
                        ├── Web: Secure HttpOnly Cookie
                        └── Mobile: Bearer Auth Token
                                          │
                                          ▼
                               [ Check Guest Session ]
                                          │
                          ┌───────────────┴───────────────┐
                          ▼                               ▼
                 Has Guest Attempt?               No Guest Attempt
                          │                               │
                          ▼                               ▼
             Merge Guest Data into Account      Direct to Personalized Hub
```

### 2.1 Supported Auth Rails
1. **Google Sign-In (OAuth2 / OIDC / Google One-Tap)**:
   - Client sends Google ID Token to backend `POST /api/auth/google`.
   - Backend validates cryptographic signature against Google public certs via `google-auth`.
   - Automatically links `google_id` and avatar to existing email or provisions new user.
2. **Post-Google Strong Password Generation / Custom Setup**:
   - For users signing in via Google, provide a seamless option to:
     * **1-Click Auto-Generate**: Generates a 20-character high-entropy cryptographic password (e.g. `kX8#mP9$qL2@pZ4!`) and hashes it on the backend for multi-platform/offline access.
     * **Set Custom Password**: Verified by client/server password entropy calculation.
     * **Skip**: Remain pure Google Sign-In.
3. **Direct Email & Password Authentication**:
   - Hashed using **`Argon2id`** or **`bcrypt`** (work factor 12).
   - Live client-side password entropy meter:
     * 🔴 Weak (<40 bits)
     * 🟡 Moderate (40–65 bits)
     * 🟢 Strong (65–80 bits)
     * 🟣 Bulletproof (>80 bits)
   - "Suggest Strong Password" tool built directly into the UI.

### 2.2 Multi-Platform Session & Token Rotation Strategy
* **Access Token**: Short-lived JWT (15 minutes), RS256/HS256 signed.
* **Refresh Token**: Long-lived opaque token (30 days), stored as a SHA-256 hash in `user_sessions`.
* **Transport**:
  * **Next.js Web (`apps/web`)**: `HttpOnly`, `SameSite=Lax`, `Secure` cookie.
  * **Native App (`apps/student-native`)**: Encrypted storage (Expo SecureStore) passed via `Authorization: Bearer <token>`.
* **Token Rotation**: Each call to `/api/auth/refresh` revokes the old refresh token and issues a new pair. If a revoked refresh token is reused, all sessions for that user are immediately invalidated (anti-theft detection).
* **Multi-Device Session Management**:
  * View all active logins with Device Name, OS, IP Address, and Last Active time.
  * 1-Click **"Logout of all other devices"** (`POST /api/auth/logout-all`).

### 2.3 Server-Side Role-Based Access Control (RBAC)
- Strict endpoint decorators enforcing minimum role hierarchy:
  $$\text{ADMIN} \succ \text{REVIEWER} \succ \text{EDUCATOR} \succ \text{STUDENT (USER)}$$
- Granular permission scopes for question editing, curriculum modification, and audit log inspection.

---

## 3. Guest Diagnostic Funnel & Anonymous-to-Registered Account Merge

### 3.1 The Conversion Funnel
```
Landing Page ──► "Try 5 Questions" (No Login Required) ──► 5-Question Rapid Diagnostic 
             ──► Diagnostic Score & Robbins Evidence Preview ──► Sign in with Google / Email 
             ──► Merge Guest Attempt & Topic Mastery ──► Personalized Dashboard
```

### 3.2 Guest Session Engine
1. When an unauthenticated visitor starts the diagnostic quiz, the backend issues an anonymous `guest_session_id` (UUID stored in temporary cookie or localStorage).
2. The guest takes the 5-question diagnostic (conducted via Milestone 5's Assessment Engine).
3. Attempt, answers, time spent, and question-level metrics are persisted with `guest_session_id`.
4. When the user completes authentication (Google Sign-In or Email Registration), the client calls:
   `POST /api/auth/merge-guest` with `{ "guest_session_id": "..." }`.
5. **Merge Execution**:
   - Migrates `AssessmentAttempt` and `AttemptQuestion` records to the new `user_id`.
   - Populates `UserQuestionHistory` and updates `UserMastery` with Laplace-smoothed accuracy for the questions answered.
   - Marks the `GuestSession` as `merged_at = NOW()`.
   - **Zero Lost Progress**: The student's diagnostic baseline immediately informs Milestone 6's Question Selector!

---

## 4. Adaptive Medical Learner Onboarding

Instead of an exhausting 10-screen medical survey, the onboarding wizard is progressive and adaptive (max 3 concise steps):

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Target Examination                                                 │
│  ├── [ ] NEET-SS Oncopathology (DM / DrNB)                                  │
│  ├── [ ] NEET-PG / INI-CET Pathology                                        │
│  ├── [ ] MD / DNB Pathology Exit Exam                                       │
│  ├── [ ] MBBS 2nd Professional Pathology                                     │
│  └── [ ] General / Other Medical Speciality                                  │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼ (Adaptive Branch)
┌──────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Target Attempt & Timeline                                          │
│  ├── Target Exam Year/Session (e.g., "November 2026", "May 2027")           │
│  └── Primary Subspecialty Focus (Oncopath, Hemato, Molecular IHC, GI, Lung) │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Professional Stage & Medical College                                │
│  ├── Stage: MBBS Student | Junior Resident (JR) | Senior Resident (SR) |    │
│  │          Fellow | Attending / Consultant                                  │
│  └── Institution: (Autocomplete search across Medical Colleges & Hospitals)  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Common Assessment & Student Core Backend Services

Milestone 7 provides the robust backend APIs for all student features (to be visualized natively in Milestone 8):

### 5.1 Daily High-Yield Quiz Service (`/api/assessments/daily-quiz`)
* Daily 5-question curated or auto-selected high-yield vignette set.
* Changes every 24 hours at midnight UTC.
* Computes cohort percentile ranking and streak counters.

### 5.2 "Continue Learning" & Spaced Repetition API (`/api/assessments/continue-learning`)
* Returns the user's unfinished assessment attempts (resumable with 1 click).
* Generates real-time recommendations for next 3 priority topics based on Milestone 6 weak-topic mastery scores.

### 5.3 Smart Mistake Review API (`/api/assessments/mistake-review`)
* Aggregates questions answered incorrectly from recent attempts.
* Filterable by:
  * Repeated errors (2+ wrong answers)
  * By Topic / Subtopic
  * By Bookmarked / Flagged questions
* Provides 1-click **"Launch Remediation Quiz"** testing identical learning objectives.

### 5.4 Exam Readiness Indicator Calculation (`/api/assessments/readiness`)
* Computes a weighted composite **Exam Readiness Score (0–100%)**:
  $$\text{Readiness} = 0.40 \times \text{Curriculum Coverage} + 0.35 \times \text{Smoothed Accuracy} + 0.15 \times \text{Recent Mock Average} + 0.10 \times \text{Pacing Consistency}$$

### 5.5 Network Resilience & Interrupted Exam Recovery API
* **Idempotent Draft Sync**: `POST /api/assessments/{attempt_id}/sync-answers` accepts batch answer payloads with client-side timestamps.
* Resolves conflict gracefully (latest client timestamp wins).
* Allows seamless transition between devices (start on mobile webview, resume on desktop).

---

## 6. Security, Privacy & Admin Audit Logging

1. **Authentication Rate Limiting**:
   - Max 5 failed login attempts per IP/Email per 15 minutes before exponential lockout.
2. **Admin Audit Trail (`admin_audit_logs`)**:
   - Records every administrative modification (question edits, status changes, user role upgrades, curriculum re-indexing).
   - Captures `admin_user_id`, `target_entity_type`, `target_entity_id`, `action`, `diff_snapshot`, `ip_address`, `created_at`.
3. **Privacy & GDPR Compliance**:
   - **Data Export**: `GET /api/users/me/export` (downloads complete learner history, attempts, and mastery data as JSON).
   - **Account Deletion**: `POST /api/users/me/delete-account` (anonymizes medical attempts for research/analytics integrity while purging PII, email, and password hashes).

---

## 7. Database Schema Specifications

```sql
-- 1. Users Table Additions
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(100) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS target_exam VARCHAR(50) DEFAULT 'NEET_SS';
ALTER TABLE users ADD COLUMN IF NOT EXISTS target_year INT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS medical_college VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS residency_stage VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS primary_speciality VARCHAR(100) DEFAULT 'Pathology';
ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak INT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS longest_streak INT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_date DATE;

-- 2. Guest Sessions Table
CREATE TABLE IF NOT EXISTS guest_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_token VARCHAR(64) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    converted_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    merged_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_guest_sessions_token ON guest_sessions(session_token);

-- 3. User Sessions Table (Refresh Tokens & Device Audit)
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(64) NOT NULL UNIQUE,
    user_agent TEXT,
    ip_address VARCHAR(45),
    device_name VARCHAR(100),
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(refresh_token_hash);

-- 4. Auth & Admin Audit Logs
CREATE TABLE IF NOT EXISTS auth_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    changes JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_admin ON admin_audit_logs(admin_id);
```

---

## 8. API Endpoints Specification

### Authentication & Identity
* `POST /api/auth/google` — Verifies Google ID Token, provisions/links account, returns JWT & HttpOnly cookie.
* `POST /api/auth/register` — Native email + password registration with profile.
* `POST /api/auth/login` — Native email + password login with brute-force rate limiter.
* `POST /api/auth/set-password` — Set custom or auto-generated strong password.
* `POST /api/auth/generate-password` — Generate cryptographically secure password string.
* `POST /api/auth/refresh` — Rotates refresh token & issues new access JWT.
* `POST /api/auth/logout` — Revokes session & clears cookie.
* `POST /api/auth/logout-all` — Revokes all active sessions for user.
* `GET /api/auth/me` — Returns current user profile, target exams, and roles.
* `PATCH /api/auth/profile` — Updates adaptive medical onboarding preferences.
* `POST /api/auth/merge-guest` — Migrates guest diagnostic attempts to authenticated user.

### Common Student & Assessment Services
* `GET /api/assessments/daily-quiz` — Fetches today's high-yield 5-question daily quiz.
* `GET /api/assessments/continue-learning` — Returns active unfinished attempts & top weak-topic recommendations.
* `GET /api/assessments/readiness` — Calculates current exam readiness index (0–100%).
* `GET /api/assessments/mistake-review` — Returns filtered mistake questions with Robbins citations.
* `POST /api/assessments/{attempt_id}/sync-answers` — Resilient batch draft answer synchronization.

---

## 9. Acceptance Criteria

> [!NOTE]
> **Status: 100% COMPLETED & FULLY VERIFIED**  
> All 12 criteria verified via 59 automated tests in `tests/test_auth_and_student_services.py`, `tests/test_question_selection.py`, and `tests/test_assessment_engine.py`.

* [x] Google Sign-In validates token and links or creates user account (`test_google_auth_creates_new_user`, `test_google_auth_links_existing_user`).
* [x] Post-Google password setup allows custom or auto-generated cryptographic password (`test_generate_crypto_password`).
* [x] Direct email/password registration and login works with secure PBKDF2/bcrypt hashing (`test_email_password_registration_and_login`).
* [x] Password entropy scoring accurately classifies weak, moderate, strong, and very strong tiers (`test_password_entropy_evaluation`).
* [x] Guest diagnostic quiz runs without prior authentication (`test_guest_session_creation`).
* [x] `merge-guest` seamlessly transfers attempt history and mastery into the user's account upon login (`test_guest_session_merge_after_auth`).
* [x] Adaptive onboarding saves target exam, stage, and institution to `User` (`test_adaptive_onboarding_update`).
* [x] Daily quiz API produces 24h rotating quiz sets and updates streak (`test_daily_quiz_and_streak_tracking`).
* [x] Mistake review API surfaces repeated errors and generates targeted remediation (`test_mistake_review_and_remediation`).
* [x] Exam readiness index computes weighted composite score from coverage, accuracy, and mock consistency (`test_exam_readiness_calculation`).
* [x] Multi-device session management allows viewing, rotating, and revoking active sessions (`test_refresh_token_rotation`, `test_logout_and_logout_all`).
* [x] Idempotent draft answer batch synchronization (`test_draft_answer_sync`).

---

## 10. Verification & Test Suite Execution

```bash
python -m unittest discover tests
```
**Results**:
- `Ran 59 tests in 6.748s — OK (100% Green)`
- Full test coverage across:
  * Google OAuth2 verification & provisioning
  * Direct email/password registration & entropy enforcement
  * Strong cryptographic password generator
  * Failed login brute-force rate limiter
  * Refresh token rotation & remote logout-all
  * Guest session creation & diagnostic attempt persistence
  * Guest-to-user account merge & mastery backfill
  * Adaptive onboarding updates
  * Daily quiz & streak engine
  * Continue learning & weak topic recommendations
  * Exam readiness index calculation
  * Smart mistake review & remediation blueprint
  * Idempotent draft answer synchronization

```bash
bun run typecheck
```
**Results**:
- `@medical/shared`: 0 errors
- `@medical/api-client`: 0 errors
- `apps/student-native`: 0 errors
- `apps/web`: 0 errors
