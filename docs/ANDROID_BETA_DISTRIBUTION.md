# Android Beta Distribution

## Current decision

DocEdge AI will use **signed APKs attached to GitHub prereleases** for its first Android pilot. Google Play publication is deferred until the application is stable and there is budget and product justification for store distribution.

F-Droid is an evaluation track, not the current beta channel. The present application cannot be submitted to F-Droid’s main repository without source/licensing and dependency changes.

## Why GitHub Releases first

- GitHub Releases can package release notes, source tags, APKs, and checksum files together.
- The existing EAS preview profile already creates an installable, signed APK.
- A release keeps a durable mapping between source commit, app version, APK, and tester feedback.
- Testers do not need Google Play enrollment.
- Google Play work can resume later without changing the Android package name.

Trade-offs:

- Android shows an unknown-source/security warning during installation.
- Updates are not automatically installed; testers must install the newer APK.
- There is no store review, staged rollout, device catalog, or Play crash dashboard.
- A public repository exposes source and release assets to everyone. A private repository requires every tester to have authorized GitHub access.

This removes the Play developer-account dependency, but it does not make every build resource unlimited. Expo’s current Free plan advertises up to 15 Android builds per month and does not charge overages; builds pause when the quota is exhausted. GitHub Actions billing/allowance also depends on whether the repository is public or private. Batch fixes and reserve native builds for release candidates.

## Public-source blockers

Do **not** make the repository public yet. Complete these first:

1. Rotate every credential that was present in the committed root `.env`.
2. Remove `.env` from Git tracking and decide whether to purge it from history.
3. Audit Git history for credentials, copyrighted books/datasets, private question content, generated evidence, user data, signing material, and service-account files.
4. Choose and add an OSI-approved license if the product is intended to be open source. There is currently no `LICENSE` file.
5. Add copyright/license notices for code, artwork, fonts, screenshots, and redistributable datasets.
6. Decide which production configuration and operational documentation should remain private.

Until these gates pass, use either:

- a private GitHub repository with named testers as collaborators; or
- a separate public binary-release repository containing only approved APKs, checksums, release notes, privacy/support links, and no application source. The second option is public distribution, but it is not itself an open-source release.

## Automated GitHub beta release

The workflow `.github/workflows/android-beta-release.yml` performs validation, starts an EAS signed-APK build, downloads the result, creates a SHA-256 checksum, and publishes both files as a GitHub prerelease.

### One-time setup

1. In GitHub, create a protected `preview` environment.
2. Add `EXPO_TOKEN` as an environment secret.
3. In EAS, configure the `preview` environment:

   ```text
   EXPO_PUBLIC_API_URL=https://<production-or-beta-api>
   EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=<backend-web-oauth-client-id>
   ```

4. Confirm the EAS Android signing certificate SHA-1 is registered in the Android OAuth client for package `ai.docedge.student`.
5. Confirm the EAS-managed signing key is retained. Every APK update for the installed package must use the same signing key.
6. Protect the workflow/environment so only maintainers can create beta releases.

### Create a beta

1. Set `apps/mobile/app.json` to the intended semantic app version, validate the native/runtime change, and merge the approved release candidate into `main`.
2. Open **Actions → Android Beta Release → Run workflow**.
3. Enter a unique tag matching the app version, such as `android-beta-v1.0.2` or `android-beta-v1.0.2-beta.2`.
4. Wait for validation and EAS Build to complete.
5. Open the generated GitHub prerelease and confirm it contains:
   - `docedge-ai-android-beta-v1.0.2.apk`
   - `docedge-ai-android-beta-v1.0.2.apk.sha256`
6. Install and smoke-test that exact release asset before sharing it.

The workflow creates a prerelease, not a production release. It does not publish to Google Play.

### Manual fallback

If GitHub Actions or EAS automation is unavailable:

```bash
cd apps/mobile
eas build --platform android --profile github-beta
```

Download the completed APK from EAS, calculate its SHA-256 checksum, and attach both files manually to a versioned GitHub prerelease. Never attach an unsigned APK or an APK built from uncommitted source.

## Tester installation instructions

