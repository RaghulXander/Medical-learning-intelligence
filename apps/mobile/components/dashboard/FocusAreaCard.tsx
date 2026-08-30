/**
 * apps/mobile/components/dashboard/FocusAreaCard.tsx
 *
 * Card highlighting weak medical topic recommendation with 1-click drill launcher.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { AlertCircle, ArrowRight } from 'lucide-react-native';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

interface FocusAreaCardProps {
  topicName: string;
  masteryScore: number;
  unmasteredCount?: number;
  onPractice: () => void;
  loading?: boolean;
  title?: string;
  actionLabel?: string;
}

export function FocusAreaCard({
  topicName,
  masteryScore,
  unmasteredCount = 6,
  onPractice,
  loading = false,
  title = 'High-Yield Weak Topic',
  actionLabel = 'Practice Weak Area',
}: FocusAreaCardProps) {
  const masteryPercentage = Math.round(masteryScore * 100);

  return (
    <Card style={styles.card} variant="warning">
      <View style={styles.header}>
        <View style={styles.badgeRow}>
          <Badge
            label={title}
            variant="warning"
            icon={<AlertCircle size={12} color="#f59e0b" />}
          />
        </View>
        <Text style={styles.masteryPill}>{masteryPercentage}% Accuracy</Text>
      </View>

      <Text style={styles.topicTitle}>{topicName}</Text>
      <Text style={styles.subtitle}>
        {unmasteredCount} unmastered questions in this topic based on your recent error patterns.
      </Text>

      <Button
        title={actionLabel}
        variant="secondary"
        size="sm"
        loading={loading}
        onPress={onPractice}
        icon={<ArrowRight size={14} color="#e2e8f0" />}
        style={styles.actionBtn}
      />
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: 16,
    backgroundColor: '#0f172a',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  masteryPill: {
    fontSize: 12,
    fontWeight: '800',
    color: '#f59e0b',
  },
  topicTitle: {
    fontSize: 17,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 12,
    color: '#94a3b8',
    lineHeight: 18,
    marginBottom: 12,
  },
  actionBtn: {
    alignSelf: 'flex-start',
  },
});
