# Milestone 17 — Android Direct Beta and Stabilization

## Decision

Milestone 17 produces a stable Android pilot without paying for or depending on an app-store launch. The primary beta channel is a **signed APK published as a versioned GitHub prerelease**. Google Play is deferred until the product is stable and the team decides store reach justifies its cost and operational work.

F-Droid is a later compatibility track. It requires a public FLOSS-licensed source tree and a build flavor without proprietary Google dependencies; it is not the first beta channel.

Milestone 16 remains reserved for evidence-bound learning-content generation. Release stabilization can proceed while the Milestone 15 evidence gate is completed.

## Outcome

Deliver a signed Android APK that:

- installs and starts reliably on supported physical Android devices;
- completes password and native Google authentication against the beta/production API;
- preserves onboarding and exam progress without data loss;
- exposes privacy, support, educational disclaimer, and account-deletion paths;
- is traceable to one Git commit, release tag, checksum, signing key, and test report;
- can be observed, supported, updated, and rolled back during a controlled pilot.

## Scope boundaries

Included:

- Android only;
- GitHub prerelease automation and directly installable APKs;
- production-like API connectivity and Google authentication;
- branding, release notes, signing continuity, checksums, diagnostics, tester instructions, feedback triage, and rollback;
- a small trusted pilot followed by a wider invited beta.

Deferred:

- Google Play and iOS App Store publication;
- F-Droid main-repository submission;
- payments and self-service subscriptions (Milestone 50);
- unrestricted public registration or broad production rollout;
- image diagnosis, clinical decision support, or patient-care claims;
- scaling the content corpus before evidence and editorial gates pass.

## Current release baseline

| Area | Current state | Release implication |
|---|---|---|
| Android identity | Package `ai.docedge.student`; Expo/EAS project configured | Keep this package and its signing key stable so testers can install updates. |
| Versioning | App/runtime version `1.0.1`; EAS remote auto-increment enabled | Increment app version for native runtime changes; every APK must have a higher `versionCode`. |
| Android compatibility | Expo SDK 54 targets Android API 36 | Verify the generated manifest and physical-device coverage, independent of Play submission. |
| Branding | Full icon, adaptive foreground, splash image, transparent mark, and 512 px icon created | Ready for GitHub beta; screenshots remain useful for the release page. |
| Distribution | `github-beta` EAS profile and manual GitHub Actions workflow added | Needs `EXPO_TOKEN`, EAS preview environment values, and a successful first workflow run. |
| Authentication | Password and native Google sign-in are implemented | Register the EAS signing SHA with the Android OAuth client and test the signed beta APK. |
| Backend | Hosted API/database deployment exists | Health checks, migrations, backup restore, cold-start handling, and rollback must be exercised. |
| Monetization | Manual subscription/entitlement assignment | Pilot copy must state access is controlled; do not imply in-app purchasing. |
| Account deletion | No verified end-to-end deletion flow | **External-beta blocker**: implement in-app deletion and a public deletion resource. |
| Observability | No verified mobile crash/error reporting | **Wider-beta blocker**: add privacy-reviewed crash and release diagnostics. |
| Source licensing | No `LICENSE` file | **Open-source blocker**: the owner must choose a FLOSS license and audit third-party assets/data. |
| Repository secrets | A root `.env` was previously committed and pushed | **Public-repository blocker**: rotate credentials and remove tracked/history exposure before making source public. |

## 17.0 — Brand, identity, and signed artifact

- [x] Replace the generic application icon.
- [x] Add an Android adaptive icon and matching launch mark.
- [x] Add a `github-beta` EAS profile that creates a directly installable APK.
- [x] Add a manually triggered workflow that validates, builds, checksums, and creates a GitHub prerelease.
- [x] Manage Android `versionCode` remotely with EAS auto-increment.
- [ ] Configure GitHub’s protected `preview` environment and `EXPO_TOKEN` secret.
- [ ] Confirm the EAS preview environment contains the public API URL and Web OAuth client ID.
- [ ] Record and back up the Android signing-key ownership/recovery process.
- [ ] Register the EAS certificate SHA-1 with the Android OAuth client.
- [ ] Produce and install the first workflow-generated APK on two physical phones.
- [ ] Verify the published SHA-256 checksum before installation.

The operational procedure is documented in [Android beta distribution](../docs/ANDROID_BETA_DISTRIBUTION.md).

## 17.1 — Stability and release diagnostics

### Critical journeys

Test every journey against production-like services using both a free/pilot user and a manually entitled user:

