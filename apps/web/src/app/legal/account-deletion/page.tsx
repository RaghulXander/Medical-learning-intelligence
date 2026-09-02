import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Account Deletion & Data Rights — DocEdge',
  description: 'Step-by-step instructions for permanent account and data deletion in DocEdge.',
};

export default function AccountDeletionPage() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-12 text-slate-200">
      <div className="border-b border-slate-800 pb-6 mb-8">
        <span className="text-xs font-bold uppercase tracking-widest text-red-400 bg-red-950/60 border border-red-800/60 px-3 py-1 rounded-full">
          Data Rights & Erasure
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight text-white mt-4">
          Account & Data Deletion Instructions
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          GDPR Article 17 • CCPA Right to Delete Policy • DocEdge (ai.docedge.student)
        </p>
      </div>

      <div className="space-y-8 text-sm leading-relaxed">
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 text-slate-300">
          <p className="font-semibold text-white mb-1">
            Immediate Self-Service Deletion Available
          </p>
          <p className="text-xs text-slate-400 leading-normal">
            You do not need to submit a ticket or wait for manual review to delete your account.
            You can permanently erase your profile directly inside the DocEdge mobile app at any time.
          </p>
        </div>

        <section className="space-y-4">
          <h2 className="text-lg font-bold text-white">How to Delete Your Account (In-App Steps)</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
              <span className="text-xs font-bold text-sky-400 uppercase">Step 1</span>
              <h3 className="font-bold text-white mt-1">Open Profile</h3>
              <p className="text-xs text-slate-400 mt-1">
                Launch the DocEdge Android app and navigate to the <strong>Profile</strong> tab in the bottom navigation bar.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
              <span className="text-xs font-bold text-sky-400 uppercase">Step 2</span>
              <h3 className="font-bold text-white mt-1">Select Delete</h3>
              <p className="text-xs text-slate-400 mt-1">
                Scroll down to the <strong>Account Operations</strong> section and tap <strong>Delete Account & Data</strong>.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
              <span className="text-xs font-bold text-sky-400 uppercase">Step 3</span>
              <h3 className="font-bold text-white mt-1">Confirm Erasure</h3>
              <p className="text-xs text-slate-400 mt-1">
                Read the warning dialog and confirm twice. Your account and data will be permanently wiped immediately.
              </p>
            </div>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">What Happens When You Delete Your Account</h2>
          <ul className="list-disc pl-6 space-y-2 text-slate-300">
            <li>
              <strong className="text-white">Credentials & Sessions Purged:</strong> Your email, hashed passwords, OAuth linkages, and active JWT refresh tokens across all devices are immediately deleted.
            </li>
            <li>
              <strong className="text-white">Personal Learner Profiles Erased:</strong> Your preparation streak, topic accuracy scores, spaced repetition history, and custom target exam preferences are permanently destroyed.
            </li>
            <li>
              <strong className="text-white">Test Attempts Anonymized:</strong> Individual examination answers are stripped of your user identifier (anonymized) to preserve psychometric difficulty calibration without tying data to any individual.
            </li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">Alternative: Request Deletion via Email</h2>
          <p>
            If you no longer have access to your mobile device or need assistance with data erasure, you can submit a manual deletion request by emailing us from your registered account email:
          </p>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 font-mono text-xs text-slate-300 space-y-1">
            <p><strong>To:</strong> support@docedge.ai</p>
            <p><strong>Subject:</strong> Account Deletion Request — [Your Registered Email]</p>
            <p><strong>Body:</strong> Please permanently erase my DocEdge account and all associated personal data.</p>
          </div>
          <p className="text-xs text-slate-400">
            Manual email requests are verified and processed within 48 hours.
          </p>
        </section>
      </div>
    </main>
  );
}
