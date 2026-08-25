'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { AuthModal } from '@/components/auth/auth-modal';

export default function SignUpPage() {
  const router = useRouter();

  return (
    <AuthModal
      isOpen={true}
      initialMode="register"
      onClose={() => router.push('/')}
      onSuccess={() => router.push('/onboarding')}
    />
  );
}
