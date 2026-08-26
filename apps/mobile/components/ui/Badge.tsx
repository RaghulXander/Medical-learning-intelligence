/**
 * apps/mobile/components/ui/Badge.tsx
 *
 * Status badge pill component.
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle, TextStyle, StyleProp } from 'react-native';

export type BadgeVariant = 'default' | 'verified' | 'outline' | 'warning' | 'danger' | 'purple';

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  icon?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
}

export function Badge({ label, variant = 'default', icon, style, textStyle }: BadgeProps) {
  let containerVariant: ViewStyle = styles.defaultContainer;
  let textVariant: TextStyle = styles.defaultText;

  if (variant === 'verified') {
    containerVariant = styles.verifiedContainer;
    textVariant = styles.verifiedText;
  } else if (variant === 'warning') {
    containerVariant = styles.warningContainer;
    textVariant = styles.warningText;
  } else if (variant === 'danger') {
    containerVariant = styles.dangerContainer;
    textVariant = styles.dangerText;
  } else if (variant === 'purple') {
    containerVariant = styles.purpleContainer;
    textVariant = styles.purpleText;
  } else if (variant === 'outline') {
    containerVariant = styles.outlineContainer;
    textVariant = styles.outlineText;
  }

  return (
    <View style={[styles.base, containerVariant, style]}>
      {icon ? <View style={{ marginRight: 4 }}>{icon}</View> : null}
      <Text style={[styles.baseText, textVariant, textStyle]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    paddingHorizontal: 9,
    paddingVertical: 3,
    borderRadius: 999,
    borderWidth: 1,
  },
  baseText: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  defaultContainer: {
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    borderColor: 'rgba(56, 189, 248, 0.3)',
  },
  defaultText: {
    color: '#38bdf8',
  },
  verifiedContainer: {
    backgroundColor: 'rgba(16, 185, 129, 0.12)',
    borderColor: 'rgba(16, 185, 129, 0.3)',
  },
  verifiedText: {
    color: '#34d399',
  },
  warningContainer: {
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    borderColor: 'rgba(245, 158, 11, 0.3)',
  },
  warningText: {
    color: '#fbbf24',
  },
  dangerContainer: {
    backgroundColor: 'rgba(244, 63, 94, 0.12)',
    borderColor: 'rgba(244, 63, 94, 0.3)',
  },
  dangerText: {
    color: '#fb7185',
  },
  purpleContainer: {
    backgroundColor: 'rgba(168, 85, 247, 0.12)',
    borderColor: 'rgba(168, 85, 247, 0.3)',
  },
  purpleText: {
    color: '#c084fc',
  },
  outlineContainer: {
    backgroundColor: 'transparent',
    borderColor: '#475569',
  },
  outlineText: {
    color: '#94a3b8',
  },
});
