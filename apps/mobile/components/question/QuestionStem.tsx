/**
 * apps/mobile/components/question/QuestionStem.tsx
 *
 * High-readability medical question stem renderer supporting long vignettes,
 * clinical cases, and embedded diagrams.
 */

import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { Badge } from '../ui/Badge';

interface QuestionStemProps {
  questionNumber: number;
  totalQuestions: number;
  stem: string;
  topicName?: string;
  difficulty?: string;
  imageUrl?: string;
  imageCaption?: string;
}

export function QuestionStem({
  questionNumber,
  totalQuestions,
  stem,
  topicName,
  difficulty,
  imageUrl,
  imageCaption,
}: QuestionStemProps) {
  return (
    <View style={styles.container}>
      {/* Top Meta row */}
      <View style={styles.metaRow}>
        <Badge
          label={`Question ${questionNumber} of ${totalQuestions}`}
          variant="default"
        />
        {difficulty ? (
          <Badge
            label={difficulty.toUpperCase()}
            variant={
              difficulty.toLowerCase() === 'hard'
                ? 'danger'
                : difficulty.toLowerCase() === 'medium'
                ? 'warning'
                : 'verified'
            }
          />
        ) : null}
      </View>

      {topicName ? (
        <Text style={styles.topicText} numberOfLines={1}>
          {topicName}
        </Text>
      ) : null}

      {/* Stem Text */}
      <Text style={styles.stemText}>{stem}</Text>

      {/* Embedded Image / Pathology Vignette Media */}
      {imageUrl ? (
        <View style={styles.mediaContainer}>
          <Image
            source={{ uri: imageUrl }}
            style={styles.image}
            resizeMode="contain"
          />
          {imageCaption ? (
            <Text style={styles.captionText}>{imageCaption}</Text>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 12,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  topicText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#38bdf8',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  stemText: {
    fontSize: 17,
    lineHeight: 26,
    fontWeight: '600',
    color: '#f8fafc',
    letterSpacing: -0.2,
  },
  mediaContainer: {
    marginTop: 16,
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: '#020617',
    borderWidth: 1,
    borderColor: '#334155',
    padding: 8,
  },
  image: {
    width: '100%',
    height: 220,
    borderRadius: 12,
  },
  captionText: {
    fontSize: 11,
    color: '#94a3b8',
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 6,
  },
});
