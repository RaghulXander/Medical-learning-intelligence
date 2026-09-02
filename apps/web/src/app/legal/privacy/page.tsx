import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy — DocEdge Medical Exam AI',
  description: 'Privacy Policy, telemetry transparency, and data rights for DocEdge users and mobile beta testers.',
};

export default function PrivacyPolicyPage() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-12 text-slate-200">
      <div className="border-b border-slate-800 pb-6 mb-8">
        <span className="text-xs font-bold uppercase tracking-widest text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-3 py-1 rounded-full">
          Compliance & GDPR/CCPA
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight text-white mt-4">
          Privacy Policy
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Effective Date: September 2026 • Application: DocEdge (ai.docedge.student)
        </p>
      </div>

      <div className="space-y-8 text-sm leading-relaxed">
        {/* Important Callout */}
        <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 text-emerald-300">
          <p className="font-semibold text-emerald-200 mb-1">
            Zero Patient Identifiable Data (PHI) Policy
          </p>
          <p className="text-xs text-emerald-300/90 leading-normal">
            DocEdge is strictly an academic preparation and testing platform for medical doctors.
            We do not collect, ingest, or store patient records, clinical charts, or protected health information.
            All histopathological micrographs and clinical vignettes are simulated or published educational reference assets.
          </p>
        </div>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">1. Information We Collect</h2>
          <p>
            When registering, taking examinations, or utilizing DocEdge mobile applications, we collect the following minimal data:
          </p>
          <ul className="list-disc pl-6 space-y-1.5 text-slate-300">
            <li><strong className="text-white">Account Identification:</strong> Full name, verified email address, hashed passwords (Argon2id), or Google OAuth unique identifiers.</li>
            <li><strong className="text-white">Academic Profile:</strong> Target examination track (e.g. NEET-SS, NEET-PG, MD Pathology), target examination year, medical college, and residency stage.</li>
            <li><strong className="text-white">Assessment & Performance Data:</strong> Answers selected, timestamps, elapsed question duration, review bookmarks, and topic mastery ratings.</li>
            <li><strong className="text-white">Technical Diagnostics:</strong> Operating system version, app release version, device hardware class, and privacy-sanitized error stack traces (all authorization tokens and personal data are strictly redacted).</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">2. How We Use Information</h2>
          <p>We process collected data exclusively to:</p>
          <ul className="list-disc pl-6 space-y-1.5 text-slate-300">
            <li>Deliver personalized adaptive question selection based on mastery state.</li>
            <li>Calculate standardized NEET-SS/NEET-PG scorecards (+4/-1 scoring).</li>
            <li>Detect question quality defects and misclassified distractors via reporting tools.</li>
            <li>Ensure security, rate-limiting, and single-user session integrity.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">3. Third-Party Services & Infrastructure</h2>
          <p>
            DocEdge utilizes SOC-2 and ISO-27001 compliant cloud infrastructure:
          </p>
          <ul className="list-disc pl-6 space-y-1.5 text-slate-300">
            <li><strong className="text-white">Database:</strong> Neon Cloud PostgreSQL (Encrypted at rest with AES-256 and TLS 1.3 in transit).</li>
            <li><strong className="text-white">Object Storage & CDN:</strong> Cloudflare R2 (Public educational pathology micrographs).</li>
            <li><strong className="text-white">Identity:</strong> Google Identity Services (OAuth 2.0).</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">4. Right to Erasure (Account & Data Deletion)</h2>
          <p>
            In accordance with GDPR, CCPA, and privacy best practices, users have an absolute right to permanently delete their account and personal data.
          </p>
          <p>
            Users may trigger immediate self-service account deletion at any time inside the mobile app:
            <br />
            <code className="text-sky-400 bg-slate-900 px-2 py-1 rounded">Profile → Account Operations → Delete Account & Data</code>.
          </p>
          <p>
            Upon deletion, authentication sessions are invalidated immediately, personal mastery data is purged, and test attempts are anonymized to maintain institutional psychometric validity.
            See our <a href="/legal/account-deletion" className="text-sky-400 underline hover:text-sky-300">Account Deletion Guide</a> for detailed steps.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">5. Security & Contact</h2>
          <p>
            If you have questions regarding your data privacy or wish to submit a data protection inquiry, please contact our team:
          </p>
          <p className="text-sky-400 font-medium">support@docedge.ai</p>
        </section>
      </div>
    </main>
  );
}
