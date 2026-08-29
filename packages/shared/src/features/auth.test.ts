import { describe, expect, it } from 'bun:test';

import {
  getPostAuthDestination,
  isOnboardingComplete,
  normalizeEmail,
  validateLoginInput,
  validateRegistrationInput,
} from './auth';

describe('shared authentication rules', () => {
  it('normalizes email consistently across clients', () => {
    expect(normalizeEmail('  Doctor@Example.COM ')).toBe('doctor@example.com');
  });

  it('rejects incomplete and invalid login input', () => {
    expect(validateLoginInput({ email: '', password: '' }).success).toBe(false);
    expect(validateLoginInput({ email: 'doctor', password: 'secret' }).success).toBe(false);
  });

  it('returns normalized valid login input', () => {
    expect(validateLoginInput({ email: ' Doctor@Example.COM ', password: 'secret' })).toEqual({
      success: true,
      data: { email: 'doctor@example.com', password: 'secret' },
    });
  });

  it('requires a registration name', () => {
    const result = validateRegistrationInput({
      email: 'doctor@example.com',
      password: 'secret',
      name: '   ',
    });
    expect(result).toEqual({ success: false, error: 'Please enter your name.' });
  });

  it('uses one onboarding completion rule', () => {
    expect(isOnboardingComplete(null)).toBe(false);
    expect(isOnboardingComplete({ residency_stage: 'resident', target_exam: null })).toBe(false);
    expect(isOnboardingComplete({ residency_stage: 'resident', target_exam: 'NEET_SS' })).toBe(true);
  });

  it('routes new or incomplete users to onboarding', () => {
    const complete = { residency_stage: 'resident', target_exam: 'NEET_SS' };
    expect(getPostAuthDestination(complete)).toBe('STUDENT_HOME');
    expect(getPostAuthDestination(complete, true)).toBe('ONBOARDING');
    expect(getPostAuthDestination({ residency_stage: null, target_exam: 'NEET_SS' })).toBe(
      'ONBOARDING'
    );
  });
});
