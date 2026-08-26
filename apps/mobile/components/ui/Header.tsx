/**
 * apps/mobile/components/ui/Header.tsx
 *
 * Mobile top navigation bar with back navigation and right actions.
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { ArrowLeft } from 'lucide-react-native';

interface HeaderProps {
  title: string;
  subtitle?: string;
  onBack?: () => void;
  rightElement?: React.ReactNode;
}

export function Header({ title, subtitle, onBack, rightElement }: HeaderProps) {
  return (
    <View style={styles.header}>
      <View style={styles.leftContainer}>
        {onBack ? (
          <TouchableOpacity activeOpacity={0.7} onPress={onBack} style={styles.backButton}>
            <ArrowLeft size={20} color="#94a3b8" />
          </TouchableOpacity>
        ) : null}
        <View style={styles.titleContainer}>
          <Text style={styles.title} numberOfLines={1}>
            {title}
          </Text>
          {subtitle ? (
            <Text style={styles.subtitle} numberOfLines={1}>
              {subtitle}
            </Text>
          ) : null}
        </View>
      </View>

      {rightElement ? <View style={styles.rightContainer}>{rightElement}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
    backgroundColor: '#020617', // Slate-950
  },
  leftContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  backButton: {
    width: 38,
    height: 38,
    borderRadius: 10,
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  titleContainer: {
    flex: 1,
  },
  title: {
    fontSize: 17,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 1,
  },
  rightContainer: {
    marginLeft: 12,
  },
});