Send testers the release page, version, checksum, and feedback link—not a forwarded APK from an unknown chat account.

1. Open the GitHub prerelease on the Android phone.
2. Download the `.apk` asset.
3. Allow installation from the browser or GitHub client only when Android asks.
4. Install the APK and disable that unknown-source permission again afterward.
5. Open DocEdge AI and report the version/device details with any issue.

For an update, download the newer APK and install it over the existing application. The update succeeds only when the package ID and signing key match and the new `versionCode` is greater. Do not uninstall first unless testing fresh-install behavior; uninstalling removes local application data.

### Checksum verification

On a desktop before installing:

```bash
sha256sum -c docedge-ai-android-beta-v1.0.2.apk.sha256
```

On macOS:

```bash
shasum -a 256 docedge-ai-android-beta-v1.0.2.apk
```

Compare the result with the published `.sha256` file.

## Beta channels

| Phase | Audience | Distribution | Promotion gate |
|---|---|---|---|
| Maintainer smoke test | Owner and developers | EAS build URL or draft prerelease | Installs, starts, authenticates, and reaches dashboard |
| Trusted pilot | 2–5 pathology learners | Private GitHub prerelease | No open P0/P1 defect; two assessments per tester |
| Wider beta | 10–20 invited learners | Public or private GitHub prerelease after source/security decision | Milestone 17 stability and privacy gates |
| Store evaluation | Only after stable beta | Google Play or another store | Product/budget decision and store compliance review |

## Update and rollback behavior

- Native dependency, icon, permission, package, or Expo SDK changes require a new signed APK.
- Compatible JavaScript/assets may use the existing preview EAS Update channel, but the release notes must identify the update and installed runtime.
- Keep at least the previous known-good APK release available.
- GitHub has no staged rollout. If a bad beta is published, mark it clearly, remove its download link if necessary, and publish a higher-version fixed APK. Existing installations cannot be remotely removed.
- Backend and database changes must remain compatible with at least the current and previous beta APK.

## F-Droid readiness assessment

F-Droid’s main repository builds applications from publicly accessible source and requires FLOSS licensing and dependencies. The current project has these blockers:

| Blocker | Required change |
|---|---|
| No repository license | Select and add an accepted FLOSS license and audit all included assets/data. |
| Native Google Sign-In / Google Play Services | Create an F-Droid build flavor with password authentication and no GMS/Firebase/proprietary SDK dependency. |
| Expo Updates | Disable it for the F-Droid flavor or implement explicit opt-in behavior compatible with F-Droid’s executable-download policy. |
| Hosted backend dependency | Document the network service and likely F-Droid anti-feature; consider whether a self-hostable backend is in scope. |
| Expo/React Native monorepo build | Produce a deterministic command-line Gradle build from a tagged public commit in F-Droid’s isolated environment. |
| Metadata | Add Fastlane-compatible descriptions, icon, screenshots, and version-code changelog. |
| Signing/update strategy | Decide F-Droid signing versus reproducible builds before users install the first F-Droid version. |

F-Droid becomes reasonable after the beta proves the product and an explicit `fdroid` flavor is maintainable. It is not a faster replacement for GitHub APK distribution.

## Privacy and safety still apply

Skipping Play Store does not remove responsibility for user data. Before inviting external testers:

- publish privacy, support, educational disclaimer, and account-deletion information;
- implement account deletion and session invalidation;
- minimize and redact diagnostic data;
- avoid collecting patient information;
- provide a maintained security/support contact;
- preserve question provenance and avoid clinical-use claims.

## References

- [GitHub Releases documentation](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [GitHub release links and direct asset downloads](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases)
- [Expo installable Android APK builds](https://docs.expo.dev/build-reference/apk/)
- [Expo internal distribution](https://docs.expo.dev/build/internal-distribution/)
- [Expo plans and Free-build limits](https://docs.expo.dev/billing/plans/)
- [F-Droid inclusion policy](https://f-droid.org/docs/Inclusion_Policy/)
- [F-Droid submission guide](https://f-droid.org/en/docs/Submitting_to_F-Droid_Quick_Start_Guide/)
