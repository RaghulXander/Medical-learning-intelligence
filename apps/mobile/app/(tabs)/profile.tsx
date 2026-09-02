/**
 * apps/mobile/app/(tabs)/profile.tsx
 *
 * Doctor Profile, Target Examination Config, and Account Settings.
 */

import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
  Linking,
} from 'react-native';
import { useRouter } from 'expo-router';
import {
  User,
  Sliders,
  Flame,
  Award,
  LogOut,
  ShieldCheck,
  ChevronRight,
  BookOpen,
  Trash2,
  ExternalLink,
  FileText,
  ShieldAlert,
} from 'lucide-react-native';
import { useAuth } from '../../lib/auth/auth-context';
import { authApi } from '@medical/api-client';
import { Header } from '../../components/ui/Header';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out of DocEdge?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: async () => {
          await logout();
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      'Delete Account & Data',
      'This will permanently delete your account, authentication sessions, and individual learning records in accordance with GDPR/CCPA. This action cannot be undone.\n\nAre you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete Forever',
          style: 'destructive',
          onPress: () => {
            Alert.alert(
              'Final Confirmation',
              'Are you absolutely certain? All preparation history and streaks will be immediately purged.',
              [
                { text: 'Cancel', style: 'cancel' },
                {
                  text: 'Yes, Permanently Delete',
                  style: 'destructive',
                  onPress: async () => {
                    try {
                      await authApi.deleteAccount();
                      await logout();
                      Alert.alert(
                        'Account Deleted',
                        'Your account and data have been permanently removed.'
                      );
                    } catch (err: any) {
                      Alert.alert(
                        'Error',
                        err?.message || 'Failed to delete account. Please try again or contact support.'
                      );
                    }
                  },
                },
              ]
            );
          },
        },
      ]
    );
  };

  const openWebUrl = async (url: string) => {
    try {
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
      } else {
        Alert.alert('Notice', `Please visit ${url} in your web browser.`);
      }
    } catch {
      Alert.alert('Notice', `Please visit ${url} in your web browser.`);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <Header title="Doctor Profile" subtitle="Account & Target Settings" />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* User Card */}
        <Card style={styles.userCard} variant="highlight">
          <View style={styles.userRow}>
            <View style={styles.avatarBox}>
              <Text style={styles.avatarText}>
                {user?.name ? user.name.charAt(0).toUpperCase() : 'D'}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Text style={styles.userName}>{user?.name || 'Dr. Medical Resident'}</Text>
                {user?.role === 'SUPER_ADMIN' ? (
                  <Badge label="Super Admin" variant="purple" />
                ) : null}
              </View>
              <Text style={styles.userEmail}>{user?.email}</Text>
              <Text style={styles.userStage}>
                {user?.residency_stage || 'Resident'} • {user?.medical_college || 'Medical College'}
              </Text>
            </View>
          </View>
        </Card>

        {/* Target Examination Settings Card */}
        <Text style={styles.sectionHeading}>Target Examination</Text>
        <Card style={styles.settingsCard}>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => router.push('/onboarding' as any)}
            style={styles.settingItem}
          >
            <View style={styles.settingLeft}>
              <Sliders size={20} color="#38bdf8" />
              <View>
                <Text style={styles.settingTitle}>Current Target Exam</Text>
                <Text style={styles.settingValue}>
                  {user?.target_exam || 'NEET_SS'} ({user?.target_year || 2026})
                </Text>
              </View>
            </View>
            <ChevronRight size={18} color="#64748b" />
          </TouchableOpacity>

          <View style={styles.divider} />

          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => router.push('/onboarding' as any)}
            style={styles.settingItem}
          >
            <View style={styles.settingLeft}>
              <Award size={20} color="#38bdf8" />
              <View>
                <Text style={styles.settingTitle}>Curriculum Track / Speciality</Text>
                <Text style={styles.settingValue}>
                  {user?.primary_speciality || 'Oncopathology'}
                </Text>
              </View>
            </View>
            <ChevronRight size={18} color="#64748b" />
          </TouchableOpacity>
        </Card>

        {/* Streak & Consistency */}
        <Text style={styles.sectionHeading}>Preparation Consistency</Text>
        <Card style={styles.streakCard}>
          <View style={styles.streakRow}>
            <View style={styles.streakIconBox}>
              <Flame size={24} color="#f59e0b" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.streakTitle}>{user?.current_streak || 0} Days Active Streak</Text>
              <Text style={styles.streakSub}>
                Longest streak: {user?.longest_streak || user?.current_streak || 0} days
              </Text>
            </View>
          </View>
        </Card>

        {/* Legal, Privacy & Safety (Milestone 17.2) */}
        <Text style={styles.sectionHeading}>Privacy & Compliance</Text>
        <Card style={styles.settingsCard}>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => openWebUrl('https://medexam.ai/legal/privacy')}
            style={styles.settingItem}
          >
            <View style={styles.settingLeft}>
              <ShieldCheck size={20} color="#10b981" />
              <View>
                <Text style={styles.settingTitle}>Privacy Policy</Text>
                <Text style={styles.settingValue}>Zero patient data • Encrypted storage</Text>
              </View>
            </View>
            <ExternalLink size={16} color="#64748b" />
          </TouchableOpacity>

          <View style={styles.divider} />

          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => openWebUrl('https://medexam.ai/legal/terms')}
            style={styles.settingItem}
          >
            <View style={styles.settingLeft}>
              <FileText size={20} color="#38bdf8" />
              <View>
                <Text style={styles.settingTitle}>Terms & Medical Disclaimer</Text>
                <Text style={styles.settingValue}>Strictly educational exam preparation</Text>
              </View>
            </View>
            <ExternalLink size={16} color="#64748b" />
          </TouchableOpacity>

          <View style={styles.divider} />

          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => openWebUrl('https://medexam.ai/legal/account-deletion')}
            style={styles.settingItem}
          >
            <View style={styles.settingLeft}>
              <ShieldAlert size={20} color="#f59e0b" />
              <View>
                <Text style={styles.settingTitle}>Data Erasure Rights</Text>
                <Text style={styles.settingValue}>Public deletion instructions & policies</Text>
              </View>
            </View>
            <ExternalLink size={16} color="#64748b" />
          </TouchableOpacity>
        </Card>

        {/* Account Management & Deletion */}
        <Text style={styles.sectionHeading}>Account Operations</Text>
        <Card style={styles.settingsCard}>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={handleDeleteAccount}
            style={styles.settingItem}
          >
            <View style={styles.settingLeft}>
              <Trash2 size={20} color="#ef4444" />
              <View>
                <Text style={[styles.settingTitle, { color: '#f87171' }]}>Delete Account & Data</Text>
                <Text style={styles.settingValue}>Irrevocably erase profile, streaks, and sessions</Text>
              </View>
            </View>
            <ChevronRight size={18} color="#64748b" />
          </TouchableOpacity>
        </Card>

        {/* Sign Out Button */}
        <Button
          title="Sign Out"
          variant="secondary"
          size="lg"
          onPress={handleLogout}
          icon={<LogOut size={18} color="#94a3b8" />}
          style={{ marginTop: 12 }}
        />

        {/* Release Diagnostics Footer (Milestone 17.1) */}
        <View style={styles.footerContainer}>
          <Text style={styles.footerVersion}>DocEdge Android Beta v1.0.1 (Build 12)</Text>
          <Text style={styles.footerChannel}>Channel: github-beta • Educational Use Only</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#020617',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
  },
  userCard: {
    marginBottom: 20,
    backgroundColor: '#0f172a',
  },
  userRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  avatarBox: {
    width: 54,
    height: 54,
    borderRadius: 18,
    backgroundColor: '#0284c7',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 22,
    fontWeight: '900',
    color: '#ffffff',
  },
  userName: {
    fontSize: 17,
    fontWeight: '800',
    color: '#ffffff',
  },
  userEmail: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 1,
  },
  userStage: {
    fontSize: 11,
    color: '#38bdf8',
    fontWeight: '600',
    marginTop: 4,
  },
  sectionHeading: {
    fontSize: 14,
    fontWeight: '800',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
    marginTop: 6,
  },
  settingsCard: {
    backgroundColor: '#0f172a',
    padding: 6,
    marginBottom: 16,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  settingTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#ffffff',
  },
  settingValue: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 1,
  },
  divider: {
    height: 1,
    backgroundColor: '#1e293b',
    marginHorizontal: 12,
  },
  streakCard: {
    backgroundColor: '#0f172a',
    marginBottom: 16,
  },
  streakRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  streakIconBox: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  streakTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ffffff',
  },
  streakSub: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 1,
  },
  footerContainer: {
    marginTop: 32,
    alignItems: 'center',
    paddingVertical: 12,
  },
  footerVersion: {
    fontSize: 12,
    fontWeight: '700',
    color: '#64748b',
    letterSpacing: 0.3,
  },
  footerChannel: {
    fontSize: 11,
    color: '#475569',
    marginTop: 4,
  },
});
