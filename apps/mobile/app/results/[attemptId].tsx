/**
 * apps/mobile/app/results/[attemptId].tsx
 *
 * Marrow-grade Results & Scorecard Screen with Topic Breakdown and Review Actions.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  Trophy,
  CheckCircle2,
  XCircle,
  Clock,
  BookOpen,
  Home,
} from 'lucide-react-native';
import { assessmentsApi } from '@medical/api-client';
import { AttemptResults } from '@medical/shared';
import { Header } from '../../components/ui/Header';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';

export default function ResultsScreen() {
  const { attemptId } = useLocalSearchParams<{ attemptId: string }>();
  const router = useRouter();

  const [results, setResults] = useState<AttemptResults | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!attemptId) return;
    assessmentsApi
      .getResults(attemptId)
      .then(setResults)
      .catch((err) => console.error('Failed to load results:', err))
      .finally(() => setLoading(false));
  }, [attemptId]);

  if (loading || !results) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#38bdf8" />
        <Text style={styles.loadingText}>Calculating Scorecard & Analytics...</Text>
      </SafeAreaView>
    );
  }

  const scorePct = Math.round(results.percentage || results.accuracy || 0);
  const totalQ = results.correct_count + results.incorrect_count + (results.unanswered_count || 0);
  const isPass = scorePct >= 65;

  return (
    <SafeAreaView style={styles.safeArea}>
      <Header
        title="Assessment Results"
        subtitle={results.title || 'Exam Scorecard'}
        rightElement={
          <TouchableOpacity
            onPress={() => router.replace('/(tabs)' as any)}
            style={styles.homeBtn}
          >
            <Home size={18} color="#94a3b8" />
          </TouchableOpacity>
        }
      />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Scorecard Hero */}
        <Card style={styles.heroCard} variant={isPass ? 'highlight' : 'warning'}>
          <View style={styles.heroTop}>
            <View>
              <Text style={styles.scoreTitle}>Overall Score</Text>
              <Text style={styles.scorePercentage}>{scorePct}%</Text>
              <Text style={styles.scoreSub}>
                {results.correct_count} of {totalQ} Correct
              </Text>
            </View>

            <View style={styles.trophyBox}>
              <Trophy size={32} color={isPass ? '#38bdf8' : '#f59e0b'} />
            </View>
          </View>

          {/* Quick Metrics Row */}
          <View style={styles.metricsRow}>
            <View style={styles.metricItem}>
              <CheckCircle2 size={16} color="#34d399" />
              <Text style={[styles.metricNum, { color: '#34d399' }]}>
                {results.correct_count}
              </Text>
              <Text style={styles.metricLabel}>Correct</Text>
            </View>

            <View style={styles.metricDivider} />

            <View style={styles.metricItem}>
              <XCircle size={16} color="#fb7185" />
              <Text style={[styles.metricNum, { color: '#fb7185' }]}>
                {results.incorrect_count}
              </Text>
              <Text style={styles.metricLabel}>Incorrect</Text>
            </View>

            <View style={styles.metricDivider} />

            <View style={styles.metricItem}>
              <Clock size={16} color="#94a3b8" />
              <Text style={styles.metricNum}>
                {Math.round((results.time_spent_seconds || 120) / 60)}m
              </Text>
              <Text style={styles.metricLabel}>Time Spent</Text>
            </View>
          </View>
        </Card>

        {/* Primary Action: Review Explanations */}
        <Button
          title="Review All Explanations & Citations"
          variant="gradient"
          size="lg"
          onPress={() => router.push(`/review/${attemptId}` as any)}
          icon={<BookOpen size={18} color="#ffffff" />}
          style={{ marginBottom: 18 }}
        />

        {/* Topic Breakdown */}
        {results.topic_breakdown && results.topic_breakdown.length > 0 ? (
          <>
            <Text style={styles.sectionHeading}>Topic Performance Breakdown</Text>
            <Card style={styles.breakdownCard}>
              {results.topic_breakdown.map((t, idx) => (
                <View
                  key={idx}
                  style={[
                    styles.topicRow,
                    idx < results.topic_breakdown.length - 1 ? styles.borderBottom : null,
                  ]}
                >
                  <View style={{ flex: 1, marginRight: 10 }}>
                    <Text style={styles.topicName}>{t.topic}</Text>
                    <Text style={styles.topicCounts}>
                      {t.correct}/{t.total} Correct
                    </Text>
                  </View>
                  <Text
                    style={[
                      styles.topicPct,
                      { color: t.accuracy >= 65 ? '#34d399' : '#fb7185' },
                    ]}
                  >
                    {Math.round(t.accuracy)}%
                  </Text>
                </View>
              ))}
            </Card>
          </>
        ) : null}

        {/* Bottom Actions */}
        <Button
          title="Return to Dashboard"
          variant="outline"
          size="md"
          onPress={() => router.replace('/(tabs)' as any)}
          icon={<Home size={16} color="#38bdf8" />}
          style={{ marginTop: 12 }}
        />
      </ScrollView>
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
    paddingBottom: 36,
  },
  homeBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroCard: {
    marginBottom: 16,
    backgroundColor: '#0f172a',
  },
  heroTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 18,
  },
  scoreTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#94a3b8',
    textTransform: 'uppercase',
  },
  scorePercentage: {
    fontSize: 44,
    fontWeight: '900',
    color: '#ffffff',
    letterSpacing: -1,
  },
  scoreSub: {
    fontSize: 13,
    color: '#cbd5e1',
    fontWeight: '600',
    marginTop: 2,
  },
  trophyBox: {
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    borderWidth: 1.5,
    borderColor: 'rgba(56, 189, 248, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  metricsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingTop: 14,
    borderTopWidth: 1,
    borderColor: '#334155',
  },
  metricItem: {
    alignItems: 'center',
    gap: 2,
  },
  metricNum: {
    fontSize: 18,
    fontWeight: '800',
    color: '#ffffff',
  },
  metricLabel: {
    fontSize: 11,
    color: '#94a3b8',
    fontWeight: '600',
  },
  metricDivider: {
    width: 1,
    height: 24,
    backgroundColor: '#334155',
  },
  sectionHeading: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 10,
  },
  breakdownCard: {
    backgroundColor: '#0f172a',
    padding: 12,
    marginBottom: 16,
  },
  topicRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  borderBottom: {
    borderBottomWidth: 1,
    borderColor: '#1e293b',
  },
  topicName: {
    fontSize: 13,
    fontWeight: '700',
    color: '#e2e8f0',
  },
  topicCounts: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
  },
  topicPct: {
    fontSize: 15,
    fontWeight: '800',
  },
});
