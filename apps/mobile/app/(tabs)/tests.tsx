/**
 * apps/mobile/app/(tabs)/tests.tsx
 *
 * Marrow-grade Tests Hub with Preset Drills, Subject Tests, Grand Mocks,
 * and Custom Test Builder launcher.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Sliders, Sparkles, Trophy, Award, Zap } from 'lucide-react-native';
import { useAuth } from '../../lib/auth/auth-context';
import { assessmentsApi } from '@medical/api-client';
import { AssessmentPreset } from '@medical/shared';
import { Header } from '../../components/ui/Header';
import { QuickPresetCard } from '../../components/dashboard/QuickPresetCard';
import { Button } from '../../components/ui/Button';

export default function TestsScreen() {
  const router = useRouter();
  const { user } = useAuth();

  const [presets, setPresets] = useState<AssessmentPreset[]>([]);
  const [filter, setFilter] = useState<'ALL' | 'DAILY' | 'TOPIC' | 'MOCK'>('ALL');
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    assessmentsApi
      .listPresets()
      .then(setPresets)
      .catch((err) => console.warn('Presets note:', err));
  }, []);

  const handleLaunchPreset = async (presetId: string) => {
    setLoadingId(presetId);
    try {
      const attempt = await assessmentsApi.launchPreset(presetId, user?.id);
      router.push(`/exam/${attempt.attempt_id}` as any);
    } catch (err) {
      console.error('Failed to launch preset:', err);
    } finally {
      setLoadingId(null);
    }
  };

  const filteredPresets = presets.filter((p) => {
    if (filter === 'ALL') return true;
    return p.type === filter;
  });

  return (
    <SafeAreaView style={styles.safeArea}>
      <Header
        title="Assessment Series"
        subtitle={`${user?.target_exam || 'NEET-SS'} • Test Center`}
        rightElement={
          <TouchableOpacity
            onPress={() => router.push('/mock/builder' as any)}
            style={styles.buildIconBtn}
          >
            <Sliders size={18} color="#38bdf8" />
          </TouchableOpacity>
        }
      />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Custom Mock Builder Banner */}
        <TouchableOpacity
          activeOpacity={0.8}
          onPress={() => router.push('/mock/builder' as any)}
          style={styles.heroBanner}
        >
          <View style={styles.heroBannerContent}>
            <View style={styles.heroIconBox}>
              <Sliders size={22} color="#ffffff" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.heroTitle}>Create Custom Test</Text>
              <Text style={styles.heroSubtitle}>
                Select topics, 10 to 150 questions, difficulty & timer mode
              </Text>
            </View>
          </View>
        </TouchableOpacity>

        {/* Filter Pills */}
        <View style={styles.filterRow}>
          {(['ALL', 'DAILY', 'TOPIC', 'MOCK'] as const).map((f) => (
            <TouchableOpacity
              key={f}
              onPress={() => setFilter(f)}
              style={[styles.filterPill, filter === f ? styles.filterPillActive : null]}
            >
              <Text style={[styles.filterText, filter === f ? styles.filterTextActive : null]}>
                {f === 'ALL'
                  ? 'All Tests'
                  : f === 'DAILY'
                  ? 'Daily'
                  : f === 'TOPIC'
                  ? 'Subject Drills'
                  : 'Grand Mocks'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Test Cards List */}
        {filteredPresets.map((preset) => (
          <QuickPresetCard
            key={preset.id}
            title={preset.title}
            description={preset.description}
            questionCount={preset.question_count}
            durationSeconds={preset.duration_seconds}
            type={preset.type}
            loading={loadingId === preset.id}
            onPress={() => handleLaunchPreset(preset.id)}
          />
        ))}
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
  buildIconBtn: {
    padding: 8,
    borderRadius: 10,
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#334155',
  },
  heroBanner: {
    backgroundColor: '#0284c7', // Sky-600
    borderRadius: 20,
    padding: 18,
    marginBottom: 16,
    shadowColor: '#38bdf8',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 4,
  },
  heroBannerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  heroIconBox: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroTitle: {
    fontSize: 17,
    fontWeight: '900',
    color: '#ffffff',
  },
  heroSubtitle: {
    fontSize: 12,
    color: '#e0f2fe',
    marginTop: 2,
  },
  filterRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 16,
  },
  filterPill: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 999,
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#334155',
  },
  filterPillActive: {
    backgroundColor: '#0284c7',
    borderColor: '#38bdf8',
  },
  filterText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#94a3b8',
  },
  filterTextActive: {
    color: '#ffffff',
  },
});
