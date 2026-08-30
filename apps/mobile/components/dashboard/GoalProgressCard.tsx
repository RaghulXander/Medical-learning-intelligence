/**
 * apps/mobile/components/dashboard/GoalProgressCard.tsx
 *
 * Daily question goal progress widget with streak pill.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Flame, Target, Sparkles } from 'lucide-react-native';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

interface GoalProgressCardProps {
  currentStreak: number;
  completedToday: number;
  dailyGoal: number;
  onContinue: () => void;
  targetExam?: string;
  speciality?: string;
  title?: string;
  actionLabel?: string;
}

export function GoalProgressCard({
  currentStreak,
  completedToday,
  dailyGoal = 20,
  onContinue,
  targetExam = 'NEET_SS',
  speciality = 'Pathology',
  title = 'Daily Preparation Target',
  actionLabel,
}: GoalProgressCardProps) {
  const percentage = Math.min(100, Math.round((completedToday / dailyGoal) * 100));

  return (
    <Card style={styles.card} variant="highlight">
      {/* Top row */}
      <View style={styles.topRow}>
        <View>
          <Text style={styles.greetingText}>{title}</Text>
          <Text style={styles.examText}>
            {targetExam} • {speciality}
          </Text>
        </View>
        <Badge
          label={`${currentStreak} Day Streak`}
          variant="warning"
          icon={<Flame size={12} color="#f59e0b" />}
        />
      </View>

      {/* Counter */}
      <View style={styles.counterRow}>
        <View style={styles.counterBox}>
          <Text style={styles.counterNum}>
            {completedToday}{' '}
            <Text style={styles.counterTotal}>/ {dailyGoal} MCQs</Text>
          </Text>
          <Text style={styles.statusText}>
            {percentage >= 100 ? '🎉 Goal Achieved Today!' : `${dailyGoal - completedToday} questions remaining`}
          </Text>
        </View>
      </View>

      {/* Progress Bar */}
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${percentage}%` }]} />
      </View>

      {/* Action */}
      <Button
        title={actionLabel || (completedToday > 0 ? 'Continue Practice' : 'Start Daily Quiz')}
        onPress={onContinue}
        variant="primary"
        size="md"
        icon={<Sparkles size={16} color="#ffffff" />}
        style={{ marginTop: 14 }}
      />
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: 16,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  greetingText: {
    fontSize: 13,
    color: '#94a3b8',
    fontWeight: '600',
  },
  examText: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ffffff',
    marginTop: 1,
  },
  counterRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 10,
  },
  counterBox: {
    flex: 1,
  },
  counterNum: {
    fontSize: 26,
    fontWeight: '900',
    color: '#ffffff',
    letterSpacing: -0.5,
  },
  counterTotal: {
    fontSize: 15,
    fontWeight: '600',
    color: '#64748b',
  },
  statusText: {
    fontSize: 12,
    color: '#38bdf8',
    fontWeight: '600',
    marginTop: 2,
  },
  progressTrack: {
    width: '100%',
    height: 8,
    backgroundColor: '#1e293b',
    borderRadius: 999,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#0284c7',
    borderRadius: 999,
  },
});
