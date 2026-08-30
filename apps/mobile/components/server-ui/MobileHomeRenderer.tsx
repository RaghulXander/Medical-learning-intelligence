import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Play, RotateCcw, Sliders } from 'lucide-react-native';
import type {
  AssessmentPreset,
  ContinueLearningResponse,
  DailyQuizResponse,
  MobileScreenDocument,
  UserProfile,
} from '@medical/shared';
import { GoalProgressCard } from '../dashboard/GoalProgressCard';
import { FocusAreaCard } from '../dashboard/FocusAreaCard';
import { QuickPresetCard } from '../dashboard/QuickPresetCard';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface MobileHomeRendererProps {
  document: MobileScreenDocument;
  user: UserProfile | null;
  presets: AssessmentPreset[];
  dailyQuiz: DailyQuizResponse | null;
  continueData: ContinueLearningResponse | null;
  loadingAction: string | null;
  onLaunchPreset: (presetId: string) => void;
  onResumeAttempt: (attemptId: string) => void;
  onLaunchTopic: (topicId: string, topicName: string) => void;
  onOpenMockBuilder: () => void;
  onViewAllTests: () => void;
}

export function MobileHomeRenderer(props: MobileHomeRendererProps) {
  const activeAttempt = props.continueData?.resumable_attempts?.[0];
  const weakTopic = props.continueData?.weak_topic_recommendations?.[0];

  return <>{props.document.widgets.map((widget) => {
    switch (widget.type) {
      case 'goal_progress':
        return <GoalProgressCard key={widget.id} title={widget.props.title} actionLabel={widget.props.actionLabel} currentStreak={props.user?.current_streak || 0} completedToday={props.dailyQuiz ? 10 : 0} dailyGoal={widget.props.dailyGoal} targetExam={props.user?.target_exam || 'NEET-SS'} speciality={props.user?.primary_speciality || 'Pathology'} onContinue={() => props.presets[0] && props.onLaunchPreset(props.presets[0].id)} />;
      case 'continue_learning':
        return activeAttempt ? <Card key={widget.id} style={styles.card} variant="highlight"><View style={styles.tagRow}><RotateCcw size={14} color="#38bdf8" /><Text style={styles.tag}>{widget.props.title}</Text></View><Text style={styles.title}>{activeAttempt.assessment_title}</Text><Text style={styles.subtitle}>Question {activeAttempt.answered_count} of {activeAttempt.total_questions} answered</Text><Button title={widget.props.actionLabel} variant="gradient" size="md" onPress={() => props.onResumeAttempt(activeAttempt.attempt_id)} icon={<Play size={15} color="#ffffff" fill="#ffffff" />} style={{ marginTop: 12 }} /></Card> : null;
      case 'focus_area':
        return weakTopic ? <FocusAreaCard key={widget.id} title={widget.props.title} actionLabel={widget.props.actionLabel} topicName={weakTopic.topic_name} masteryScore={weakTopic.smoothed_accuracy} unmasteredCount={weakTopic.incorrect_count} loading={props.loadingAction === weakTopic.curriculum_node_id} onPractice={() => props.onLaunchTopic(weakTopic.curriculum_node_id, weakTopic.topic_name)} /> : null;
      case 'custom_mock':
        return <TouchableOpacity key={widget.id} activeOpacity={0.75} onPress={props.onOpenMockBuilder} style={styles.mock}><View style={styles.mockLeft}><View style={styles.icon}><Sliders size={20} color="#38bdf8" /></View><View style={styles.flex}><Text style={styles.mockTitle}>{widget.props.title}</Text><Text style={styles.mockSubtitle}>{widget.props.description}</Text></View></View></TouchableOpacity>;
      case 'quick_presets':
        return <View key={widget.id}><View style={styles.sectionHeader}><Text style={styles.sectionTitle}>{widget.props.title}</Text><TouchableOpacity onPress={props.onViewAllTests}><Text style={styles.sectionLink}>{widget.props.viewAllLabel}</Text></TouchableOpacity></View>{props.presets.slice(0, widget.props.limit).map((preset) => <QuickPresetCard key={preset.id} title={preset.title} description={preset.description} questionCount={preset.question_count} durationSeconds={preset.duration_seconds} type={preset.type} loading={props.loadingAction === preset.id} onPress={() => props.onLaunchPreset(preset.id)} />)}</View>;
    }
  })}</>;
}

const styles = StyleSheet.create({
  card: { marginBottom: 16 }, tagRow: { flexDirection: 'row', alignItems: 'center', gap: 6 }, tag: { color: '#38bdf8', fontSize: 12, fontWeight: '700' }, title: { color: '#fff', fontSize: 17, fontWeight: '800', marginTop: 8 }, subtitle: { color: '#94a3b8', fontSize: 12, marginTop: 3 },
  mock: { backgroundColor: '#0f172a', borderWidth: 1, borderColor: '#334155', borderRadius: 16, padding: 14, marginBottom: 18 }, mockLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 }, icon: { width: 40, height: 40, borderRadius: 10, backgroundColor: 'rgba(56,189,248,0.12)', alignItems: 'center', justifyContent: 'center' }, flex: { flex: 1 }, mockTitle: { color: '#fff', fontWeight: '800', fontSize: 14 }, mockSubtitle: { color: '#94a3b8', fontSize: 11, marginTop: 2 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }, sectionTitle: { color: '#fff', fontWeight: '900', fontSize: 16 }, sectionLink: { color: '#38bdf8', fontSize: 12, fontWeight: '700' },
});
