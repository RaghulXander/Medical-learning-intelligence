'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  GraduationCap,
  Calendar,
  Building2,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Stethoscope,
  Microscope,
  Award,
  Layers,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth-context';
import { studentApi } from '@medical/api-client';
import { MedicalTaxonomyMetadata, ExaminationNode } from '@medical/shared';

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  NEET_SS: Microscope,
  NEET_PG: GraduationCap,
  MD_PATH: Stethoscope,
  MBBS: Building2,
  FELLOWSHIP: Award,
};

const DEFAULT_EXAMINATIONS: ExaminationNode[] = [
  {
    id: 'NEET_SS',
    title: 'NEET-SS / DrNB Super-Specialty',
    badge: 'Super-Specialty',
    category: 'super_specialty',
    description: 'High-yield oncology, sub-specialty IHC algorithms, flow cytometry & molecular diagnostics.',
    has_specialities: true,
    specialities: [
      { id: 'Oncopathology', name: 'Oncopathology & Tumor Markers', is_default: true },
      { id: 'Hematopathology', name: 'Hematopathology & Flow Cytometry' },
      { id: 'General & Surgical Pathology', name: 'General & Surgical Pathology' },
      { id: 'Molecular Diagnostics', name: 'Molecular Genetics & Diagnostic IHC' },
      { id: 'Cytopathology', name: 'Cytopathology & FNAC' },
      { id: 'Neuropathology', name: 'Neuropathology & CNS Tumors' },
      { id: 'Nephropathology', name: 'Nephropathology & Renal Biopsies' },
    ],
  },
  {
    id: 'MD_PATH',
    title: 'MD / MS / DNB Residency Exit Exam',
    badge: 'Residency Exit',
    category: 'postgraduate',
    description: 'Theory and practical viva exam prep with comprehensive surgical pathology & hematology depth.',
    has_specialities: true,
    specialities: [
      { id: 'General & Surgical Pathology', name: 'General & Surgical Pathology', is_default: true },
      { id: 'Hematopathology', name: 'Clinical Hematology & Transfusion' },
      { id: 'Cytopathology', name: 'Diagnostic Cytopathology' },
      { id: 'Chemical Pathology', name: 'Biochemistry & Lab Management' },
    ],
  },
  {
    id: 'NEET_PG',
    title: 'NEET-PG / INI-CET Entrance',
    badge: 'Postgraduate Entrance',
    category: 'postgraduate',
    description: 'Comprehensive clinical vignettes across 19 subjects with deep pathology & medicine core.',
    has_specialities: false,
    default_speciality: 'General Medicine & Pathology Core',
    specialities: [],
  },
  {
    id: 'MBBS',
    title: 'MBBS Professional University Exam',
    badge: 'Undergraduate',
    category: 'undergraduate',
    description: 'Core fundamentals, general disease mechanisms, systemic pathology & clinical vignettes.',
    has_specialities: false,
    default_speciality: '2nd Professional Pathology Core',
    specialities: [],
  },
  {
    id: 'FELLOWSHIP',
    title: 'Post-Doctoral Clinical Fellowship',
    badge: 'Sub-Specialty Board',
    category: 'fellowship',
    description: 'Advanced subspecialty certification in oncopathology, hematopathology, or neuropathology.',
    has_specialities: true,
    specialities: [
      { id: 'Oncopathology Fellowship', name: 'Oncopathology Fellowship (Tata / AIIMS Pattern)', is_default: true },
      { id: 'Hematopathology Fellowship', name: 'Hematopathology & Flow Cytometry Fellowship' },
      { id: 'Dermatopathology Fellowship', name: 'Dermatopathology & Skin Biopsy Fellowship' },
    ],
  },
];

