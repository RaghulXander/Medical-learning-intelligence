import React, { useCallback, useEffect, useState } from 'react';
import { RefreshControl, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Flame } from 'lucide-react-native';
import { assessmentsApi, studentApi } from '@medical/api-client';
import type { AssessmentPreset, ContinueLearningResponse, DailyQuizResponse } from '@medical/shared';
import { MobileHomeRenderer } from '../../components/server-ui/MobileHomeRenderer';
import { useAuth } from '../../lib/auth/auth-context';
import { useMobileScreen } from '../../lib/server-ui/use-mobile-screen';

export default function HomeScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const { document, refresh: refreshLayout } = useMobileScreen(user);
  const [refreshing, setRefreshing] = useState(false);
  const [presets, setPresets] = useState<AssessmentPreset[]>([]);
  const [dailyQuiz, setDailyQuiz] = useState<DailyQuizResponse | null>(null);
  const [continueData, setContinueData] = useState<ContinueLearningResponse | null>(null);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    const presetsResponse = await assessmentsApi.listPresets().catch(() => null);
    if (presetsResponse) setPresets(presetsResponse);
    if (!user) return;
    const [quizResponse, continueResponse] = await Promise.allSettled([
      studentApi.getDailyQuiz(),
      studentApi.getContinueLearning(),
    ]);
    if (quizResponse.status === 'fulfilled') setDailyQuiz(quizResponse.value);
    if (continueResponse.status === 'fulfilled') setContinueData(continueResponse.value);
  }, [user]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadData(), refreshLayout()]);
    setRefreshing(false);
  };

  const launchPreset = async (presetId: string) => {
    setLoadingAction(presetId);
    try {
      const attempt = await assessmentsApi.launchPreset(presetId);
      router.push(`/exam/${attempt.attempt_id}` as never);
    } catch (error) {
      console.error('Failed to launch preset:', error);
    } finally {
      setLoadingAction(null);
    }
  };

  const launchTopic = async (topicId: string, topicName: string) => {
    setLoadingAction(topicId);
    try {
      const assessment = await assessmentsApi.createAssessment({
        title: `${topicName} High-Yield Practice`,
        type: 'TOPIC',
        question_count: 10,
        blueprint: { topic: topicName },
      });
      const attempt = await assessmentsApi.startAttempt(assessment.assessment_id);
      router.push(`/exam/${attempt.attempt_id}` as never);
    } catch (error) {
      console.error('Failed to launch topic drill:', error);
    } finally {
      setLoadingAction(null);
    }
  };

  const firstName = user?.name ? user.name.split(' ')[0] : 'Doctor';

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#38bdf8" />}
      >
        <View style={styles.topBar}>
          <View>
            <Text style={styles.welcomeText}>Hello, {firstName} 👋</Text>
            <Text style={styles.examSubtext}>{user?.target_exam || 'NEET_SS'} • {user?.primary_speciality || 'Pathology'}</Text>
          </View>
          <View style={styles.streakPill}><Flame size={15} color="#f59e0b" /><Text style={styles.streakNum}>{user?.current_streak || 0}</Text></View>
        </View>

        <MobileHomeRenderer
          document={document}
          user={user}
          presets={presets}
          dailyQuiz={dailyQuiz}
          continueData={continueData}
          loadingAction={loadingAction}
          onLaunchPreset={(presetId) => void launchPreset(presetId)}
          onResumeAttempt={(attemptId) => router.push(`/exam/${attemptId}` as never)}
          onLaunchTopic={(topicId, topicName) => void launchTopic(topicId, topicName)}
          onOpenMockBuilder={() => router.push('/mock/builder' as never)}
          onViewAllTests={() => router.push('/(tabs)/tests' as never)}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#020617' },
  scrollContent: { padding: 16, paddingBottom: 32 },
  topBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, paddingTop: 8 },
  welcomeText: { fontSize: 20, fontWeight: '900', color: '#ffffff', letterSpacing: -0.4 },
  examSubtext: { fontSize: 12, fontWeight: '700', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 2 },
  streakPill: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(245, 158, 11, 0.15)', borderWidth: 1, borderColor: 'rgba(245, 158, 11, 0.3)', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5, gap: 4 },
  streakNum: { fontSize: 12, fontWeight: '800', color: '#f59e0b' },
});
