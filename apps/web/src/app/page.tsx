'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { assessmentsApi } from '@medical/api-client';
import { LandingPageRenderer } from '@/components/cms/landing-page-renderer';
import { landingPageContent } from '@/lib/cms/content';
import { useAuth } from '@/lib/auth-context';

export default function LandingPage() {
  const router = useRouter();
  const { user, getOrCreateGuestSession } = useAuth();
  const [startingDiagnostic, setStartingDiagnostic] = useState(false);

  const handleLaunchDiagnostic = async (questionCount: number, durationMinutes: number) => {
    setStartingDiagnostic(true);
    try {
      if (!user) await getOrCreateGuestSession();
      const assessment = await assessmentsApi.createAssessment({
        title: `${questionCount}-Question Rapid Diagnostic Assessment`,
        type: 'CUSTOM',
        question_count: questionCount,
        duration_seconds: durationMinutes * 60,
        blueprint: {
          difficulty_distribution: questionCount === 5
            ? { easy: 1, medium: 3, hard: 1 }
            : { medium: questionCount },
        },
      });
      const attempt = await assessmentsApi.startAttempt(assessment.assessment_id);
      router.push(`/student/exam/${attempt.attempt_id}`);
    } catch (error) {
      console.error('Failed to launch diagnostic:', error);
      router.push('/student');
    } finally {
      setStartingDiagnostic(false);
    }
  };

  return (
    <div className="relative overflow-hidden">
      <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] rounded-full bg-sky-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute top-[20%] right-[10%] w-[600px] h-[600px] rounded-full bg-indigo-500/10 blur-[140px] pointer-events-none" />
      <LandingPageRenderer
        document={landingPageContent}
        isAuthenticated={Boolean(user)}
        diagnosticLoading={startingDiagnostic}
        onStartDiagnostic={handleLaunchDiagnostic}
      />
    </div>
  );
}
