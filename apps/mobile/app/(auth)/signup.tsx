/**
 * apps/mobile/app/(auth)/signup.tsx
 *
 * Doctor registration screen with strong password generator and exam track initialization.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Stethoscope, Lock, Mail, User, Sparkles, AlertCircle } from 'lucide-react-native';
import { useAuth } from '../../lib/auth/auth-context';
import { authApi } from '@medical/api-client';
import { validateRegistrationInput } from '@medical/shared';
import { Button } from '../../components/ui/Button';

export default function SignupScreen() {
  const router = useRouter();
  const { register } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSuggestPassword = async () => {
    try {
      const res = await authApi.generatePassword(16);
      setPassword(res.password);
    } catch {
      setPassword('DocEdge#2026!Exam');
    }
  };

  const handleSignup = async () => {
    const validation = validateRegistrationInput({
      email,
      password,
      name,
      target_exam: 'NEET_SS',
      primary_speciality: 'Oncopathology',
    });
    if (!validation.success) {
      setError(validation.error);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await register(validation.data);
      // Automatically routed to /onboarding
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please check your details.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
          <View style={styles.brandHeader}>
            <View style={styles.iconCircle}>
              <Stethoscope size={28} color="#38bdf8" />
            </View>
            <Text style={styles.brandTitle}>Join DocEdge</Text>
            <Text style={styles.brandSubtitle}>Create Doctor Account</Text>
          </View>

          {error ? (
            <View style={styles.errorBox}>
              <AlertCircle size={16} color="#f43f5e" style={{ marginRight: 8 }} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <View style={styles.formCard}>
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Full Name / Title</Text>
              <View style={styles.inputWrapper}>
                <User size={18} color="#64748b" style={styles.inputIcon} />
                <TextInput
                  style={styles.textInput}
                  placeholder="Dr. Raghul Xander"
                  placeholderTextColor="#475569"
                  value={name}
                  onChangeText={setName}
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Doctor Email</Text>
              <View style={styles.inputWrapper}>
                <Mail size={18} color="#64748b" style={styles.inputIcon} />
                <TextInput
                  style={styles.textInput}
                  placeholder="doctor@hospital.org"
                  placeholderTextColor="#475569"
                  autoCapitalize="none"
                  keyboardType="email-address"
                  value={email}
                  onChangeText={setEmail}
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <View style={styles.passwordHeader}>
                <Text style={styles.inputLabel}>Password</Text>
                <TouchableOpacity onPress={handleSuggestPassword} style={styles.suggestBtn}>
                  <Sparkles size={12} color="#38bdf8" />
                  <Text style={styles.suggestText}>Suggest Strong</Text>
                </TouchableOpacity>
              </View>
              <View style={styles.inputWrapper}>
                <Lock size={18} color="#64748b" style={styles.inputIcon} />
                <TextInput
                  style={styles.textInput}
                  placeholder="••••••••••••"
                  placeholderTextColor="#475569"
                  value={password}
                  onChangeText={setPassword}
                />
              </View>
            </View>

            <Button
              title="Create Account & Start Onboarding"
              onPress={handleSignup}
              loading={loading}
              variant="primary"
              size="lg"
              style={{ marginTop: 10 }}
            />
          </View>

          <View style={styles.footerRow}>
            <Text style={styles.footerText}>Already registered? </Text>
            <TouchableOpacity onPress={() => router.push('/(auth)/login' as any)}>
              <Text style={styles.footerLink}>Sign In Here</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#020617',
  },
  scrollContent: {
    padding: 24,
    justifyContent: 'center',
    minHeight: '100%',
  },
  brandHeader: {
    alignItems: 'center',
    marginBottom: 24,
  },
  iconCircle: {
    width: 56,
    height: 56,
    borderRadius: 18,
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    borderWidth: 1.5,
    borderColor: 'rgba(56, 189, 248, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  brandTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#ffffff',
    letterSpacing: -0.5,
  },
  brandSubtitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#38bdf8',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 2,
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(244, 63, 94, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(244, 63, 94, 0.3)',
    padding: 12,
    borderRadius: 12,
    marginBottom: 16,
  },
  errorText: {
    flex: 1,
    fontSize: 12,
    color: '#fb7185',
    fontWeight: '600',
  },
  formCard: {
    backgroundColor: '#0f172a',
    borderRadius: 24,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  inputGroup: {
    marginBottom: 16,
  },
  passwordHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  suggestBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  suggestText: {
    fontSize: 11,
    color: '#38bdf8',
    fontWeight: '700',
  },
  inputLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#cbd5e1',
    marginBottom: 6,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#020617',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#334155',
    paddingHorizontal: 12,
    height: 48,
  },
  inputIcon: {
    marginRight: 10,
  },
  textInput: {
    flex: 1,
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  footerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 24,
  },
  footerText: {
    fontSize: 13,
    color: '#94a3b8',
  },
  footerLink: {
    fontSize: 13,
    color: '#38bdf8',
    fontWeight: '700',
  },
});
