/**
 * apps/mobile/components/dashboard/QuickPresetCard.tsx
 *
 * Exam preset test launcher card.
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Play, Clock, HelpCircle } from 'lucide-react-native';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';

interface QuickPresetCardProps {
  title: string;
  description: string;
  questionCount: number;
  durationSeconds: number;
  type: string;
  onPress: () => void;
  loading?: boolean;
}

export function QuickPresetCard({
  title,
  description,
  questionCount,
  durationSeconds,
  type,
  onPress,
  loading = false,
}: QuickPresetCardProps) {
  const durationMins = Math.round(durationSeconds / 60);

  return (
    <TouchableOpacity activeOpacity={0.75} onPress={onPress} disabled={loading}>
      <Card style={styles.card}>
        <View style={styles.topRow}>
          <Badge
            label={type === 'DAILY' ? 'Daily' : type === 'MOCK' ? 'Mock Test' : 'Topic Drill'}
            variant={type === 'DAILY' ? 'default' : type === 'MOCK' ? 'purple' : 'verified'}
          />
          <View style={styles.playIconBox}>
            <Play size={14} color="#38bdf8" fill="#38bdf8" />
          </View>
        </View>

        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description} numberOfLines={2}>
          {description}
        </Text>

        <View style={styles.metaRow}>
          <View style={styles.metaItem}>
            <HelpCircle size={13} color="#94a3b8" />
            <Text style={styles.metaText}>{questionCount} MCQs</Text>
          </View>
          <View style={styles.metaItem}>
            <Clock size={13} color="#94a3b8" />
            <Text style={styles.metaText}>{durationMins} mins</Text>
          </View>
        </View>
      </Card>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: 12,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  playIconBox: {
    width: 28,
    height: 28,
    borderRadius: 8,
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 16,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 4,
  },
  description: {
    fontSize: 12,
    color: '#94a3b8',
    lineHeight: 17,
    marginBottom: 12,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  metaText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#cbd5e1',
  },
});