1. Fresh install → password sign-up → onboarding → dashboard.
2. Fresh install → native Google sign-in → onboarding → dashboard.
3. Existing session → cold start → authenticated dashboard.
4. Expired token → one recovery path without a redirect or onboarding loop.
5. Free user → visible learning content → clear contact/access message instead of a broken exam.
6. Entitled user → build exam → answer → background/resume → submit → results → answer review.
7. Network loss during an assessment → deterministic recovery with no duplicate submission or lost answers.
8. Question report → admin visibility → resolution audit trail.
9. Sign out → credentials and user-specific cached state cleared.
10. Account deletion → confirmation → backend deletion/anonymization → session invalidation.
11. Existing beta → newer signed APK installed over it → account and safe local state retained.

### Implementation work

- [ ] Add privacy-reviewed crash/error reporting with environment and release tags; exclude tokens, unnecessary question text, and personal/health data.
- [ ] Capture app version, runtime version, Git tag, Android version, device class, API request ID, and sanitized failure category.
- [ ] Add visible offline, timeout, server cold-start, and maintenance states.
- [ ] Bound retries and make harmful duplicate writes idempotent.
- [ ] Verify secure token storage and authorization-header redaction.
- [ ] Exercise database migration, backup restore, API rollback, and compatibility with the current and previous APK.
- [ ] Document which changes may use EAS Update and which require a new signed APK.

### Device matrix

| Class | Minimum pilot coverage |
|---|---|
| Older supported Android | One low-memory/low-end device on the oldest supported app API level |
| Common Android | One mid-range device on Android 13 or 14 |
| Current Android | One device or emulator on Android 16/API 36 |
| Network | Wi-Fi, mobile data, slow connection, offline/reconnect, and hosted-API cold start |
| Installation | Fresh APK install, update over previous APK, sign-out/sign-in, and reinstall |

## 17.2 — Privacy, safety, and public-source readiness

Skipping an app store does not lower the product’s duty to beta users.

### External-beta blockers

- [ ] Publish stable HTTPS privacy, support, terms, educational disclaimer, and account-deletion pages.
- [ ] Link those pages from inside the app and every public download page.
- [ ] Implement account deletion in the app and verify backend deletion/anonymization and session invalidation.
- [ ] State what is deleted, what must be retained, why, and for how long.
- [ ] Inventory data collected by the app, backend, logs, and every SDK.
- [ ] Provide a security/support email and a response process.
- [ ] Ensure tester reports do not include patient information.
- [ ] Keep all claims educational and avoid diagnosis/treatment positioning.

### Before making the source repository public

- [ ] Rotate credentials exposed by the committed root `.env`.
- [ ] Stop tracking `.env` and decide whether coordinated Git-history cleanup is required.
- [ ] Scan current files and history for secrets, private data, copyrighted book content, non-redistributable datasets, question-bank restrictions, and signing material.
- [ ] Choose and add an OSI-approved license; do not assume a GitHub-visible repository is open source without one.
- [ ] Audit licenses for generated branding, fonts, dependencies, screenshots, and datasets.
- [ ] Decide whether operational infrastructure/configuration remains in the same public repository.

Until this passes, use private GitHub Releases with named collaborators or an isolated public binary-release repository. A binary-only repository is public distribution, not an open-source release.

## 17.3 — GitHub prerelease channel

### Release contents

Each beta prerelease must include:

- immutable version tag such as `android-beta-v1.0.2`;
- signed APK named from that tag;
- SHA-256 checksum file;
- generated and manually reviewed release notes;
- installation/update instructions;
- privacy, support, account-deletion, and feedback links;
- known limitations and rollback notice.

### Release gate

- Source commit is reviewed and CI passes.
- Version/runtime compatibility and signing identity are verified.
- The exact GitHub release APK—not a local substitute—passes the smoke test.
- No unresolved P0 or P1 defect exists.
- Backend backup and rollback have been tested.
- Public repository/source blockers pass before a release becomes public.

## 17.4 — Trusted pilot

### Audience and duration

- 2–5 trusted pathology learners or doctors.
- 3–7 days, with repeated login and at least two completed assessments per tester.
- Private GitHub prerelease unless the public-source/security gate has passed.

### Feedback record

Collect tester ID, timestamp, app/build version, release tag, device/Android version, current screen, reproduction steps, expected result, actual result, screenshot/video when safe, and severity. Ask testers not to include patient information.

### Exit criteria

- All critical journeys pass on at least two physical phones.
- No P0/P1 issue remains.
- Installation and update-over-existing behavior pass using consecutive signed releases.
- Every tester can find support, privacy, and deletion instructions.
- Feedback is triaged and known limitations are documented.

