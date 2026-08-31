# Milestone 8 — Mobile Student Application

## React Native / Expo Student Experience

---

# 1. Milestone Objective

Build the first production-oriented mobile application for the student-facing medical exam platform.

The mobile app should reuse the existing backend and assessment infrastructure from:

```text

M5 — Universal Assessment Engine

M6 — Intelligent Question Selection

M7 — Web Student Application

```

The mobile application is **another client**, not another backend.

```text

                       Backend

                          |

             +------------+------------+

             |                         |

          Next.js                  React Native

             |                         |

             v                         v

            Web                      Mobile

```

---

# 2. Primary Goal

A student should be able to install/open the app and:

```text

Open app

   ↓

Sign up / Login

   ↓

Onboarding

   ↓

Home

   ↓

Daily Quiz

   ↓

Take exam

   ↓

Submit

   ↓

Results

   ↓

Review explanations

```

The second major flow:

```text

Home

 ↓

Create Mock

 ↓

Choose exam

 ↓

Choose topic / random

 ↓

Choose difficulty

 ↓

Choose question count

 ↓

Start

 ↓

150-question mock

 ↓

Submit

 ↓

Results

```

---

# 3. Technology

Recommended:

```text

React Native

Expo

TypeScript

Expo Router

NativeWind or existing styling system

```

Use the selected React Native boilerplate as the foundation.

Recommended starting point:

**ixartz/React-Native-Boilerplate**

