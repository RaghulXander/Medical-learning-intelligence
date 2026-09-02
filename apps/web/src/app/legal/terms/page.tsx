import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms & Educational Disclaimer — DocEdge',
  description: 'Terms of service, intellectual property, and medical educational disclaimer for DocEdge.',
};

export default function TermsPage() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-12 text-slate-200">
      <div className="border-b border-slate-800 pb-6 mb-8">
        <span className="text-xs font-bold uppercase tracking-widest text-sky-400 bg-sky-950/60 border border-sky-800/60 px-3 py-1 rounded-full">
          Terms & Disclaimers
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight text-white mt-4">
          Terms of Service & Medical Disclaimer
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Effective Date: September 2026 • DocEdge Medical Intelligence
        </p>
      </div>

      <div className="space-y-8 text-sm leading-relaxed">
        {/* Critical Medical Disclaimer Banner */}
        <div className="p-5 rounded-xl border border-amber-500/40 bg-amber-950/20 text-amber-200">
          <h3 className="font-bold text-base text-amber-300 mb-1">
            CRITICAL MEDICAL EDUCATION DISCLAIMER
          </h3>
          <p className="text-xs text-amber-200/90 leading-normal">
            DocEdge is exclusively an academic examination simulation and educational test-preparation platform.
            Content provided—including multiple-choice questions, simulated clinical vignettes, histopathological micrographs, and AI explanations—is strictly intended for medical licensure and postgraduate competitive examinations (NEET-PG, NEET-SS, MD Pathology).
            <br /><br />
            <strong>THIS PLATFORM DOES NOT PROVIDE MEDICAL ADVICE, CLINICAL DIAGNOSES, OR TREATMENT PLANS.</strong>
            Never use information from this platform for clinical patient diagnosis or bedside medical care. Always consult certified clinical protocols and primary institutional review.
          </p>
        </div>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">1. Educational Intended Use</h2>
          <p>
            By using DocEdge mobile applications or web platforms, you acknowledge and agree that:
          </p>
          <ul className="list-disc pl-6 space-y-1.5 text-slate-300">
            <li>You are a qualified medical professional, resident, fellow, or medical student preparing for board, exit, or entrance examinations.</li>
            <li>Synthetic AI-generated questions and explanations are training aids designed to test diagnostic criteria and must not be treated as autonomous medical truth.</li>
            <li>All textbook citations (e.g. Robbins & Cotran, Sternberg, WHO Classification) represent academic provenance indicators for learning reference.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">2. User Accounts & Integrity</h2>
          <p>
            You agree to maintain the security of your account credentials. Sharing accounts, distributing exam items, or attempting to reverse-engineer proprietary algorithms is strictly prohibited.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">3. Intellectual Property</h2>
          <p>
            The DocEdge software, assessment engine, user interfaces, branding, and proprietary algorithms are protected by copyright.
            Reference excerpts and figure citations are utilized solely under educational fair reference principles to verify academic medical curricula.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">4. Limitation of Liability</h2>
          <p>
            Under no circumstances shall DocEdge, its developers, or affiliated medical contributors be liable for any direct, indirect, incidental, or consequential damages arising from the use or inability to use this platform, including examination scores or clinical decisions.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">5. Contact Information</h2>
          <p>
            For inquiries regarding terms, licensing, or academic partnerships:
          </p>
          <p className="text-sky-400 font-medium">legal@docedge.ai</p>
        </section>
      </div>
    </main>
  );
}
