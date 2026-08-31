/**
 * apps/mobile/app/(auth)/login.tsx
 *
 * Doctor sign-in screen with email credentials and Google identity options.
 */

import React, { useRef, useState } from 'react';
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
import Constants from 'expo-constants';
import { Stethoscope, Lock, Mail, AlertCircle, Sparkles } from 'lucide-react-native';
import { useAuth } from '../../lib/auth/auth-context';
import { Button } from '../../components/ui/Button';
import { validateLoginInput } from '@medical/shared';

export default function LoginScreen() {
  const router = useRouter();
  const { login, googleSignIn } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const googleSignInInProgress = useRef(false);
  const googleIosClientId = process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID;
  const googleWebClientId = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID;

  const handleLogin = async () => {
    const validation = validateLoginInput({ email, password });
    if (!validation.success) {
      setError(validation.error);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await login(validation.data.email, validation.data.password);
      // NavigationGuard will automatically route to /onboarding or /(tabs)
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please check your medical credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError(null);
    if (Constants.appOwnership === 'expo') {
      setError('Google Sign-In requires a development or preview build; it is not available in Expo Go.');
      return;
    }
    if (!googleWebClientId) {
      setError('Google Sign-In is missing EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID in this build.');
      return;
    }
    if (googleSignInInProgress.current) {
      return;
    }
    googleSignInInProgress.current = true;
    setLoading(true);
    try {
      const {
        GoogleSignin,
        isSuccessResponse,
      } = await import('@react-native-google-signin/google-signin');

      GoogleSignin.configure({
        webClientId: googleWebClientId,
        iosClientId: Platform.OS === 'ios' ? googleIosClientId : undefined,
        offlineAccess: false,
      });

      if (Platform.OS === 'android') {
        await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
      }

      const response = await GoogleSignin.signIn();
      if (!isSuccessResponse(response)) return;

      const idToken = response.data.idToken || (await GoogleSignin.getTokens()).idToken;
      if (!idToken) {
        throw new Error('Google did not return an ID token. Confirm that the configured client ID is a Web OAuth client.');
      }
      await googleSignIn(idToken);
    } catch (err: any) {
      const nativeCode = String(err?.code ?? '');
      if (nativeCode === '10' || nativeCode === 'DEVELOPER_ERROR') {
        setError(
          'Google rejected this Android build. Match package ai.docedge.student and the EAS signing SHA-1 in the Google Android OAuth client.'
        );
      } else if (nativeCode === '7' || nativeCode === 'NETWORK_ERROR') {
        setError('Google Sign-In could not reach Google. Check the phone network and try again.');
      } else {
        setError(err?.message || 'Google Sign-In failed.');
      }
    } finally {
      googleSignInInProgress.current = false;
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
          {/* Brand Header */}
          <View style={styles.brandHeader}>
            <View style={styles.iconCircle}>
              <Stethoscope size={28} color="#38bdf8" />
            </View>
            <Text style={styles.brandTitle}>DocEdge AI</Text>
            <Text style={styles.brandSubtitle}>Medical Exam Intelligence</Text>
            <Text style={styles.tagline}>
              High-yield question banks, adaptive mock exams & topic mastery for PG/SS preparation.
            </Text>
          </View>

          {/* Error Banner */}
          {error ? (
            <View style={styles.errorBox}>
              <AlertCircle size={16} color="#f43f5e" style={{ marginRight: 8 }} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          {/* Form */}
          <View style={styles.formCard}>
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Doctor / Medical Email</Text>
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
              <Text style={styles.inputLabel}>Password</Text>
              <View style={styles.inputWrapper}>
                <Lock size={18} color="#64748b" style={styles.inputIcon} />
                <TextInput
                  style={styles.textInput}
                  placeholder="••••••••••••"
                  placeholderTextColor="#475569"
                  secureTextEntry
                  value={password}
                  onChangeText={setPassword}
                />
              </View>
            </View>

            <Button
              title="Sign In"
              onPress={handleLogin}
              loading={loading}
              variant="primary"
              size="lg"
              style={{ marginTop: 8 }}
            />

            <View style={styles.dividerRow}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>or continue with</Text>
              <View style={styles.dividerLine} />
            </View>

            <Button
              title="Sign in with Google"
              variant="outline"
              size="md"
              disabled={loading}
              onPress={handleGoogleSignIn}
              icon={<Sparkles size={16} color="#38bdf8" />}
            />
          </View>

          {/* Bottom Switch to Register */}
          <View style={styles.footerRow}>
            <Text style={styles.footerText}>New to DocEdge? </Text>
            <TouchableOpacity onPress={() => router.push('/(auth)/signup' as any)}>
              <Text style={styles.footerLink}>Create Doctor Account</Text>
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
    marginBottom: 28,
  },
  iconCircle: {
    width: 60,
    height: 60,
    borderRadius: 20,
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    borderWidth: 1.5,
    borderColor: 'rgba(56, 189, 248, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  brandTitle: {
    fontSize: 26,
    fontWeight: '900',
    color: '#ffffff',
    letterSpacing: -0.5,
  },
  brandSubtitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#38bdf8',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 2,
  },
  tagline: {
    fontSize: 12,
    color: '#94a3b8',
    textAlign: 'center',
    lineHeight: 18,
    marginTop: 8,
    maxWidth: 280,
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
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 18,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#334155',
  },
  dividerText: {
    fontSize: 11,
    color: '#64748b',
    fontWeight: '600',
    paddingHorizontal: 12,
    textTransform: 'uppercase',
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