## 17.5 — Wider invited beta

### Audience and duration

- Begin with 10–20 invited learners and increase only if stability holds.
- Run for at least 14 consecutive days.
- Keep a tester roster, build history, weekly issue summary, and release-to-feedback mapping.

### Entry criteria

- Trusted-pilot exit criteria pass.
- Crash diagnostics and support triage are operational.
- The question pool supports every exposed assessment, or unavailable assessments are hidden/disabled clearly.
- Account deletion is verified end to end.
- Public source/release checks pass if testers do not have private-repository access.

### Exit criteria

- No unresolved P0 or P1 defects.
- At least 99.5% crash-free sessions after a minimum of 100 measured sessions.
- Critical journeys pass across all required device classes.
- At least 98% authentication completion excluding user cancellation and invalid credentials.
- No observed answer/progress loss, duplicate submission, or inconsistent score in the release-candidate matrix.
- Backend 5xx responses stay below 1% of measured beta API requests; cold starts are tracked separately.
- Product owner signs off the feedback summary and known limitations.

These are promotion gates, not marketing claims. Extend the beta when the sample is too small.

## 17.6 — F-Droid evaluation and future stores

F-Droid main-repository submission is deferred until all of these are true:

- repository and bundled assets have a compatible FLOSS license;
- a tagged public commit builds deterministically with command-line tools;
- an `fdroid` flavor removes native Google Sign-In/Google Play Services and other proprietary libraries;
- password authentication remains functional in that flavor;
- Expo Updates is disabled or redesigned to satisfy F-Droid’s explicit-consent rules for additional executable code;
- hosted-backend dependency and applicable F-Droid anti-features are disclosed;
- Fastlane-compatible metadata, screenshots, icon, changelog, and build metadata exist;
- signing versus reproducible-build strategy is decided before first publication.

Google Play work remains documented in [the Play Store listing runbook](../docs/PLAY_STORE_LISTING.md) but is not part of this milestone’s completion gate.

## Severity and response policy

| Severity | Definition | Pilot action |
|---|---|---|
| **P0** | Security/privacy exposure, account crossover, unrecoverable data loss, corrupted score, or service-wide outage | Withdraw the release immediately; rotate/revoke where relevant; owner-led incident response |
| **P1** | Repeatable startup, authentication, onboarding, exam, submission, deletion, or APK-update failure | Block wider distribution; target a tested fix within 24 hours |
| **P2** | Non-blocking functional or serious usability defect with a workaround | Triage into the current beta unless risk increases |
| **P3** | Cosmetic, copy, or low-impact enhancement | Backlog for a later release |

## Rollback strategy

- GitHub APK: mark the faulty prerelease clearly and stop sharing it. Publish a fixed APK with a higher `versionCode`; Android cannot install an older version over a newer one normally.
- EAS Update: publish only JavaScript/assets compatible with the installed runtime and republish the known-good update when safe.
- API: remain backward-compatible with the current and previous beta APK and retain a tested deployment rollback.
- Database: use forward-safe migrations, backups, and a documented restore decision; do not depend on destructive production down-migrations.

## Inputs needed from the product owner

- Whether the current source repository should eventually become public or releases should use a separate binary repository.
- The preferred open-source license after legal/product consideration; MIT/Apache-2.0 are permissive, while AGPL-3.0 requires network-service modifications to remain available under its terms.
- Approval to rotate exposed credentials and decide whether Git history must be rewritten.
- Final production domain and privacy, support, terms, deletion, and feedback URLs.
- Invited tester accounts and confirmation that `raghuljayan@gmail.com` is the public support contact.

## Definition of done

Milestone 17 is complete when:

1. Two consecutive signed GitHub prereleases install/update successfully and their checksums are verified.
2. The trusted pilot and wider invited beta meet their recorded exit gates.
3. Privacy, deletion, diagnostics, support, signing, deployment, migrations, backup, and rollback are implemented and exercised.
4. The owner has a feedback summary and written go/no-go decision for wider distribution.
5. Store publication remains an optional later business decision rather than a blocker to the Android beta.

## Authoritative references

- [GitHub Releases documentation](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [Expo installable Android APK builds](https://docs.expo.dev/build-reference/apk/)
- [Expo internal distribution](https://docs.expo.dev/build/internal-distribution/)
- [F-Droid inclusion policy](https://f-droid.org/docs/Inclusion_Policy/)
- [F-Droid submission guide](https://f-droid.org/en/docs/Submitting_to_F-Droid_Quick_Start_Guide/)
