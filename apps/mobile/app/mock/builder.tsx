/**
 * apps/mobile/app/mock/builder.tsx
 *
 * Marrow-grade Custom Test & QBank Module Builder.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Sliders, Play } from 'lucide-react-native';
import { useAuth } from '../../lib/auth/auth-context';
import { assessmentsApi, questionsApi, TopicCountItem } from '@medical/api-client';
import { Header } from '../../components/ui/Header';
import { Button } from '../../components/ui/Button';

export default function MockBuilderScreen() {
  const router = useRouter();
  const { user } = useAuth();

  const [title, setTitle] = useState('');
  const [questionCount, setQuestionCount] = useState<number>(20);
  const [difficulty, setDifficulty] = useState<string>('ALL');
  const [mode, setMode] = useState<'MOCK' | 'PRACTICE'>('MOCK');
  const [selectedTopic, setSelectedTopic] = useState<string>('ALL');
  const [topics, setTopics] = useState<TopicCountItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    questionsApi
      .listTopics()
      .then(setTopics)
      .catch(() => {});
  }, []);

  const handleCreateMock = async () => {
    setLoading(true);
    try {
      const blueprint: Record<string, any> = {};
      if (selectedTopic !== 'ALL') blueprint.topic = selectedTopic;
      if (difficulty !== 'ALL') blueprint.difficulty = difficulty.toLowerCase();

      const assessment = await assessmentsApi.createAssessment({
        title: title.trim() || `${user?.target_exam || 'NEET-SS'} Custom Mock`,
        type: mode === 'PRACTICE' ? 'PRACTICE' : 'CUSTOM',
        question_count: questionCount,
        duration_seconds: mode === 'PRACTICE' ? 7200 : questionCount * 60,
        blueprint,
      });

      const attempt = await assessmentsApi.startAttempt(assessment.assessment_id, user?.id);
      router.replace(`/exam/${attempt.attempt_id}` as any);
    } catch (err) {
      console.error('Failed to create custom test:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <Header
        title="Custom Module Builder"
        subtitle="Configure Custom Test & Blueprint"
        onBack={() => router.back()}
      />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Module Title */}
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Module Name (Optional)</Text>
          <TextInput
            style={styles.textInput}
            placeholder="e.g. Oncopathology & IHC Speed Drill"
            placeholderTextColor="#64748b"
            value={title}
            onChangeText={setTitle}
          />
        </View>

        {/* Number of Questions */}
        <Text style={styles.inputLabel}>Number of Questions</Text>
        <View style={styles.chipRow}>
          {[10, 20, 50, 100, 150].map((count) => (
            <TouchableOpacity
              key={count}
              onPress={() => setQuestionCount(count)}
              style={[styles.chipPill, questionCount === count ? styles.chipActive : null]}
            >
              <Text
                style={[styles.chipText, questionCount === count ? styles.chipTextActive : null]}
              >
                {count} MCQs
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Exam Mode */}
        <Text style={styles.inputLabel}>Mode</Text>
        <View style={styles.modeRow}>
          <TouchableOpacity
            onPress={() => setMode('MOCK')}
            style={[styles.modeCard, mode === 'MOCK' ? styles.modeCardActive : null]}
          >
            <Text style={[styles.modeTitle, mode === 'MOCK' ? styles.textSky : null]}>
              Timed Exam Mode
            </Text>
            <Text style={styles.modeSub}>Countdown timer, strict submission & scorecard</Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => setMode('PRACTICE')}
            style={[styles.modeCard, mode === 'PRACTICE' ? styles.modeCardActive : null]}
          >
            <Text style={[styles.modeTitle, mode === 'PRACTICE' ? styles.textSky : null]}>
              Practice Mode
            </Text>
            <Text style={styles.modeSub}>Untimed self-paced study with instant answers</Text>
          </TouchableOpacity>
        </View>

        {/* Difficulty */}
        <Text style={styles.inputLabel}>Difficulty Filter</Text>
        <View style={styles.chipRow}>
          {['ALL', 'EASY', 'MEDIUM', 'HARD'].map((diff) => (
            <TouchableOpacity
              key={diff}
              onPress={() => setDifficulty(diff)}
              style={[styles.chipPill, difficulty === diff ? styles.chipActive : null]}
            >
              <Text
                style={[styles.chipText, difficulty === diff ? styles.chipTextActive : null]}
              >
                {diff === 'ALL' ? 'Balanced' : diff.charAt(0) + diff.slice(1).toLowerCase()}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Topic Selector */}
        <Text style={styles.inputLabel}>Target Topic / System</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.topicScroll}>
          <TouchableOpacity
            onPress={() => setSelectedTopic('ALL')}
            style={[styles.topicChip, selectedTopic === 'ALL' ? styles.chipActive : null]}
          >
            <Text style={[styles.chipText, selectedTopic === 'ALL' ? styles.chipTextActive : null]}>
              All Pathology Topics
            </Text>
          </TouchableOpacity>

          {topics.map((t, idx) => (
            <TouchableOpacity
              key={idx}
              onPress={() => setSelectedTopic(t.name)}
              style={[styles.topicChip, selectedTopic === t.name ? styles.chipActive : null]}
            >
              <Text
                style={[styles.chipText, selectedTopic === t.name ? styles.chipTextActive : null]}
              >
                {t.name} ({t.count})
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <Button
          title={`Start ${questionCount}-Question Module`}
          variant="gradient"
          size="lg"
          loading={loading}
          onPress={handleCreateMock}
          icon={<Play size={16} color="#ffffff" fill="#ffffff" />}
          style={{ marginTop: 24 }}
        />
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
    padding: 18,
    paddingBottom: 36,
  },
  inputGroup: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: '#cbd5e1',
    marginBottom: 8,
    marginTop: 6,
  },
  textInput: {
    backgroundColor: '#0f172a',
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: '#334155',
    height: 48,
    paddingHorizontal: 14,
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 16,
  },
  chipPill: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: '#0f172a',
    borderWidth: 1.5,
    borderColor: '#334155',
  },
  chipActive: {
    borderColor: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
  },
  chipText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#94a3b8',
  },
  chipTextActive: {
    color: '#38bdf8',
  },
  modeRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 16,
  },
  modeCard: {
    flex: 1,
    backgroundColor: '#0f172a',
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: '#334155',
    padding: 12,
  },
  modeCardActive: {
    borderColor: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
  },
  modeTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 4,
  },
  modeSub: {
    fontSize: 10,
    color: '#94a3b8',
    lineHeight: 14,
  },
  topicScroll: {
    marginBottom: 16,
  },
  topicChip: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: '#0f172a',
    borderWidth: 1.5,
    borderColor: '#334155',
    marginRight: 8,
  },
  textSky: {
    color: '#38bdf8',
  },
});
