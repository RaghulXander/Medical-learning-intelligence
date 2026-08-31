# Deferred Google Play Listing

Google Play publication is currently de-prioritized. The active pilot channel is documented in [Android beta distribution](ANDROID_BETA_DISTRIBUTION.md). Retain this submission sheet for a later store launch; replace every `<production-domain>` placeholder and verify every declaration against that future release build before submission.

## Listing identity

| Field | Working value |
|---|---|
| App name | **DocEdge AI: Pathology Prep** |
| Default language | English |
| App or game | App |
| Category | Education |
| Pricing | Free during pilot; access to some content is manually managed |
| Ads | No ads, provided the release contains no advertising SDK |
| Target audience | Adults / medical learners; configure the Play age groups truthfully |
| Initial region | Decide before closed beta; India is the proposed first pilot region |
| Support email | `raghuljayan@gmail.com` |
| Website | `https://<production-domain>` |
| Privacy policy | `https://<production-domain>/privacy` |
| Support | `https://<production-domain>/support` |
| Account deletion | `https://<production-domain>/account-deletion` |

The proposed name is within Google Play’s 30-character limit. Confirm name availability in Play Console before treating it as final.

## Short description

> Pathology questions, mock exams and progress tracking for PG and SS learners.

This is within the 80-character limit.

## Full description

> DocEdge AI is an educational exam-preparation app for doctors and pathology learners preparing for postgraduate and superspecialty examinations.
>
> Build a consistent pathology study routine with focused questions, timed assessments, answer review and progress insights.
>
> Features available in the pilot:
>
> • Pathology-focused question practice
>
> • Daily learning and assessment activities
>
> • Configurable mock exams
>
> • Timed exam experience with answer navigation
>
> • Scores, answer review and readiness insights
>
> • Question reporting for incorrect, ambiguous or outdated content
>
> • Secure account access with password or Google sign-in
>
> Pilot access is limited. Some learning bundles are assigned manually by the DocEdge AI team during the beta.
>
> DocEdge AI is intended only for medical education and examination preparation. It does not provide diagnosis, treatment recommendations or patient-specific clinical advice. Educational content should be checked against current authoritative guidance. DocEdge AI is not affiliated with an examination board, university or textbook publisher.

The description deliberately avoids rankings, guaranteed outcomes, unsupported evidence claims, and clinical-use claims. Recheck it after features change.

## Closed-beta release notes

> First closed beta of DocEdge AI for Pathology preparation.
>
> • Password and Google sign-in
>
> • Guided learner onboarding
>
> • Pathology question practice and mock exams
>
> • Results, answer review and question reporting
>
> • Stability and feedback improvements for pilot testers

## Graphics checklist

| Asset | Play requirement / working plan | State |
|---|---|---|
| App icon | 512 × 512, 32-bit PNG, no more than 1 MB | Ready: `apps/mobile/store-assets/icon-512.png` |
| Feature graphic | 1024 × 500 JPEG or 24-bit PNG without alpha | Pending |
| Phone screenshots | Minimum two; JPEG or 24-bit PNG without alpha; each side 320–3840 px; longest side no more than twice the shortest | Pending; capture six genuine screens |
| Tablet screenshots | Add only after tablet UX is tested | Optional/pending |

Planned phone screenshot order:

1. Secure login.
2. Learner dashboard and daily learning.
3. Pathology assessment setup.
4. Timed exam runner.
5. Results and readiness.
6. Answer review and question reporting.

Capture the release build on a representative Android phone. Use seeded tester data, consistent time/status bars, and no real personal or patient data. Do not fabricate functionality in a marketing mock-up.

## App access for Google review

The app contains account-gated and entitlement-gated content, so Play Console must receive reusable reviewer instructions.

```text
Account type: Dedicated Google Play review account
Email: <store-review-email>
Password: <stored only in Play Console, never in Git>

Steps:
1. Open the app and choose email/password sign-in.
2. Enter the credentials above.
3. The account has completed onboarding and has the pilot Pathology bundle assigned.
4. Open Dashboard → Start assessment to reach the main gated experience.

No OTP, location restriction, staff approval, or expiring credential is required.
Contact raghuljayan@gmail.com if review access fails.
```

