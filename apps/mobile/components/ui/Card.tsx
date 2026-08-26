/**
 * apps/mobile/components/ui/Card.tsx
 *
 * Rich dark slate mobile card container with crisp borders and optional glow.
 */

import React from 'react';
import { View, StyleSheet, ViewStyle, StyleProp } from 'react-native';

interface CardProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  variant?: 'default' | 'highlight' | 'warning' | 'success' | 'danger';
}

export function Card({ children, style, variant = 'default' }: CardProps) {
  let borderStyle: ViewStyle = styles.defaultBorder;
  if (variant === 'highlight') borderStyle = styles.highlightBorder;
  else if (variant === 'warning') borderStyle = styles.warningBorder;
  else if (variant === 'success') borderStyle = styles.successBorder;
  else if (variant === 'danger') borderStyle = styles.dangerBorder;

  return <View style={[styles.card, borderStyle, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#0f172a', // Slate-900
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
  },
  defaultBorder: {
    borderColor: '#334155', // Slate-700
  },
  highlightBorder: {
    borderColor: 'rgba(56, 189, 248, 0.4)', // Sky-400
  },
  warningBorder: {
    borderColor: 'rgba(245, 158, 11, 0.4)', // Amber-500
  },
  successBorder: {
    borderColor: 'rgba(16, 185, 129, 0.4)', // Emerald-500
  },
  dangerBorder: {
    borderColor: 'rgba(244, 63, 94, 0.4)', // Rose-500
  },
});
