/**
 * packages/shared/src/types/auth.ts
 *
 * Authentication, Session & User Profile Types.
 */

export type UserRole = 'SUPER_ADMIN' | 'ADMIN' | 'REVIEWER' | 'EDUCATOR' | 'USER';

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  avatar_url?: string | null;
  target_exam?: string | null;
  target_year?: number | null;
  medical_college?: string | null;
  residency_stage?: string | null;
  primary_speciality?: string | null;
  current_streak?: number;
  longest_streak?: number;
  is_email_verified?: boolean;
  has_password?: boolean;
}

export interface AdminUserListItem {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_email_verified: boolean;
  is_active: boolean;
  is_protected: boolean;
  target_exam?: string | null;
  residency_stage?: string | null;
  medical_college?: string | null;
  created_at: string;
  total_attempts: number;
}

export interface ListUsersResponse {
  total: number;
  page: number;
  limit: number;
  items: AdminUserListItem[];
}

export interface AuthSessionResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  is_new_user?: boolean;
  user: UserProfile;
}

export interface PasswordEntropyResult {
  entropy_bits: number;
  score: number;
  strength: 'WEAK' | 'MODERATE' | 'STRONG' | 'VERY_STRONG';
  feedback: string[];
  is_acceptable: boolean;
}

export interface GuestSessionResponse {
  guest_session_token: string;
  expires_at: string;
}

export interface MergeGuestResponse {
  success: boolean;
  user_id: string;
  migrated_attempts_count: number;
  migrated_answers_count: number;
}
