/**
 * apps/mobile/app/(tabs)/index.tsx
 *
 * Marrow-style Home Dashboard with Daily Goals, Active Attempt Resumption,
 * Weak Area Recommendations, and Quick Test Presets.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import {
  Flame,
  Play,
  RotateCcw,
  Sliders,
} from 'lucide-react-native';
import { useAuth } from '../../lib/auth/auth-context';
import { studentApi, assessmentsApi } from '@medical/api-client';
import {
  AssessmentPreset,
  ContinueLearningResponse,
  DailyQuizResponse,
  ExamReadinessResponse,
} from '@medical/shared';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { GoalProgressCard } from '../../components/dashboard/GoalProgressCard';
import { FocusAreaCard } from '../../components/dashboard/FocusAreaCard';
import { QuickPresetCard } from '../../components/dashboard/QuickPresetCard';

export default function HomeScreen() {
  const router = useRouter();
  const { user } = useAuth();

  const [refreshing, setRefreshing] = useState(false);
  const [presets, setPresets] = useState<AssessmentPreset[]>([]);
  const [dailyQuiz, setDailyQuiz] = useState<DailyQuizResponse | null>(null);
  const [continueData, setContinueData] = useState<ContinueLearningResponse | null>(null);
  const [readiness, setReadiness] = useState<ExamReadinessResponse | null>(null);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const presetsRes = await assessmentsApi.listPresets().catch(() => null);
      if (presetsRes) setPresets(presetsRes);

      if (user) {
        const [quizRes, contRes, readyRes] = await Promise.allSettled([
          studentApi.getDailyQuiz(),
          studentApi.getContinueLearning(),
          studentApi.getExamReadiness(),
        ]);

        if (quizRes.status === 'fulfilled') setDailyQuiz(quizRes.value);
        if (contRes.status === 'fulfilled') setContinueData(contRes.value);
        if (readyRes.status === 'fulfilled') setReadiness(readyRes.value);
      }
    } catch (err) {
      console.warn('Home data load notice:', err);
    }
  }, [user]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const handleLaunchPreset = async (presetId: string) => {
    setLoadingAction(presetId);
    try {
      const attempt = await assessmentsApi.launchPreset(presetId, user ? user.id : undefined);
      router.push(`/exam/${attempt.attempt_id}` as any);
    } catch (err) {
      console.error('Failed to launch preset:', err);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleLaunchTopicDrill = async (topicId: string, topicName: string) => {
    setLoadingAction(topicId);
    try {
      const assessment = await assessmentsApi.createAssessment({
        title: `${topicName} High-Yield Practice`,
        type: 'TOPIC',
        question_count: 10,
        blueprint: { topic: topicName },
      });
      const attempt = await assessmentsApi.startAttempt(assessment.assessment_id, user?.id);
      router.push(`/exam/${attempt.attempt_id}` as any);
    } catch (err) {
      console.error('Failed to launch topic drill:', err);
    } finally {
      setLoadingAction(null);
    }
  };

  const firstName = user?.name ? user.name.split(' ')[0] : 'Doctor';
  const activeAttempt = continueData?.resumable_attempts && continueData.resumable_attempts.length > 0
    ? continueData.resumable_attempts[0]
    : null;

  const weakTopic = continueData?.weak_topic_recommendations && continueData.weak_topic_recommendations.length > 0
    ? continueData.weak_topic_recommendations[0]
    : null;

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#38bdf8" />
        }
      >
        {/* Top Doctor Profile Bar */}
        <View style={styles.topBar}>
          <View>
            <Text style={styles.welcomeText}>Hello, {firstName} 👋</Text>
            <Text style={styles.examSubtext}>
              {user?.target_exam || 'NEET_SS'} • {user?.primary_speciality || 'Pathology'}
            </Text>
          </View>
          <View style={styles.streakPill}>
            <Flame size={15} color="#f59e0b" />
            <Text style={styles.streakNum}>{user?.current_streak || 0}</Text>
          </View>
        </View>

        {/* 1. Daily Preparation Target Card */}
        <GoalProgressCard
          currentStreak={user?.current_streak || 0}
          completedToday={dailyQuiz ? 10 : 0}
          dailyGoal={20}
          targetExam={user?.target_exam || 'NEET-SS'}
          speciality={user?.primary_speciality || 'Oncopathology'}
          onContinue={() => {
            if (presets.length > 0) handleLaunchPreset(presets[0].id);
          }}
        />

        {/* 2. Active Attempt Resume Card (if exists) */}
        {activeAttempt ? (
          <Card style={styles.resumeCard} variant="highlight">
            <View style={styles.resumeHeader}>
              <View style={styles.resumeBadgeRow}>
                <RotateCcw size={14} color="#38bdf8" />
                <Text style={styles.resumeTag}>Unfinished Assessment</Text>
              </View>
            </View>

            <Text style={styles.resumeTitle}>{activeAttempt.assessment_title}</Text>
            <Text style={styles.resumeSubtitle}>
              Question {activeAttempt.answered_count} of {activeAttempt.total_questions} answered
            </Text>

            <Button
              title="Resume Exam Now"
              variant="gradient"
              size="md"
              onPress={() => router.push(`/exam/${activeAttempt.attempt_id}` as any)}
              icon={<Play size={15} color="#ffffff" fill="#ffffff" />}
              style={{ marginTop: 12 }}
            />
          </Card>
        ) : null}

        {/* 3. Focus Area / Weak Topic Drill Recommendation */}
        {weakTopic ? (
          <FocusAreaCard
            topicName={weakTopic.topic_name}
            masteryScore={weakTopic.smoothed_accuracy}
            unmasteredCount={weakTopic.incorrect_count}
            loading={loadingAction === weakTopic.curriculum_node_id}
            onPractice={() =>
              handleLaunchTopicDrill(
                weakTopic.curriculum_node_id,
                weakTopic.topic_name
              )
            }
          />
        ) : null}

        {/* 4. Quick Action: Custom Mock Builder Button */}
        <TouchableOpacity
          activeOpacity={0.75}
          onPress={() => router.push('/mock/builder' as any)}
          style={styles.customMockBanner}
        >
          <View style={styles.customMockLeft}>
            <View style={styles.customIconBox}>
              <Sliders size={20} color="#38bdf8" />
            </View>
            <View>
              <Text style={styles.customMockTitle}>Custom QBank & Mock Test</Text>
              <Text style={styles.customMockSub}>
                Build custom tests by topic, difficulty, or 150-Q grand mock
              </Text>
            </View>
          </View>
        </TouchableOpacity>

        {/* 5. Quick Test Presets (Marrow-Style Test Modules) */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>High-Yield Test Modules</Text>
          <TouchableOpacity onPress={() => router.push('/(tabs)/tests' as any)}>
            <Text style={styles.sectionLink}>View All</Text>
          </TouchableOpacity>
        </View>

        {presets.slice(0, 3).map((pr) => (
          <QuickPresetCard
            key={pr.id}
            title={pr.title}
            description={pr.description}
            questionCount={pr.question_count}
            durationSeconds={pr.duration_seconds}
            type={pr.type}
            loading={loadingAction === pr.id}
            onPress={() => handleLaunchPreset(pr.id)}
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
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
    paddingTop: 8,
  },
  welcomeText: {
    fontSize: 20,
    fontWeight: '900',
    color: '#ffffff',
    letterSpacing: -0.4,
  },
  examSubtext: {
    fontSize: 12,
    fontWeight: '700',
    color: '#38bdf8',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 2,
  },
  streakPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.3)',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    gap: 4,
  },
  streakNum: {
    fontSize: 12,
    fontWeight: '800',
    color: '#f59e0b',
  },
  resumeCard: {
    marginBottom: 16,
    backgroundColor: '#0f172a',
    borderColor: '#0284c7',
  },
  resumeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  resumeBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  resumeTag: {
    fontSize: 11,
    fontWeight: '700',
    color: '#38bdf8',
    textTransform: 'uppercase',
  },
  resumeTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 2,
  },
  resumeSubtitle: {
    fontSize: 12,
    color: '#94a3b8',
  },
  customMockBanner: {
    backgroundColor: '#0f172a',
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: '#334155',
    padding: 14,
    marginBottom: 20,
  },
  customMockLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  customIconBox: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  customMockTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ffffff',
  },
  customMockSub: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
    maxWidth: 240,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
    marginTop: 6,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#ffffff',
  },
  sectionLink: {
    fontSize: 12,
    fontWeight: '700',
    color: '#38bdf8',
  },
});