[React-Native-Boilerplate on GitHub](https://github.com/ixartz/React-Native-Boilerplate?utm_source=chatgpt.com)

It provides an Expo/React Native/TypeScript foundation with Expo Router and NativeWind, reducing the amount of infrastructure you need to create yourself.

---

# 4. Important Architecture Rule

Do NOT create separate business logic for mobile.

Bad:

```text

Web Question Selection

Mobile Question Selection

```

Good:

```text

                    Backend

                       |

                 M5 + M6 Logic

                       |

             +---------+---------+

             |                   |

            Web               Mobile

```

The mobile app only consumes APIs.

---

# 5. Repository Structure

Recommended:

```text

apps/

├── web/

│

└── mobile/

    ├── app/

    │   ├── _layout.tsx

    │   │

    │   ├── (auth)/

    │   │   ├── login.tsx

    │   │   ├── signup.tsx

    │   │   └── forgot-password.tsx

    │   │

    │   ├── onboarding/

    │   │   ├── welcome.tsx

    │   │   ├── education.tsx

    │   │   ├── exam.tsx

    │   │   ├── specialty.tsx

    │   │   └── goals.tsx

    │   │

    │   └── (app)/

    │       ├── _layout.tsx

    │       ├── home.tsx

    │       ├── quiz/

    │       ├── mock/

    │       ├── assessment/

    │       ├── results/

    │       ├── mastery/

    │       └── profile/

    │

    ├── components/

    │   ├── ui/

    │   ├── question/

    │   ├── assessment/

    │   ├── dashboard/

    │   └── charts/

    │

    ├── lib/

    │   ├── api/

    │   ├── auth/

    │   ├── storage/

    │   └── sync/

    │

    ├── hooks/

    ├── store/

    ├── types/

    └── constants/

```

---

# 6. Navigation

Recommended bottom navigation:

```text

┌────────────────────────────────────┐

│                                    │

│              CONTENT               │

│                                    │

├────────────────────────────────────┤

│  Home  │  Tests  │  Progress │ Me │

└────────────────────────────────────┘

```

Keep navigation small.

---

# 7. Main Tabs

## Home

```text

Today's goal

Daily quiz

Continue preparation

Weak topics

Recent results

```

## Tests

```text

Daily Quiz

Topic Test

Mock Test

Grand Test

```

## Progress

```text

Overall performance

Topic mastery

Recent performance

Weak areas

```

## Profile

```text

Account

Target exam

Specialty

Daily goal

Settings

Logout

```

---

# 8. Mobile Home Screen

The first screen should immediately answer:

> What should I do now?

Example:

```text

Good morning 👋

NEET-SS · Pathology

Today's Goal

12 / 20 questions

[ Continue Quiz ]

────────────────────

Focus Area

Hematopathology

48% mastery

[ Practice ]

────────────────────

Quick Start

[ Daily Quiz ]

[ Topic Test ]

[ Mock Test ]

```

---

# 9. Daily Quiz

The most important mobile interaction.

```text

Home

 ↓

Daily Quiz

 ↓

10 questions

 ↓

Question

 ↓

Select answer

 ↓

Next

 ↓

Result

```

The app should require minimal configuration.

---

# 10. Question Screen

Mobile question UI:

```text

Question 4 / 10

────────────────

Which of the following

is the most appropriate...

○ Option A

○ Option B

○ Option C

○ Option D

────────────────

[ Mark for Review ]

          [ Next ]

```

Requirements:

* large touch targets

* readable typography

* no tiny buttons

* comfortable spacing

* scrollable question stem

* fixed bottom action area where appropriate

---

# 11. Long Question Support

Medical questions can contain:

* long stems

* tables

* images

* special characters

* superscripts

* Greek letters

* pathology terminology

The question component must support rich content.

Do not assume:

```text

question.length < 500 characters

```

---

# 12. Image Support

M8 should support question images even if image-based questions are not the primary MVP.

Examples:

```text

Histopathology image

Cytology image

Radiology image

Diagram

Flow cytometry plot

```

Question schema should eventually support:

```json

{

  "media": [

    {

      "type": "IMAGE",

      "url": "...",

      "caption": "..."

    }

  ]

}

```

---

# 13. Answer Selection

When the user selects an option:

```text

selected_answer

```

should immediately update local state.

Server synchronization can happen asynchronously.

Do not require a network round-trip just to visually select an option.

---

# 14. Answer Persistence

Use:

```text

local state

+

server persistence

```

Example:

```text

User selects B

    ↓

Save locally

    ↓

POST answer

    ↓

Server confirms

```

If POST fails:

```text

retry queue

```

---

# 15. Network Resilience

M8 should provide basic resilience.

States:

```text

ONLINE

OFFLINE

SYNCING

SYNC_ERROR

```

Example:

```text

Offline

Your answer is saved on this device

and will sync when connection returns.

```

Do not attempt full offline exam support in the first implementation.

---

# 16. Assessment Timer

Use server timestamps.

Mobile:

```text

display remaining time

```

Backend:

```text

authoritative end time

```

On app restart:

```text

GET attempt

     ↓

server end_time

     ↓

recalculate remaining time

```

Never trust local device time as the authority.

---

# 17. App Interruption

Mobile users can:

* receive a call

* lock the screen

* switch apps

* lose network

* terminate the application

The assessment must survive these events where possible.

On reopening:

```text

GET active attempt

      ↓

restore state

```

---

# 18. Mock Builder

The mobile mock builder should be deliberately simple.

Screen:

```text

Create Mock

Exam

[ NEET-SS ▼ ]

Specialty

[ Pathology ▼ ]

Questions

○ 10

○ 20

○ 50

○ 100

○ 150

Difficulty

☑ Medium

☑ Hard

Mode

○ Practice

● Mock

[ Create Mock ]

```

Advanced filters can be added later.

---

# 19. Topic Selection

Use hierarchical navigation:

```text

Pathology

    ↓

Hematopathology

    ↓

Lymphoid Neoplasms

```

Avoid displaying hundreds of raw MedMCQA topic labels.

The app must consume the canonical curriculum hierarchy.

---

# 20. Results Screen

Mobile results:

```text

             72%

          72 / 100

Correct        72

Incorrect      23

Skipped         5

Time           84 min

────────────────────

Weak Areas

Hematopathology     42%

Molecular Pathology 37%

[ Review Answers ]

[ Practice Weak Areas ]

```

---

# 21. Review Screen

Question-by-question review:

```text

Q37

Your answer

B ❌

Correct answer

D ✓

Explanation

...

Topic

Hematopathology

[ Report Question ]

```

Swipe/navigation can be added later.

---

# 22. Progress Screen

Initial version:

```text

Overall Accuracy

72%

Questions

1,284

Topics

Hematopathology      48%

Breast Pathology     81%

GIT Pathology        65%

Molecular Pathology  37%

```

Don't build sophisticated charts initially.

Clear numbers are more useful.

---

# 23. Weak Area Recommendations

Progress screen should eventually expose:

```text

Recommended for you

1. Molecular Pathology

   37% mastery

2. Hematopathology

   48% mastery

3. GIT Pathology

   65% mastery

```

Button:

```text

[ Practice ]

```

This invokes M6.

---

# 24. Authentication

The mobile app should use the same backend authentication system as web.

```text

Mobile

   ↓

Authentication API

   ↓

User

```

Do not create separate mobile users.

---

# 25. Secure Token Storage

Tokens/session credentials must use secure mobile storage.

Use platform-secure storage rather than:

```text

AsyncStorage

```

for long-lived sensitive credentials.

The exact authentication mechanism depends on the backend authentication implementation.

---

# 26. API Client

Same conceptual API as web:

```text

lib/api/

├── client.ts

├── auth.ts

├── assessments.ts

├── attempts.ts

├── questions.ts

├── mastery.ts

└── users.ts

```

---

# 27. Shared API Types

If the backend is FastAPI:

```text

OpenAPI

   ↓

generated TypeScript types

   ↓

Web

Mobile

```

This prevents:

```text

Web thinks:

question.correctOption

Mobile thinks:

question.correct_answer

```

Use one contract.

---

# 28. State Management

Keep global state small.

Potential state:

```text

auth

user

activeAssessment

assessmentAnswers

networkStatus

```

Do not put every API response into global state.

Server data should remain server data.

---

# 29. Local Persistence

Persist only what is necessary.

Examples:

```text

auth/session state

onboarding progress

active attempt

unsynced answers

UI preferences

```

Do not store the entire question bank locally.

---

# 30. Push Notifications

Optional foundation only.

Do not build a notification backend in M8.

Leave architecture ready for:

```text

Daily Quiz reminder

Exam reminder

Streak reminder

```

This can become a future milestone.

---

# 31. Deep Links

Prepare the app for future links:

```text

medexam://quiz/123

medexam://assessment/123

medexam://question/123

```

This is useful later for notifications and web-to-app navigation.

---

# 32. Error Handling

Every API operation must have:

```text

loading

success

error

retry

```

Example:

```text

Unable to load today's quiz.

[ Try Again ]

```

Never leave a blank screen.

---

# 33. Accessibility

Support:

* large touch targets

* readable font sizes

* screen-reader labels

* sufficient contrast

* dynamic text where practical

Medical exam apps involve long reading sessions, so readability is more important than visual novelty.

---

# 34. Performance

The question runner should:

* avoid unnecessary rerenders

* preload the next question where possible

* lazy-load large images

* avoid loading the entire exam payload unnecessarily

* cache curriculum data

* minimize network requests

For a 150-question mock, do not blindly download massive media assets for all 150 questions at once.

---

# 35. Assessment Data Strategy

Preferred:

```text

Create Assessment

       ↓

Receive assessment metadata

       ↓

Fetch question pages / chunks

       ↓

Answer

       ↓

Persist answer

```

Potential future optimization:

```text

Question 1–10

Question 11–20

Question 21–30

...

```

This becomes important if questions contain images.

---

# 36. Mobile Security

The app must never trust client-side:

```text

score

correct answer

marks

assessment completion

```

The backend remains authoritative.

---

# 37. Analytics Events

M8 should begin collecting product analytics events.

Minimum:

```text

APP_OPENED

LOGIN_COMPLETED

ONBOARDING_COMPLETED

QUIZ_STARTED

QUESTION_VIEWED

ANSWER_SELECTED

QUESTION_MARKED_REVIEW

ASSESSMENT_SUBMITTED

RESULT_VIEWED

EXPLANATION_VIEWED

QUESTION_REPORTED

```

Do not collect unnecessary personal data.

---

# 38. Important Learner Signals

These events should eventually support M6:

```text

question viewed

answer selected

answer changed

answer submitted

time spent

confidence

question reported

```

The actual authoritative learner history remains on the backend.

Analytics are supplementary.

---

# 39. App States

Support:

```text

FIRST_LAUNCH

AUTHENTICATED

ONBOARDING

READY

ACTIVE_ASSESSMENT

RESULT

OFFLINE

SYNCING

```

This prevents navigation logic from becoming scattered across screens.

---

# 40. Navigation Guard

Example:

```text

Not authenticated

    ↓

Login

Authenticated

    ↓

Onboarding incomplete

    ↓

Onboarding

Authenticated

+

Onboarding complete

    ↓

Home

```

Active assessment:

```text

Active attempt

    ↓

Resume assessment

```

Do not accidentally send a user to Home while an unfinished exam exists.

---

# 41. App Startup

Startup sequence:

```text

Launch

  ↓

Load session

  ↓

Check user

  ↓

Check onboarding

  ↓

Check active attempt

  ↓

Route

```

Example:

```text

No session

    → Login

Session + incomplete onboarding

    → Onboarding

Session + active attempt

    → Resume Exam

Session + no active attempt

    → Home

```

---

# 42. UI Design Principles

Target:

> Marrow-like usability, not Marrow-like feature count.

Focus on:

```text

Fast

Readable

Focused

Minimal

Medical

Professional

```

Avoid copying proprietary UI/branding.

Build your own design system and visual identity.

---

# 43. Recommended Screen Count for M8

Do not exceed approximately:

```text

Authentication

    3–4

Onboarding

    4–5

Main app

    4 tabs

Assessment

    4–5

Results

    2–3

```

The goal is a complete product loop, not a huge application.

---

# 44. Acceptance Criteria

## App

* [ ] Expo project runs

* [ ] Android development build runs

* [ ] iOS development path documented

* [ ] Navigation works

* [ ] Authentication works

* [ ] Session persistence works

* [ ] Onboarding works

* [ ] Home works

* [ ] Daily quiz works

* [ ] Topic test works

* [ ] Mock builder works

## Assessment

* [ ] 10-question exam works

* [ ] 20-question exam works

* [ ] 50-question exam works

* [ ] 100-question exam works

* [ ] 150-question exam works

* [ ] Timer works

* [ ] Answers persist

* [ ] App interruption handled

* [ ] Network failure handled

* [ ] Assessment resumes

* [ ] Submit works

* [ ] Results load

* [ ] Explanations load

## Student experience

* [ ] Dashboard shows daily goal

* [ ] Weak topics visible

* [ ] Recent results visible

* [ ] Recommended quiz visible

* [ ] Progress visible

* [ ] Question reporting works

## Security

* [ ] Tokens stored securely

* [ ] Correct answers not exposed

* [ ] Score calculated server-side

* [ ] User cannot access another user's assessment

* [ ] Role permissions enforced server-side

---

# 45. Definition of Done

M8 is complete when the following scenario works on a physical or emulator device:

```text

Install / Open App

       ↓

Create Account

       ↓

Complete Onboarding

       ↓

Home

       ↓

Start Daily Quiz

       ↓

Answer 10 Questions

       ↓

Submit

       ↓

See Score

       ↓

Review Explanations

       ↓

See Weak Topic

       ↓

Practice Weak Topic

       ↓

Create 20/50/150 Question Mock

       ↓

Take Mock

       ↓

Submit

       ↓

View Results

```

At this point the project is no longer merely a backend prototype.

It is a functioning medical exam preparation product.