import type { UserProfile } from '../types/auth';

export interface LoginInput {
  email: string;
  password: string;
}

export interface RegistrationInput extends LoginInput {
  name: string;
  target_exam?: string;
  residency_stage?: string;
  medical_college?: string;
  primary_speciality?: string;
}

export type AuthDestination = 'ONBOARDING' | 'STUDENT_HOME';

export type AuthValidationResult<T> =
  | { success: true; data: T }
  | { success: false; error: string };

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function validateLoginInput(
  input: LoginInput
): AuthValidationResult<LoginInput> {
  const email = normalizeEmail(input.email);
  if (!email || !input.password) {
    return { success: false, error: 'Please enter both email and password.' };
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { success: false, error: 'Please enter a valid email address.' };
  }
  return { success: true, data: { email, password: input.password } };
}

export function validateRegistrationInput(
  input: RegistrationInput
): AuthValidationResult<RegistrationInput> {
  const login = validateLoginInput(input);
  if (!login.success) return login;

  const name = input.name.trim();
  if (!name) {
    return { success: false, error: 'Please enter your name.' };
  }

  return {
    success: true,
    data: {
      ...input,
      ...login.data,
      name,
      medical_college: input.medical_college?.trim() || undefined,
    },
  };
}

export function isOnboardingComplete(
  user: Pick<UserProfile, 'residency_stage' | 'target_exam'> | null | undefined
): boolean {
  return Boolean(user?.residency_stage && user?.target_exam);
}

export function getPostAuthDestination(
  user: Pick<UserProfile, 'residency_stage' | 'target_exam'> | null | undefined,
  isNewUser = false
): AuthDestination {
  return isNewUser || !isOnboardingComplete(user) ? 'ONBOARDING' : 'STUDENT_HOME';
}