Test these instructions on a clean device before every submission.

## Data safety worksheet — draft only

The final declaration must be derived from the production application, backend, log retention, and all third-party SDKs.

| Data | Purpose | Questions to resolve before declaring |
|---|---|---|
| Name, email, user ID | Account management, authentication | Required or optional; retention; Google identity processing; deletion behavior |
| Education profile, college, exam preferences | App functionality and personalization | Required fields; user-edit controls; retention |
| Answers, attempts, scores, progress | App functionality and analytics | Admin visibility; retention; export/deletion |
| Question reports/support text | App functionality and support | Free-text risk; retention; access controls |
| Device/app/crash diagnostics | Stability and fraud/security if applicable | Exact crash SDK payload; persistent IDs; vendor role; opt-out |

Verify at minimum:

- whether data is collected, shared, or both under Google’s definitions;
- whether processing is ephemeral;
- whether data is required or optional;
- each permitted purpose;
- encryption in transit;
- account creation and deletion behavior;
- SDK and service-provider data handling.

Do not mark a field “not collected” merely because the app does not display it.

## Privacy, account deletion, and health content

Before review:

- publish a public HTML privacy policy under the developer or app identity;
- link it in Play Console and inside the app;
- provide in-app account deletion and an external web deletion request path;
- explain deletion/retention clearly and verify it against database backups and audit requirements;
- complete the Health apps declaration for an education/reference product;
- keep the educational/non-clinical disclaimer visible and avoid diagnosis or treatment claims.

## Content and policy declarations

- [ ] App access instructions and a working reviewer account.
- [ ] Ads declaration checked against the entire dependency/SDK set.
- [ ] Content rating questionnaire.
- [ ] Target audience and content selection.
- [ ] Data safety form.
- [ ] Health apps declaration.
- [ ] Privacy-policy URL.
- [ ] Account-deletion URL and in-app deletion flow.
- [ ] Government-app declaration.
- [ ] News/magazine declaration if Play asks; the expected response is based on actual product scope.
- [ ] Intellectual-property review for all questions, explanations, logos, screenshots, and source claims.

## First Play submission sequence

1. Create the Play application with the permanent package identity.
2. Complete developer-account verification and enroll the app in Play App Signing.
3. Create the Android OAuth client using the Play app-signing SHA fingerprints; keep the EAS upload-key fingerprints registered for directly installed builds where required.
4. Produce the EAS production AAB and upload it manually for the first submission.
5. Complete app content, store listing, pricing/regions, privacy, deletion, and reviewer access.
6. Release to internal testing and install through its Play opt-in link.
7. Resolve pilot blockers, then promote the same tested artifact to closed testing where possible.
8. Meet the Play Console’s closed-test requirements for this developer account before requesting production access.
9. Submit production access only after the Milestone 17 exit gate passes.

Internal-test users may need to opt out before they can receive a closed/open track build. Keep tester groups separate or give explicit opt-out instructions.

## Submission commands

From `apps/mobile` after environment validation:

```bash
bunx eas-cli build --platform android --profile production
```

The first Google Play upload must normally be completed manually. After the application exists and a Google service account is configured for Play Console, CI or EAS Submit can upload later builds:

```bash
bunx eas-cli submit --platform android --profile production
```

Never commit the Google service-account JSON, review password, signing material, or production `.env` files.

## References

- [Google Play store listing and asset requirements](https://support.google.com/googleplay/android-developer/answer/9866151)
- [Google Play store listing text limits](https://support.google.com/googleplay/android-developer/answer/13393723)
- [Google Play testing tracks](https://support.google.com/googleplay/android-developer/answer/9845334)
- [Google Play Data safety](https://support.google.com/googleplay/android-developer/answer/10787469)
- [Google Play account deletion](https://support.google.com/googleplay/android-developer/answer/13327111)
- [Google Play health content policy](https://support.google.com/googleplay/android-developer/answer/16679511)
- [Expo Android submission](https://docs.expo.dev/submit/android/)
- [Expo manual Android submission](https://docs.expo.dev/submit/android-manual/)
