'use client';

import React, { useState } from 'react';
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
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth-context';
import { studentApi } from '@medical/api-client';

export default function OnboardingWizardPage() {
  const router = useRouter();
  const { user, updateProfile } = useAuth();

  const [step, setStep] = useState(1);
  const [targetExam, setTargetExam] = useState(user?.target_exam || 'NEET_SS');
  const [targetYear, setTargetYear] = useState<number>(user?.target_year || 2026);
  const [primarySpeciality, setPrimarySpeciality] = useState(user?.primary_speciality || 'Pathology');
  const [residencyStage, setResidencyStage] = useState(user?.residency_stage || 'JR');
  const [medicalCollege, setMedicalCollege] = useState(user?.medical_college || '');
  const [loading, setLoading] = useState(false);

  const examOptions = [
    {
      id: 'NEET_SS',
      title: 'NEET-SS (DM / DrNB Oncopathology)',
      badge: 'Super-Specialty',
      desc: 'High-yield oncology, international diagnostic classifications, IHC algorithms & molecular genetics.',
      icon: Microscope,
    },
    {
      id: 'NEET_PG',
      title: 'NEET-PG / INI-CET Pathology',
      badge: 'Postgraduate Entrance',
      desc: 'Comprehensive clinical vignettes spanning general, hematopathology, and systemic pathology.',
      icon: GraduationCap,
    },
    {
      id: 'MD_PATH',
      title: 'MD / DNB Pathology Exit Exam',
      badge: 'Residency Exit',
      desc: 'Theory and practical viva prep with comprehensive surgical pathology depth.',
      icon: Stethoscope,
    },
    {
      id: 'MBBS',
      title: 'MBBS 2nd Professional Pathology',
      badge: 'Undergraduate',
      desc: 'Core fundamentals, general disease mechanisms, and university exam prep.',
      icon: Building2,
    },
  ];

  const stageOptions = [
    { id: 'MBBS', label: 'MBBS Student / Intern' },
    { id: 'JR', label: 'Junior Resident (MD / DNB Trainee)' },
    { id: 'SR', label: 'Senior Resident (Post-MD)' },
    { id: 'FELLOW', label: 'Fellow (Oncopath / Hematopath)' },
    { id: 'CONSULTANT', label: 'Practicing Pathologist / Consultant' },
  ];

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
            <span>{step === 1 ? 'Target Exam' : step === 2 ? 'Target Year & Focus' : 'Experience & College'}</span>
          </div>
          <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-sky-400 to-indigo-500 transition-all duration-300 rounded-full"
              style={{ width: `${(step / 3) * 100}%` }}
            />
          </div>
        </div>

        {/* STEP 1: Target Exam */}
        {step === 1 && (
          <div className="space-y-6 animate-fade-in">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-semibold mb-2">
                <Sparkles className="h-3 w-3" /> Medical Specialization
              </div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">
                What medical examination are you preparing for?
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                We calibrate difficulty levels, question distributions, and high-yield citations according to your exam.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {examOptions.map((opt) => {
                const Icon = opt.icon;
                const isSelected = targetExam === opt.id;
                return (
                  <div
                    key={opt.id}
                    onClick={() => setTargetExam(opt.id)}
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
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">{opt.desc}</p>
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end pt-4">
              <Button variant="gradient" onClick={() => setStep(2)} className="gap-2 px-6 h-11">
                <span>Continue</span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* STEP 2: Target Year & Subspecialty Focus */}
        {step === 2 && (
          <div className="space-y-6 animate-fade-in">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
                <Calendar className="h-3 w-3" /> Timeline & Subspecialty
              </div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">
                When is your target attempt?
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                We'll generate a personalized revision countdown and daily spaced-repetition plan.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Target Attempt Year</label>
                <div className="grid grid-cols-3 gap-3">
                  {[2026, 2027, 2028].map((yr) => (
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

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Primary Focus Subspecialty</label>
                <select
                  value={primarySpeciality}
                  onChange={(e) => setPrimarySpeciality(e.target.value)}
                  className="w-full h-11 px-3.5 rounded-xl bg-slate-950/70 border border-white/10 text-white text-sm focus:outline-none focus:border-sky-500 transition-colors"
                >
                  <option value="Pathology">General & Surgical Pathology</option>
                  <option value="Oncopathology">Oncopathology & Tumor Markers</option>
                  <option value="Hematopathology">Hematopathology & Flow Cytometry</option>
                  <option value="Molecular Pathology">Molecular Genetics & IHC</option>
                  <option value="GI Pathology">Gastrointestinal & Liver Pathology</option>
                </select>
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
              <Button variant="gradient" onClick={() => setStep(3)} className="gap-2 px-6 h-11">
                <span>Continue</span>
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
                <Building2 className="h-3 w-3" /> Medical Profile
              </div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">
                Tell us about your medical background
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                This helps us benchmark your performance and percentile against peer resident cohorts.
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
                <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                <span>{loading ? 'Personalizing...' : 'Launch Personalized Hub'}</span>
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
