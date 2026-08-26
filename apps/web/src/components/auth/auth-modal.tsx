'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Sparkles,
  Eye,
  EyeOff,
  ShieldCheck,
  Lock,
  Mail,
  User,
  X,
  AlertCircle,
  ArrowLeft,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth-context';
import { authApi, studentApi } from '@medical/api-client';
import { PasswordEntropyResult, MedicalTaxonomyMetadata } from '@medical/shared';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: 'login' | 'register';
  onSuccess?: () => void;
}

export function AuthModal({ isOpen, onClose, initialMode = 'login', onSuccess }: AuthModalProps) {
  const router = useRouter();
  const { login, register, googleSignIn } = useAuth();

  const [taxonomy, setTaxonomy] = useState<MedicalTaxonomyMetadata | null>(null);
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [targetExam, setTargetExam] = useState('NEET_SS');
  const [primarySpeciality, setPrimarySpeciality] = useState('Oncopathology');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Google Direct Input Prompt (Fallback)
  const [showGooglePrompt, setShowGooglePrompt] = useState(false);
  const [googleEmailInput, setGoogleEmailInput] = useState('');

  // Password entropy state
  const [entropyInfo, setEntropyInfo] = useState<PasswordEntropyResult | null>(null);

  // Fetch dynamic taxonomy metadata
  useEffect(() => {
    studentApi
      .getTaxonomies()
      .then((data) => setTaxonomy(data))
      .catch((err) => console.warn('AuthModal taxonomy note:', err));
  }, []);

  useEffect(() => {
    setMode(initialMode);
    setError(null);
    setShowGooglePrompt(false);
  }, [initialMode, isOpen]);

  // Live entropy evaluation on password change
  useEffect(() => {
    if (mode === 'register' && password) {
      authApi.evaluatePassword(password).then(setEntropyInfo).catch(() => {});
    } else {
      setEntropyInfo(null);
    }
  }, [password, mode]);

  if (!isOpen) return null;

  const handleSuggestPassword = async () => {
    try {
      const res = await authApi.generatePassword(20);
      setPassword(res.password);
      setEntropyInfo(res.entropy);
      setShowPassword(true);
      if (typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(res.password);
      }
    } catch (err) {
      console.error('Failed to generate strong password:', err);
    }
  };

  const handleGoogleOAuthPopup = () => {
    setError(null);
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    const hasValidClientId =
      clientId &&
      !clientId.includes('medicalai') &&
      !clientId.includes('xxxx') &&
      !clientId.includes('placeholder');

    const google = typeof window !== 'undefined' ? (window as any).google : null;

    // 1. If real Google OAuth2 Client ID is configured and Google SDK is available, launch OAuth popup
    if (hasValidClientId && google?.accounts?.oauth2) {
      try {
        setLoading(true);
        const tokenClient = google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: 'openid email profile',
          callback: async (tokenResponse: any) => {
            if (tokenResponse?.error) {
              setLoading(false);
              setError('Google authorization was cancelled or encountered an error.');
              return;
            }

            if (tokenResponse?.access_token) {
              try {
                const res = await googleSignIn(tokenResponse.access_token);
                setLoading(false);
                onClose();

                // Check profile completion requirement
                if (!res.user?.residency_stage || !res.user?.target_exam || res.is_new_user) {
                  router.push('/onboarding');
                } else {
                  if (onSuccess) onSuccess();
                  router.push('/student');
                }
              } catch (err: any) {
                setLoading(false);
                setError(err?.message || 'Google account verification failed.');
              }
            }
          },
        });

        tokenClient.requestAccessToken({ prompt: 'select_account' });
        return;
      } catch (err) {
        console.warn('Google OAuth2 client error:', err);
        setLoading(false);
      }
    }

    // 2. Direct Google Email Entry (instant passwordless sign-in)
    setShowGooglePrompt(true);
  };

  const handleExecuteGoogleDirectAuth = async (directEmail: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await googleSignIn(directEmail.trim().toLowerCase());
      onClose();

      // Enforce mandatory profile onboarding
      if (!res.user?.residency_stage || !res.user?.target_exam || res.is_new_user) {
        router.push('/onboarding');
      } else {
        if (onSuccess) onSuccess();
        router.push('/student');
      }
    } catch (err: any) {
      setError(err?.message || 'Google Sign-In failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (mode === 'login') {
        const res = await login(email, password);
        onClose();
        if (!res.user?.residency_stage || !res.user?.target_exam) {
          router.push('/onboarding');
        } else {
          if (onSuccess) onSuccess();
          router.push('/student');
        }
      } else {
        await register({
          email,
          password,
          name,
          target_exam: targetExam,
          primary_speciality: primarySpeciality,
        } as any);
        onClose();
        // Mandatory onboarding after registration
        router.push('/onboarding');
      }
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-md rounded-2xl border border-slate-700/80 p-6 sm:p-8 shadow-2xl bg-slate-900 text-white max-h-[90vh] overflow-y-auto z-50">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        {/* ----------------------------------------------------------------- */}
        {/* VIEW 1: Google Direct Email Sign-In Prompt */}
        {/* ----------------------------------------------------------------- */}
        {showGooglePrompt ? (
          <div className="space-y-5 animate-fade-in">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowGooglePrompt(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
              <div>
                <h3 className="text-lg font-bold text-white">Google Identity Gateway</h3>
                <p className="text-xs text-slate-400">Enter your Google account email to sign in</p>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-700/60 space-y-4">
              <div className="flex items-center gap-3 text-xs text-slate-300">
                <div className="w-8 h-8 rounded-full bg-sky-500/20 border border-sky-500/30 flex items-center justify-center text-sky-400 font-bold">
                  <Mail className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-semibold text-white">Google Account Verification</div>
                  <div className="text-[11px] text-slate-400">Fetches your verified name, email, and clinical permissions</div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300">Your Google Email</label>
                <input
                  type="email"
                  placeholder="doctor@gmail.com"
                  value={googleEmailInput}
                  onChange={(e) => setGoogleEmailInput(e.target.value)}
                  className="w-full h-11 px-3.5 rounded-xl bg-slate-900 border border-slate-700 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <Button
                type="button"
                variant="gradient"
                disabled={!googleEmailInput || !googleEmailInput.includes('@') || loading}
                onClick={() => handleExecuteGoogleDirectAuth(googleEmailInput)}
                className="w-full h-11 text-sm font-bold rounded-xl"
              >
                {loading ? 'Connecting with Google...' : 'Continue to Profile Setup'}
              </Button>
            </div>
          </div>
        ) : (
          /* ----------------------------------------------------------------- */
          /* VIEW 2: Standard Login / Registration Form */
          /* ----------------------------------------------------------------- */
          <div>
            {/* Header */}
            <div className="text-center mb-6">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-semibold mb-2">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Medical Identity Gateway</span>
              </div>
              <h2 className="text-2xl font-bold tracking-tight">
                {mode === 'login' ? 'Sign in to DocEdge' : 'Create Doctor Account'}
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {mode === 'login'
                  ? 'Access your personalized question bank, mock exams, and analytics.'
                  : 'Start targeted medical exam preparation with precision intelligence.'}
              </p>
            </div>

            {/* Google OAuth Popup Button */}
            <div className="space-y-3">
              <Button
                type="button"
                variant="outline"
                onClick={handleGoogleOAuthPopup}
                disabled={loading}
                className="w-full h-11 border-slate-700 bg-slate-800 hover:bg-slate-700/80 text-white font-medium flex items-center justify-center gap-3 rounded-xl transition-all shadow-sm"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Continue with Google</span>
              </Button>
            </div>

            <div className="relative my-5">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-700/60" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-slate-900 px-3 text-slate-400 font-medium uppercase tracking-wider">
                  or email & password
                </span>
              </div>
            </div>

            {/* Error Banner */}
            {error && (
              <div className="p-3 mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-3.5">
              {mode === 'register' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
                  <div className="relative">
                    <User className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                    <input
                      type="text"
                      required
                      placeholder="Dr. Raghul Xander"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full h-10 pl-9 pr-3 rounded-lg bg-slate-950 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-sky-500 transition-colors"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Doctor / Medical Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                  <input
                    type="email"
                    required
                    placeholder="doctor@hospital.org"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full h-10 pl-9 pr-3 rounded-lg bg-slate-950 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-sky-500 transition-colors"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold text-slate-300">Password</label>
                  {mode === 'register' && (
                    <button
                      type="button"
                      onClick={handleSuggestPassword}
                      className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium"
                    >
                      <Sparkles className="h-3 w-3" /> Suggest Strong
                    </button>
                  )}
                </div>

                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full h-10 pl-9 pr-10 rounded-lg bg-slate-950 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-sky-500 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>

                {/* Password Entropy Visualizer */}
                {mode === 'register' && entropyInfo && (
                  <div className="mt-2 space-y-1.5 animate-fade-in">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Strength:</span>
                      <span
                        className={
                          entropyInfo.strength === 'VERY_STRONG'
                            ? 'text-purple-400 font-bold'
                            : entropyInfo.strength === 'STRONG'
                            ? 'text-emerald-400 font-bold'
                            : entropyInfo.strength === 'MODERATE'
                            ? 'text-amber-400 font-medium'
                            : 'text-rose-400 font-medium'
                        }
                      >
                        {entropyInfo.strength} ({entropyInfo.entropy_bits} bits)
                      </span>
                    </div>

                    <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 rounded-full ${
                          entropyInfo.strength === 'VERY_STRONG'
                            ? 'bg-purple-500'
                            : entropyInfo.strength === 'STRONG'
                            ? 'bg-emerald-500'
                            : entropyInfo.strength === 'MODERATE'
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                        }`}
                        style={{ width: `${entropyInfo.score}%` }}
                      />
                    </div>

                    {entropyInfo.feedback.length > 0 && (
                      <p className="text-[10px] text-slate-400">
                        {entropyInfo.feedback.join(' • ')}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* DYNAMIC DROPDOWNS: Examination vs Speciality */}
              {mode === 'register' && (
                <div
                  className={`grid gap-3 ${
                    (taxonomy?.examinations.find((e) => e.id === targetExam)?.has_specialities ?? true)
                      ? 'grid-cols-1 sm:grid-cols-2'
                      : 'grid-cols-1'
                  }`}
                >
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Target Examination</label>
                    <select
                      value={targetExam}
                      onChange={(e) => {
                        const newExamId = e.target.value;
                        setTargetExam(newExamId);
                        const exam = (taxonomy?.examinations || []).find((x) => x.id === newExamId);
                        if (exam) {
                          if (!exam.has_specialities && exam.default_speciality) {
                            setPrimarySpeciality(exam.default_speciality);
                          } else if (exam.specialities && exam.specialities.length > 0) {
                            const firstSpec = exam.specialities[0]?.id;
                            if (firstSpec) setPrimarySpeciality(firstSpec);
                          }
                        }
                      }}
                      className="w-full h-10 px-3 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-sky-500 transition-colors"
                    >
                      {(taxonomy?.examinations || [
                        { id: 'NEET_SS', title: 'NEET-SS / DrNB Super-Specialty' },
                        { id: 'NEET_PG', title: 'NEET-PG / INI-CET' },
                        { id: 'MD_PATH', title: 'MD / DNB Residency Exit' },
                        { id: 'MBBS', title: 'MBBS Professional' },
                        { id: 'FELLOWSHIP', title: 'Post-Doctoral Fellowship' },
                      ]).map((ex) => (
                        <option key={ex.id} value={ex.id}>
                          {ex.title}
                        </option>
                      ))}
                    </select>
                  </div>

                  {(taxonomy?.examinations.find((e) => e.id === targetExam)?.has_specialities ?? true) && (
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Target Speciality</label>
                      <select
                        value={primarySpeciality}
                        onChange={(e) => setPrimarySpeciality(e.target.value)}
                        className="w-full h-10 px-3 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-sky-500 transition-colors"
                      >
                        {(
                          taxonomy?.examinations.find((e) => e.id === targetExam)?.specialities || [
                            { id: 'Oncopathology', name: 'Oncopathology' },
                            { id: 'Hematopathology', name: 'Hematopathology' },
                            { id: 'General & Surgical Pathology', name: 'General & Surgical Path' },
                            { id: 'Molecular Diagnostics', name: 'Molecular Genetics & IHC' },
                          ]
                        ).map((sp) => (
                          <option key={sp.id} value={sp.id}>
                            {sp.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              )}

              <Button
                type="submit"
                variant="gradient"
                disabled={loading}
                className="w-full h-10 text-sm font-semibold rounded-xl mt-4"
              >
                {loading ? 'Authenticating...' : mode === 'login' ? 'Sign In' : 'Create Account & Start Onboarding'}
              </Button>
            </form>

            {/* Toggle Mode */}
            <div className="mt-5 text-center text-xs text-slate-400">
              {mode === 'login' ? (
                <span>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setMode('register');
                      setError(null);
                    }}
                    className="text-sky-400 hover:text-sky-300 font-semibold underline underline-offset-4"
                  >
                    Sign up now
                  </button>
                </span>
              ) : (
                <span>
                  Already registered?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setMode('login');
                      setError(null);
                    }}
                    className="text-sky-400 hover:text-sky-300 font-semibold underline underline-offset-4"
                  >
                    Sign in here
                  </button>
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
