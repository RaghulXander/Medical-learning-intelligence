/**
 * apps/mobile/components/ui/Timer.tsx
 *
 * Authoritative countdown timer widget for timed mobile examinations.
 */

import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Clock } from 'lucide-react-native';

interface TimerProps {
  initialSeconds: number;
  onTimeExpired?: () => void;
}

export function Timer({ initialSeconds, onTimeExpired }: TimerProps) {
  const [secondsRemaining, setSecondsRemaining] = useState(initialSeconds);

  useEffect(() => {
    setSecondsRemaining(initialSeconds);
  }, [initialSeconds]);

  useEffect(() => {
    if (secondsRemaining <= 0) {
      if (onTimeExpired) onTimeExpired();
      return;
    }

    const interval = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          if (onTimeExpired) onTimeExpired();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [secondsRemaining, onTimeExpired]);

  const hours = Math.floor(secondsRemaining / 3600);
  const minutes = Math.floor((secondsRemaining % 3600) / 60);
  const seconds = secondsRemaining % 60;

  const formattedTime =
    hours > 0
      ? `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
      : `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

  const isUrgent = secondsRemaining < 300; // < 5 mins
  const isCritical = secondsRemaining < 60; // < 1 min

  const containerColor = isCritical
    ? styles.criticalContainer
    : isUrgent
    ? styles.urgentContainer
    : styles.normalContainer;

  const textColor = isCritical
    ? styles.criticalText
    : isUrgent
    ? styles.urgentText
    : styles.normalText;

  const iconColor = isCritical ? '#f43f5e' : isUrgent ? '#f59e0b' : '#38bdf8';

  return (
    <View style={[styles.container, containerColor]}>
      <Clock size={15} color={iconColor} style={{ marginRight: 6 }} />
      <Text style={[styles.timeText, textColor]}>{formattedTime}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    borderWidth: 1,
  },
  timeText: {
    fontFamily: 'monospace',
    fontWeight: '800',
    fontSize: 14,
  },
  normalContainer: {
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    borderColor: 'rgba(56, 189, 248, 0.3)',
  },
  normalText: {
    color: '#38bdf8',
  },
  urgentContainer: {
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    borderColor: 'rgba(245, 158, 11, 0.4)',
  },
  urgentText: {
    color: '#fbbf24',
  },
  criticalContainer: {
    backgroundColor: 'rgba(244, 63, 94, 0.2)',
    borderColor: 'rgba(244, 63, 94, 0.5)',
  },
  criticalText: {
    color: '#f43f5e',
  },
});