export default function OnboardingWizardPage() {
  const router = useRouter();
  const { user, updateProfile } = useAuth();

  const [taxonomy, setTaxonomy] = useState<MedicalTaxonomyMetadata | null>(null);
  const [step, setStep] = useState(1);
  const [targetExam, setTargetExam] = useState(user?.target_exam || 'NEET_SS');
  const [targetYear, setTargetYear] = useState<number>(user?.target_year || 2026);
  const [primarySpeciality, setPrimarySpeciality] = useState(user?.primary_speciality || 'Oncopathology');
  const [residencyStage, setResidencyStage] = useState(user?.residency_stage || 'JR');
  const [medicalCollege, setMedicalCollege] = useState(user?.medical_college || '');
  const [loading, setLoading] = useState(false);

  const examinations: ExaminationNode[] = taxonomy?.examinations || DEFAULT_EXAMINATIONS;
  const selectedExamNode: ExaminationNode =
    examinations.find((e) => e.id === targetExam) || examinations[0] || DEFAULT_EXAMINATIONS[0]!;

  // Fetch dynamic curriculum & examination taxonomy
  useEffect(() => {
    studentApi
      .getTaxonomies()
      .then((data) => {
        setTaxonomy(data);
        const currentExam = data.examinations.find((e) => e.id === (user?.target_exam || 'NEET_SS'));
        if (currentExam) {
          if (!currentExam.has_specialities && currentExam.default_speciality) {
            setPrimarySpeciality(currentExam.default_speciality);
          } else if (currentExam.specialities.length > 0 && !user?.primary_speciality) {
            const firstSpec = currentExam.specialities[0]?.id;
            if (firstSpec) setPrimarySpeciality(firstSpec);
          }
        }
      })
      .catch((err) => {
        console.warn('Using local fallback taxonomies:', err);
      });
  }, [user]);

  const stageOptions = taxonomy?.experience_stages || [
    { id: 'MBBS', label: 'MBBS Student / Intern' },
    { id: 'JR', label: 'Junior Resident (MD / MS / DNB Trainee)' },
    { id: 'SR', label: 'Senior Resident (Post-MD / Post-MS)' },
    { id: 'FELLOW', label: 'Fellow (Sub-Specialty Trainee)' },
    { id: 'CONSULTANT', label: 'Practicing Specialist / Consultant' },
  ];

  const targetYears = taxonomy?.target_years || [2026, 2027, 2028];

  const handleSelectExam = (examId: string) => {
    setTargetExam(examId);
    const exam = examinations.find((e) => e.id === examId);
    if (exam) {
      if (!exam.has_specialities && exam.default_speciality) {
        setPrimarySpeciality(exam.default_speciality);
      } else if (exam.specialities.length > 0) {
        const firstSpec = exam.specialities[0]?.id;
        if (firstSpec) setPrimarySpeciality(firstSpec);
      }
    }
  };

  const handleFinish = async () => {
    setLoading(true);
    try {
      const updated = await studentApi.updateOnboarding({
        target_exam: targetExam,
        target_year: targetYear,
        residency_stage: residencyStage,
        medical_college: medicalCollege,
        primary_speciality: primarySpeciality,
      });
      updateProfile(updated);
      router.push('/student');
    } catch (err) {
      console.error('Failed to complete onboarding:', err);
      router.push('/student');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4 py-12 relative overflow-hidden">
      {/* Glow Backdrops */}
      <div className="absolute top-1/4 left-1/4 w-[450px] h-[450px] rounded-full bg-sky-500/10 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[450px] h-[450px] rounded-full bg-indigo-500/10 blur-[130px] pointer-events-none" />

      <div className="w-full max-w-2xl mx-auto glass-card rounded-2xl border border-white/10 p-6 sm:p-10 shadow-2xl bg-slate-900/85 relative z-10">
        {/* Progress Bar & Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-medium">
            <span>Step {step} of 3</span>
            <span>
              {step === 1
                ? 'Target Examination'
                : step === 2
                ? selectedExamNode.has_specialities
                  ? 'Target Speciality & Attempt Year'
                  : 'Curriculum Track & Attempt Year'
                : 'Experience & Medical College'}
            </span>
          </div>
          <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-sky-400 to-indigo-500 transition-all duration-300 rounded-full"
              style={{ width: `${(step / 3) * 100}%` }}
            />
          </div>
        </div>

        {/* STEP 1: Dynamic Medical Examination Nodes */}
        {step === 1 && (
          <div className="space-y-6 animate-fade-in">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-semibold mb-2">
                <Sparkles className="h-3 w-3" /> Step 1: Target Medical Exam
              </div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">
                What examination are you preparing for?
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Select your target examination level to calibrate blueprint mock engines and question difficulty.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {examinations.map((opt) => {
                const Icon = ICON_MAP[opt.id] || GraduationCap;
                const isSelected = targetExam === opt.id;
                return (
                  <div
                    key={opt.id}
                    onClick={() => handleSelectExam(opt.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-sky-500/80 bg-sky-500/10 shadow-lg shadow-sky-500/10'
                        : 'border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.06]'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="p-2 rounded-lg bg-sky-500/20 text-sky-400 mb-3">
                        <Icon className="h-5 w-5" />
                      </div>
                      <Badge variant={isSelected ? 'verified' : 'outline'} className="text-[10px]">
                        {opt.badge}
                      </Badge>
                    </div>
                    <h3 className="text-sm font-bold text-white">{opt.title}</h3>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">{opt.description}</p>
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end pt-4">
              <Button variant="gradient" onClick={() => setStep(2)} className="gap-2 px-6 h-11 font-bold">
                <span>
                  {selectedExamNode.has_specialities ? 'Continue to Speciality' : 'Continue to Timeline'}
                </span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* STEP 2: Speciality Leaf Nodes (or Core Track for single-leaf exams) & Attempt Year */}
        {step === 2 && (
          <div className="space-y-6 animate-fade-in">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
                <Calendar className="h-3 w-3" /> Step 2: Speciality & Session
              </div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">
                {selectedExamNode.has_specialities
                  ? 'Select your Speciality & Target Year'
                  : 'Confirm Curriculum Track & Target Year'}
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                We will personalize your daily high-yield quiz and weak-topic remedial drills based on this focus.
              </p>
            </div>

            <div className="space-y-4">
              {/* If exam has specialities: show dynamic leaf nodes */}
              {selectedExamNode.has_specialities ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Target Speciality / Discipline
                  </label>
                  <select
                    value={primarySpeciality}
                    onChange={(e) => setPrimarySpeciality(e.target.value)}
                    className="w-full h-11 px-3.5 rounded-xl bg-slate-950/70 border border-white/10 text-white text-sm focus:outline-none focus:border-sky-500 transition-colors"
                  >
                    {selectedExamNode.specialities.map((sp) => (
                      <option key={sp.id} value={sp.id}>
                        {sp.name}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                /* If exam has NO subspecialties (e.g. MBBS, NEET-PG): show Unified Core Leaf Card */
                <div className="p-4 rounded-xl border border-sky-500/30 bg-sky-500/10 flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-sky-500/20 text-sky-400">
                    <Layers className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white">
                      {selectedExamNode.default_speciality || 'Standard Curriculum Track'}
                    </h4>
                    <p className="text-xs text-slate-300">
                      All university syllabus subjects and clinical vignette modules are automatically included.
                    </p>
                  </div>
                </div>
              )}

              {/* Dynamic Target Year Selector */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Target Attempt Session</label>
                <div className="grid grid-cols-3 gap-3">
                  {targetYears.map((yr) => (
                    <button
                      key={yr}
                      type="button"
                      onClick={() => setTargetYear(yr)}
                      className={`p-3 rounded-xl border text-sm font-bold transition-all ${
                        targetYear === yr
                          ? 'border-sky-500 bg-sky-500/20 text-white shadow-md'
                          : 'border-white/10 bg-white/[0.03] text-slate-400 hover:text-white'
                      }`}
                    >
                      {yr} Session
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-between pt-4">
              <Button
                variant="outline"
                onClick={() => setStep(1)}
                className="gap-2 border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
              >
                <ArrowLeft className="h-4 w-4" /> Back
              </Button>
              <Button variant="gradient" onClick={() => setStep(3)} className="gap-2 px-6 h-11 font-bold">
                <span>Continue to Profile</span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* STEP 3: Stage & Medical Institution */}
        {step === 3 && (
          <div className="space-y-6 animate-fade-in">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-2">
                <Building2 className="h-3 w-3" /> Step 3: Medical Background
              </div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">
                Tell us about your medical background
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                This helps us benchmark your diagnostic accuracy and percentile against peer resident cohorts.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Current Stage / Designation</label>
                <div className="grid gap-2">
                  {stageOptions.map((stg) => (
                    <button
                      key={stg.id}
                      type="button"
                      onClick={() => setResidencyStage(stg.id)}
                      className={`p-3 rounded-xl border text-left text-xs sm:text-sm font-medium transition-all ${
                        residencyStage === stg.id
                          ? 'border-sky-500 bg-sky-500/15 text-white'
                          : 'border-white/10 bg-white/[0.03] text-slate-400 hover:text-white'
                      }`}
                    >
                      {stg.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Medical College / Hospital (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. AIIMS New Delhi, Tata Memorial Hospital, CMC Vellore"
                  value={medicalCollege}
                  onChange={(e) => setMedicalCollege(e.target.value)}
                  className="w-full h-11 px-3.5 rounded-xl bg-slate-950/70 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-sky-500 transition-colors"
                />
              </div>
            </div>

            <div className="flex justify-between pt-4">
              <Button
                variant="outline"
                onClick={() => setStep(2)}
                className="gap-2 border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
              >
                <ArrowLeft className="h-4 w-4" /> Back
              </Button>
              <Button
                variant="gradient"
                disabled={loading}
                onClick={handleFinish}
                className="gap-2 px-8 h-11 font-bold shadow-lg shadow-sky-500/20"
              >
                {loading ? (
                  <span>Saving Profile...</span>
                ) : (
                  <>
                    <span>Complete & Go to Dashboard</span>
                    <CheckCircle2 className="h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
