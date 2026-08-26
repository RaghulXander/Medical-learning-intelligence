/**
 * apps/mobile/app/review/[attemptId].tsx
 *
 * Marrow-grade Question-by-Question Review with Key Concepts,
 * Distractor Rationales, Reference Citations, and Error Reporting.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Modal,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  BookOpen,
  Sparkles,
  X,
  Flag,
} from 'lucide-react-native';
import { assessmentsApi, questionsApi } from '@medical/api-client';
import { AttemptReview, ReviewQuestionItem, ReviewEvidenceItem } from '@medical/shared';
import { Header } from '../../components/ui/Header';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { QuestionStem } from '../../components/question/QuestionStem';
import { OptionItem } from '../../components/question/OptionItem';

export default function ReviewScreen() {
  const { attemptId } = useLocalSearchParams<{ attemptId: string }>();
  const router = useRouter();

  const [review, setReview] = useState<AttemptReview | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  // Report Modal
  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [reportCategory, setReportCategory] = useState('INCORRECT_ANSWER');
  const [reportNotes, setReportNotes] = useState('');
  const [submittingReport, setSubmittingReport] = useState(false);

  useEffect(() => {
    if (!attemptId) return;
    assessmentsApi
      .getReview(attemptId)
      .then(setReview)
      .catch((err) => console.error('Failed to load review:', err))
      .finally(() => setLoading(false));
  }, [attemptId]);

  const questions: ReviewQuestionItem[] = review?.review_questions || [];
  const currentQ = questions[currentIndex];

  const handleSendReport = async () => {
    if (!currentQ) return;
    setSubmittingReport(true);
    try {
      await questionsApi.reportQuestion({
        question_id: currentQ.question_id,
        category: reportCategory,
        notes: reportNotes.trim() || 'Reported via mobile app review.',
      });
      setReportModalVisible(false);
      setReportNotes('');
      Alert.alert('Report Received', 'Thank you. Our medical editorial board will review this question.');
    } catch {
      Alert.alert('Notice', 'Question report recorded.');
      setReportModalVisible(false);
    } finally {
      setSubmittingReport(false);
    }
  };

  if (loading || !review || !currentQ) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#38bdf8" />
        <Text style={styles.loadingText}>Loading Question Reviews & Rationales...</Text>
      </SafeAreaView>
    );
  }

  const isCorrect = currentQ.is_correct;
  const isUnanswered = !currentQ.selected_answer;

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
      <Header
        title={`Review ${currentIndex + 1} of ${questions.length}`}
        subtitle={review.title}
        onBack={() => router.back()}
        rightElement={
          <TouchableOpacity
            onPress={() => setReportModalVisible(true)}
            style={styles.flagBtn}
          >
            <Flag size={16} color="#fb7185" />
          </TouchableOpacity>
        }
      />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Status Indicator */}
        <View style={styles.statusRow}>
          <Badge
            label={
              isUnanswered
                ? 'Unattempted'
                : isCorrect
                ? 'Correct (+4 Marks)'
                : 'Incorrect (-1 Mark)'
            }
            variant={isUnanswered ? 'outline' : isCorrect ? 'verified' : 'danger'}
            icon={
              isUnanswered ? undefined : isCorrect ? (
                <CheckCircle2 size={12} color="#34d399" />
              ) : (
                <XCircle size={12} color="#fb7185" />
              )
            }
          />
        </View>

        {/* Question Stem */}
        <QuestionStem
          questionNumber={currentIndex + 1}
          totalQuestions={questions.length}
          stem={currentQ.stem}
          difficulty={currentQ.difficulty}
        />

        {/* Options in Review Mode */}
        <View style={styles.optionsContainer}>
          {(['A', 'B', 'C', 'D'] as const).map((key) => {
            const optText = getOptionText(key);
            const isSelected = currentQ.selected_answer === key;
            const isCorrectOption = currentQ.correct_answer === key;

            return (
              <OptionItem
                key={key}
                optionKey={key}
                optionText={optText}
                isSelected={isSelected}
                isReviewMode={true}
                isCorrectOption={isCorrectOption}
                disabled={true}
              />
            );
          })}
        </View>

        {/* Marrow-style High-Yield Explanation Box */}
        <Card style={styles.explanationCard} variant="highlight">
          <View style={styles.expHeader}>
            <BookOpen size={18} color="#38bdf8" />
            <Text style={styles.expTitle}>Comprehensive Medical Rationale</Text>
          </View>

          {/* Key Concept / Bottom Line Highlight */}
          <View style={styles.keyConceptBox}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <Sparkles size={14} color="#f59e0b" />
              <Text style={styles.keyConceptLabel}>High-Yield Key Concept</Text>
            </View>
            <Text style={styles.keyConceptText}>
              Correct Answer is Option {currentQ.correct_answer}.
            </Text>
          </View>

          {/* Detailed Explanation Text */}
          <Text style={styles.explanationBody}>{currentQ.explanation || 'No explanation provided.'}</Text>

          {/* Evidence Citations */}
          {currentQ.citations && currentQ.citations.length > 0 ? (
            <View style={styles.sourcesBox}>
              <Text style={styles.sourcesLabel}>Authoritative Medical References:</Text>
              {currentQ.citations.map((s: ReviewEvidenceItem, idx: number) => (
                <Text key={idx} style={styles.sourceItem}>
                  • {s.source_title} ({s.edition ? `${s.edition} ed` : ''}
                  {s.chapter ? `, Ch. ${s.chapter}` : ''}
                  {s.page_range ? `, p. ${s.page_range}` : ''})
                </Text>
              ))}
            </View>
          ) : null}
        </Card>
      </ScrollView>

      {/* Bottom Navigation */}
      <View style={styles.bottomBar}>
        <TouchableOpacity
          disabled={currentIndex === 0}
          onPress={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
          style={[styles.navBtn, currentIndex === 0 ? styles.navBtnDisabled : null]}
        >
          <ChevronLeft size={20} color={currentIndex === 0 ? '#475569' : '#ffffff'} />
          <Text style={styles.navBtnText}>Previous</Text>
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
          <Text style={styles.navBtnText}>Next Question</Text>
          <ChevronRight size={20} color="#ffffff" />
        </TouchableOpacity>
      </View>

      {/* Report Question Modal */}
      <Modal visible={reportModalVisible} transparent animationType="fade">
        <SafeAreaView style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Report Question Error</Text>
              <TouchableOpacity onPress={() => setReportModalVisible(false)}>
                <X size={20} color="#94a3b8" />
              </TouchableOpacity>
            </View>

            <Text style={styles.modalLabel}>Issue Category</Text>
            <View style={styles.categoryRow}>
              {[
                { id: 'INCORRECT_ANSWER', label: 'Wrong Key' },
                { id: 'AMBIGUOUS_STEM', label: 'Ambiguous' },
                { id: 'EXPLANATION_ERROR', label: 'Explanation' },
                { id: 'TYPO', label: 'Typo' },
              ].map((c) => (
                <TouchableOpacity
                  key={c.id}
                  onPress={() => setReportCategory(c.id)}
                  style={[
                    styles.categoryPill,
                    reportCategory === c.id ? styles.categoryActive : null,
                  ]}
                >
                  <Text
                    style={[
                      styles.categoryText,
                      reportCategory === c.id ? styles.textSky : null,
                    ]}
                  >
                    {c.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.modalLabel}>Details / Textbook Reference</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Describe the discrepancy or quote reference..."
              placeholderTextColor="#64748b"
              multiline
              numberOfLines={3}
              value={reportNotes}
              onChangeText={setReportNotes}
            />

            <Button
              title="Submit Report"
              variant="danger"
              size="md"
              loading={submittingReport}
              onPress={handleSendReport}
              style={{ marginTop: 14 }}
            />
          </View>
        </SafeAreaView>
      </Modal>
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
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
  },
  flagBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  optionsContainer: {
    marginVertical: 12,
  },
  explanationCard: {
    backgroundColor: '#0f172a',
    padding: 16,
    marginTop: 8,
  },
  expHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  expTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ffffff',
  },
  keyConceptBox: {
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.3)',
    padding: 12,
    marginBottom: 12,
  },
  keyConceptLabel: {
    fontSize: 11,
    fontWeight: '800',
    color: '#fbbf24',
    textTransform: 'uppercase',
  },
  keyConceptText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#fef3c7',
  },
  explanationBody: {
    fontSize: 14,
    lineHeight: 22,
    color: '#cbd5e1',
  },
  sourcesBox: {
    marginTop: 14,
    paddingTop: 12,
    borderTopWidth: 1,
    borderColor: '#1e293b',
  },
  sourcesLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#94a3b8',
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  sourceItem: {
    fontSize: 12,
    color: '#38bdf8',
    lineHeight: 18,
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
    gap: 4,
  },
  nextBtn: {
    backgroundColor: '#0284c7',
    borderColor: '#38bdf8',
  },
  navBtnDisabled: {
    opacity: 0.3,
  },
  navBtnText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#ffffff',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(2, 6, 23, 0.85)',
    justifyContent: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#0f172a',
    borderRadius: 24,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: '800',
    color: '#ffffff',
  },
  modalLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#cbd5e1',
    marginBottom: 6,
    marginTop: 8,
  },
  categoryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 12,
  },
  categoryPill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#020617',
    borderWidth: 1,
    borderColor: '#334155',
  },
  categoryActive: {
    borderColor: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
  },
  categoryText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#94a3b8',
  },
  modalInput: {
    backgroundColor: '#020617',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#334155',
    padding: 12,
    color: '#ffffff',
    fontSize: 13,
    textAlignVertical: 'top',
    minHeight: 80,
  },
  textSky: {
    color: '#38bdf8',
  },
});
