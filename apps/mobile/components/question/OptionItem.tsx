/**
 * apps/mobile/components/question/OptionItem.tsx
 *
 * High-contrast mobile option choice component with instant feedback touch states.
 */

import React from 'react';
import { TouchableOpacity, View, Text, StyleSheet } from 'react-native';
import { Check, X } from 'lucide-react-native';

interface OptionItemProps {
  optionKey: 'A' | 'B' | 'C' | 'D';
  optionText: string;
  isSelected: boolean;
  onSelect?: () => void;
  disabled?: boolean;
  isReviewMode?: boolean;
  isCorrectOption?: boolean;
}

export function OptionItem({
  optionKey,
  optionText,
  isSelected,
  onSelect,
  disabled = false,
  isReviewMode = false,
  isCorrectOption = false,
}: OptionItemProps) {
  let containerStyle = styles.defaultContainer;
  let letterContainerStyle = styles.defaultLetterContainer;
  let letterTextStyle = styles.defaultLetterText;
  let textStyle = styles.defaultText;

  if (isReviewMode) {
    if (isCorrectOption) {
      containerStyle = styles.correctContainer;
      letterContainerStyle = styles.correctLetterContainer;
      letterTextStyle = styles.correctLetterText;
      textStyle = styles.correctText;
    } else if (isSelected && !isCorrectOption) {
      containerStyle = styles.incorrectContainer;
      letterContainerStyle = styles.incorrectLetterContainer;
      letterTextStyle = styles.incorrectLetterText;
      textStyle = styles.incorrectText;
    }
  } else if (isSelected) {
    containerStyle = styles.selectedContainer;
    letterContainerStyle = styles.selectedLetterContainer;
    letterTextStyle = styles.selectedLetterText;
    textStyle = styles.selectedText;
  }

  return (
    <TouchableOpacity
      activeOpacity={0.75}
      onPress={onSelect}
      disabled={disabled}
      style={[styles.baseContainer, containerStyle]}
    >
      <View style={[styles.letterBadge, letterContainerStyle]}>
        {isReviewMode && isCorrectOption ? (
          <Check size={16} color="#ffffff" strokeWidth={3} />
        ) : isReviewMode && isSelected && !isCorrectOption ? (
          <X size={16} color="#ffffff" strokeWidth={3} />
        ) : (
          <Text style={[styles.letterText, letterTextStyle]}>{optionKey}</Text>
        )}
      </View>
      <Text style={[styles.optionText, textStyle]}>{optionText}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  baseContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 16,
    borderWidth: 1.5,
    marginBottom: 10,
    minHeight: 56,
  },
  defaultContainer: {
    backgroundColor: '#0f172a', // Slate-900
    borderColor: '#334155', // Slate-700
  },
  selectedContainer: {
    backgroundColor: 'rgba(2, 132, 199, 0.15)', // Sky-600 tint
    borderColor: '#38bdf8', // Sky-400
  },
  correctContainer: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)', // Emerald-500 tint
    borderColor: '#10b981',
  },
  incorrectContainer: {
    backgroundColor: 'rgba(244, 63, 94, 0.15)', // Rose-500 tint
    borderColor: '#f43f5e',
  },
  letterBadge: {
    width: 32,
    height: 32,
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
  },
  defaultLetterContainer: {
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#475569',
  },
  selectedLetterContainer: {
    backgroundColor: '#0284c7',
    borderWidth: 1,
    borderColor: '#38bdf8',
  },
  correctLetterContainer: {
    backgroundColor: '#10b981',
    borderWidth: 1,
    borderColor: '#34d399',
  },
  incorrectLetterContainer: {
    backgroundColor: '#f43f5e',
    borderWidth: 1,
    borderColor: '#fb7185',
  },
  letterText: {
    fontSize: 14,
    fontWeight: '800',
  },
  defaultLetterText: {
    color: '#94a3b8',
  },
  selectedLetterText: {
    color: '#ffffff',
  },
  correctLetterText: {
    color: '#ffffff',
  },
  incorrectLetterText: {
    color: '#ffffff',
  },
  optionText: {
    flex: 1,
    fontSize: 15,
    lineHeight: 22,
    fontWeight: '600',
  },
  defaultText: {
    color: '#e2e8f0',
  },
  selectedText: {
    color: '#ffffff',
  },
  correctText: {
    color: '#34d399',
  },
  incorrectText: {
    color: '#fb7185',
  },
});
