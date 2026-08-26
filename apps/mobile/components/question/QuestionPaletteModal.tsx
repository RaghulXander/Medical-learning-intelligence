/**
 * apps/mobile/components/question/QuestionPaletteModal.tsx
 *
 * Bottom sheet modal providing grid-based question navigation and status overview.
 */

import React from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { X, Bookmark, CheckCircle2 } from 'lucide-react-native';
import { Button } from '../ui/Button';

interface QuestionPaletteModalProps {
  visible: boolean;
  onClose: () => void;
  totalQuestions: number;
  currentIndex: number;
  answers: Record<string, string>;
  markedReview: Record<string, boolean>;
  questionIds: string[];
  onSelectQuestion: (index: number) => void;
  onSubmitExam: () => void;
}

export function QuestionPaletteModal({
  visible,
  onClose,
  totalQuestions,
  currentIndex,
  answers,
  markedReview,
  questionIds,
  onSelectQuestion,
  onSubmitExam,
}: QuestionPaletteModalProps) {
  const answeredCount = Object.keys(answers).length;
  const markedCount = Object.values(markedReview).filter(Boolean).length;
  const unansweredCount = Math.max(0, totalQuestions - answeredCount);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.overlay}>
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>Question Palette</Text>
              <Text style={styles.subtitle}>
                {answeredCount} of {totalQuestions} answered
              </Text>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <X size={20} color="#94a3b8" />
            </TouchableOpacity>
          </View>

          {/* Legend Counters */}
          <View style={styles.legendRow}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#0284c7' }]} />
              <Text style={styles.legendText}>Answered ({answeredCount})</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#a855f7' }]} />
              <Text style={styles.legendText}>Marked ({markedCount})</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#334155' }]} />
              <Text style={styles.legendText}>Left ({unansweredCount})</Text>
            </View>
          </View>

          {/* Number Grid */}
          <ScrollView contentContainerStyle={styles.grid}>
            {Array.from({ length: totalQuestions }).map((_, idx) => {
              const qId = questionIds[idx] || `q-${idx}`;
              const isAnswered = !!answers[qId];
              const isMarked = !!markedReview[qId];
              const isCurrent = idx === currentIndex;

              let btnStyle = styles.defaultNumBtn;
              let textStyle = styles.defaultNumText;

              if (isMarked) {
                btnStyle = styles.markedNumBtn;
                textStyle = styles.activeNumText;
              } else if (isAnswered) {
                btnStyle = styles.answeredNumBtn;
                textStyle = styles.activeNumText;
              }

              return (
                <TouchableOpacity
                  key={idx}
                  activeOpacity={0.7}
                  onPress={() => {
                    onSelectQuestion(idx);
                    onClose();
                  }}
                  style={[
                    styles.numBtn,
                    btnStyle,
                    isCurrent ? styles.currentNumBorder : null,
                  ]}
                >
                  <Text style={[styles.numText, textStyle]}>{idx + 1}</Text>
                  {isMarked ? (
                    <View style={styles.bookmarkDot}>
                      <Bookmark size={8} color="#ffffff" />
                    </View>
                  ) : null}
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          {/* Bottom Actions */}
          <View style={styles.footer}>
            <Button
              title="Submit Assessment"
              variant="danger"
              onPress={() => {
                onClose();
                onSubmitExam();
              }}
              style={{ width: '100%' }}
            />
          </View>
        </View>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(2, 6, 23, 0.85)',
    justifyContent: 'flex-end',
  },
  content: {
    backgroundColor: '#0f172a',
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    borderWidth: 1,
    borderColor: '#334155',
    padding: 20,
    maxHeight: '85%',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
    color: '#ffffff',
  },
  subtitle: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 2,
  },
  closeBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: '#1e293b',
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#1e293b',
    marginBottom: 16,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  legendText: {
    fontSize: 11,
    color: '#cbd5e1',
    fontWeight: '600',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    paddingBottom: 16,
    justifyContent: 'flex-start',
  },
  numBtn: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  defaultNumBtn: {
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155',
  },
  answeredNumBtn: {
    backgroundColor: '#0284c7', // Sky-600
    borderWidth: 1,
    borderColor: '#38bdf8',
  },
  markedNumBtn: {
    backgroundColor: '#9333ea', // Purple-600
    borderWidth: 1,
    borderColor: '#c084fc',
  },
  currentNumBorder: {
    borderWidth: 2.5,
    borderColor: '#f59e0b', // Amber-500
  },
  numText: {
    fontSize: 15,
    fontWeight: '700',
  },
  defaultNumText: {
    color: '#94a3b8',
  },
  activeNumText: {
    color: '#ffffff',
  },
  bookmarkDot: {
    position: 'absolute',
    top: 4,
    right: 4,
  },
  footer: {
    marginTop: 10,
    paddingTop: 12,
    borderTopWidth: 1,
    borderColor: '#1e293b',
  },
});
