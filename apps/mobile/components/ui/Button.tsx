/**
 * apps/mobile/components/ui/Button.tsx
 *
 * High-touch mobile button component with loading states and variants.
 */

import React from 'react';
import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  StyleSheet,
  ViewStyle,
  TextStyle,
  StyleProp,
} from 'react-native';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'gradient';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  icon,
  style,
  textStyle,
}: ButtonProps) {
  const getContainerStyle = (): ViewStyle => {
    const base: ViewStyle = styles.base;
    const sizeStyle: ViewStyle =
      size === 'sm' ? styles.sizeSm : size === 'lg' ? styles.sizeLg : styles.sizeMd;

    let variantStyle: ViewStyle = styles.variantPrimary;
    if (variant === 'secondary') variantStyle = styles.variantSecondary;
    else if (variant === 'outline') variantStyle = styles.variantOutline;
    else if (variant === 'ghost') variantStyle = styles.variantGhost;
    else if (variant === 'danger') variantStyle = styles.variantDanger;
    else if (variant === 'gradient') variantStyle = styles.variantGradient;

    if (disabled) {
      return { ...base, ...sizeStyle, ...variantStyle, opacity: 0.5 };
    }
    return { ...base, ...sizeStyle, ...variantStyle };
  };

  const getTextStyle = (): TextStyle => {
    const base: TextStyle = styles.textBase;
    const sizeText: TextStyle =
      size === 'sm' ? styles.textSm : size === 'lg' ? styles.textLg : styles.textMd;

    let variantText: TextStyle = styles.textPrimary;
    if (variant === 'outline') variantText = styles.textOutline;
    else if (variant === 'ghost') variantText = styles.textGhost;
    else if (variant === 'secondary') variantText = styles.textSecondary;

    return { ...base, ...sizeText, ...variantText };
  };

  return (
    <TouchableOpacity
      activeOpacity={0.75}
      onPress={onPress}
      disabled={disabled || loading}
      style={[getContainerStyle(), style]}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === 'outline' || variant === 'ghost' ? '#38bdf8' : '#ffffff'}
        />
      ) : (
        <>
          {icon ? <React.Fragment>{icon}</React.Fragment> : null}
          <Text style={[getTextStyle(), icon ? { marginLeft: 8 } : null, textStyle]}>{title}</Text>
        </>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 14,
  },
  sizeSm: {
    height: 38,
    paddingHorizontal: 14,
  },
  sizeMd: {
    height: 48,
    paddingHorizontal: 20,
  },
  sizeLg: {
    height: 56,
    paddingHorizontal: 24,
  },
  variantPrimary: {
    backgroundColor: '#0284c7', // Sky-600
  },
  variantSecondary: {
    backgroundColor: '#334155', // Slate-700
  },
  variantOutline: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: '#334155',
  },
  variantGhost: {
    backgroundColor: 'transparent',
  },
  variantDanger: {
    backgroundColor: '#e11d48', // Rose-600
  },
  variantGradient: {
    backgroundColor: '#0369a1', // Deep Sky
    shadowColor: '#38bdf8',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  textBase: {
    fontWeight: '700',
    textAlign: 'center',
  },
  textSm: {
    fontSize: 13,
  },
  textMd: {
    fontSize: 15,
  },
  textLg: {
    fontSize: 17,
  },
  textPrimary: {
    color: '#ffffff',
  },
  textSecondary: {
    color: '#e2e8f0',
  },
  textOutline: {
    color: '#38bdf8',
  },
  textGhost: {
    color: '#94a3b8',
  },
});
