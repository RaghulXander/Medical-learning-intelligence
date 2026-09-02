/**
 * apps/mobile/app/exam/[attemptId].tsx
 *
 * Marrow-grade Mobile Timed Question Runner with Optimistic Sync,
 * Navigation Palette, and Authoritative Timer.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Grid,
  ArrowLeft,
} from 'lucide-react-native';
import { assessmentsApi } from '@medical/api-client';
import { AttemptStateResponse, SanitizedQuestion } from '@medical/shared';
import { draftSyncQueue } from '../../lib/sync/draft-sync';
import { Timer } from '../../components/ui/Timer';
import { QuestionStem } from '../../components/question/QuestionStem';
import { OptionItem } from '../../components/question/OptionItem';
import { QuestionPaletteModal } from '../../components/question/QuestionPaletteModal';

export default function ExamRunnerScreen() {
  const { attemptId } = useLocalSearchParams<{ attemptId: string }>();
  const router = useRouter();

  const [attemptState, setAttemptState] = useState<AttemptStateResponse | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [markedReview, setMarkedReview] = useState<Record<string, boolean>>({});
  const [paletteVisible, setPaletteVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!attemptId) return;
    draftSyncQueue.setAttemptId(attemptId);

    assessmentsApi
      .getAttemptState(attemptId)
      .then((data) => {
        setAttemptState(data);
        const ansMap: Record<string, string> = {};
        const revMap: Record<string, boolean> = {};

        (data.questions || []).forEach((q) => {
          if (q.selected_answer) ansMap[q.question_id] = q.selected_answer;
          if (q.marked_for_review) revMap[q.question_id] = true;
        });

        setAnswers(ansMap);
        setMarkedReview(revMap);
      })
      .catch((err: any) => {
        console.error('Failed to load attempt state:', err);
        Alert.alert('Error', 'Unable to load examination.', [
          { text: 'Go Back', onPress: () => router.replace('/(tabs)' as any) },
        ]);
      })
      .finally(() => setLoading(false));
  }, [attemptId, router]);

  const questions: SanitizedQuestion[] = attemptState?.questions || [];
  const currentQ = questions[currentIndex];
  const questionIds = questions.map((q) => q.question_id);

  const handleSelectOption = (key: 'A' | 'B' | 'C' | 'D') => {
    if (!currentQ) return;
    setAnswers((prev) => ({ ...prev, [currentQ.question_id]: key }));
    draftSyncQueue.recordAnswer(currentQ.question_id, key, 15);
  };

  const handleToggleReview = () => {
    if (!currentQ) return;
    setMarkedReview((prev) => ({ ...prev, [currentQ.question_id]: !prev[currentQ.question_id] }));
  };

  const handleSubmitExam = useCallback(async () => {
    if (!attemptId || submitting) return;

    setSubmitting(true);
    try {
      await draftSyncQueue.flush();
      await assessmentsApi.submitAttempt(attemptId);
      router.replace(`/results/${attemptId}` as any);
    } catch {
      router.replace(`/results/${attemptId}` as any);
    } finally {
      setSubmitting(false);
    }
  }, [attemptId, submitting, router]);

  const confirmSubmit = () => {
    const answeredCount = Object.keys(answers).length;
    const totalCount = questions.length;
    const unansweredCount = totalCount - answeredCount;

    Alert.alert(
      'Submit Assessment',
      `You have answered ${answeredCount} of ${totalCount} questions (${unansweredCount} unanswered).\n\nDo you want to finalize and view results?`,
      [
        { text: 'Continue Exam', style: 'cancel' },
        { text: 'Submit Now', style: 'destructive', onPress: handleSubmitExam },
      ]
    );
  };

  if (loading || !attemptState || !currentQ) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#38bdf8" />
        <Text style={styles.loadingText}>Loading Medical Exam Module...</Text>
      </SafeAreaView>
    );
  }

  const isCurrentMarked = !!markedReview[currentQ.question_id];
  const currentSelected = answers[currentQ.question_id];

  const getOptionText = (key: 'A' | 'B' | 'C' | 'D'): string => {
    if (!currentQ.options) return '';
    if (Array.isArray(currentQ.options)) {
      const found = currentQ.options.find((o: any) => o.key === key);
      return found?.text || '';
    }
    return (currentQ.options as Record<string, string>)[key] || '';
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      {/* Top Runner Bar */}
      <View style={styles.topBar}>
        <TouchableOpacity
          onPress={() =>
            Alert.alert('Exit Exam', 'Your answers are auto-saved. Exit to home?', [
              { text: 'Stay', style: 'cancel' },
              { text: 'Exit', onPress: () => router.replace('/(tabs)' as any) },
            ])
          }
          style={styles.iconBtn}
        >
          <ArrowLeft size={18} color="#94a3b8" />
        </TouchableOpacity>

        <Timer
          initialSeconds={attemptState.remaining_seconds || 1800}
          onTimeExpired={handleSubmitExam}
        />

        <View style={styles.topBarRight}>
          <TouchableOpacity onPress={() => setPaletteVisible(true)} style={styles.iconBtn}>
            <Grid size={18} color="#38bdf8" />
          </TouchableOpacity>

          <TouchableOpacity onPress={confirmSubmit} style={styles.submitPill}>
            <Text style={styles.submitPillText}>Submit</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Main Question Stem & Options Scroll Area */}
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <QuestionStem
          questionNumber={currentIndex + 1}
          totalQuestions={questions.length}
          stem={currentQ.stem}
          topicName={currentQ.topic_name || 'Pathology & Diagnostic IHC'}
          difficulty={currentQ.difficulty}
          imageUrl={
            currentQ.image_assets?.[0]?.cdn_url ||
            (currentQ.image_assets?.[0]?.storage_uri?.startsWith('http')
              ? currentQ.image_assets[0].storage_uri
              : undefined)
          }
          imageCaption={
            currentQ.image_assets?.[0]?.caption ||
            currentQ.image_assets?.[0]?.figure_label ||
            (currentQ.image_assets?.[0]?.source_name ? `Source: ${currentQ.image_assets[0].source_name}` : undefined)
          }
        />

        {/* Options */}
        <View style={styles.optionsList}>
          {(['A', 'B', 'C', 'D'] as const).map((key) => {
            const optText = getOptionText(key);
            const isSelected = currentSelected === key;
            return (
              <OptionItem
                key={key}
                optionKey={key}
                optionText={optText}
                isSelected={isSelected}
                onSelect={() => handleSelectOption(key)}
              />
            );
          })}
        </View>
      </ScrollView>

      {/* Bottom Marrow-style Control Bar */}
      <View style={styles.bottomBar}>
        <TouchableOpacity
          disabled={currentIndex === 0}
          onPress={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
          style={[styles.navBtn, currentIndex === 0 ? styles.navBtnDisabled : null]}
        >
          <ChevronLeft size={20} color={currentIndex === 0 ? '#475569' : '#ffffff'} />
          <Text
            style={[styles.navBtnText, currentIndex === 0 ? styles.navBtnTextDisabled : null]}
          >
            Prev
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          activeOpacity={0.7}
          onPress={handleToggleReview}
          style={[styles.reviewToggleBtn, isCurrentMarked ? styles.reviewToggleActive : null]}
        >
          <Bookmark
            size={16}
            color={isCurrentMarked ? '#c084fc' : '#94a3b8'}
            fill={isCurrentMarked ? '#c084fc' : 'transparent'}
          />
          <Text style={[styles.reviewToggleText, isCurrentMarked ? styles.textPurple : null]}>
            {isCurrentMarked ? 'Marked' : 'Review'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          disabled={currentIndex === questions.length - 1}
          onPress={() => setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1))}
          style={[
            styles.navBtn,
            styles.nextBtn,
            currentIndex === questions.length - 1 ? styles.navBtnDisabled : null,
          ]}
        >
          <Text style={styles.navBtnText}>Next</Text>
          <ChevronRight size={20} color="#ffffff" />
        </TouchableOpacity>
      </View>

      {/* Question Palette Modal */}
      <QuestionPaletteModal
        visible={paletteVisible}
        onClose={() => setPaletteVisible(false)}
        totalQuestions={questions.length}
        currentIndex={currentIndex}
        answers={answers}
        markedReview={markedReview}
        questionIds={questionIds}
        onSelectQuestion={(idx) => setCurrentIndex(idx)}
        onSubmitExam={handleSubmitExam}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#020617',
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#020617',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
    color: '#94a3b8',
    fontWeight: '600',
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderColor: '#1e293b',
    backgroundColor: '#020617',
  },
  iconBtn: {
    width: 38,
    height: 38,
    borderRadius: 10,
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
  },
  topBarRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  submitPill: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: '#e11d48', // Rose-600
  },
  submitPillText: {
    fontSize: 13,
    fontWeight: '800',
    color: '#ffffff',
  },
  scrollContent: {
    padding: 18,
    paddingBottom: 24,
  },
  optionsList: {
    marginTop: 10,
  },
  bottomBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderColor: '#1e293b',
    backgroundColor: '#0f172a',
  },
  navBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155',
  },
  nextBtn: {
    backgroundColor: '#0284c7', // Sky-600
    borderColor: '#38bdf8',
  },
  navBtnDisabled: {
    opacity: 0.3,
    backgroundColor: '#1e293b',
    borderColor: '#334155',
  },
  navBtnText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#ffffff',
    marginHorizontal: 4,
  },
  navBtnTextDisabled: {
    color: '#64748b',
  },
  reviewToggleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: '#020617',
    borderWidth: 1,
    borderColor: '#334155',
    gap: 6,
  },
  reviewToggleActive: {
    borderColor: '#a855f7',
    backgroundColor: 'rgba(168, 85, 247, 0.15)',
  },
  reviewToggleText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#94a3b8',
  },
  textPurple: {
    color: '#c084fc',
  },
});
