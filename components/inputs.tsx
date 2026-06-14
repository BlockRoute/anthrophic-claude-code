import { Feather } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import React from 'react';
import {
  Pressable,
  StyleSheet,
  TextInput,
  type TextInputProps,
  View,
} from 'react-native';
import { AppText, Overline } from './ui';
import { palette, radii, spacing } from '../lib/theme';

export function TextField({
  label,
  ...props
}: TextInputProps & { label?: string }) {
  return (
    <View style={{ gap: spacing.sm }}>
      {label && <Overline color={palette.inkMuted}>{label}</Overline>}
      <TextInput
        placeholderTextColor={palette.inkFaint}
        style={styles.input}
        {...props}
      />
    </View>
  );
}

export function StepDots({ total, index }: { total: number; index: number }) {
  return (
    <View style={styles.dots}>
      {Array.from({ length: total }).map((_, i) => (
        <View
          key={i}
          style={[
            styles.dot,
            {
              width: i === index ? 22 : 7,
              backgroundColor: i <= index ? palette.glow : palette.surfaceRaised,
            },
          ]}
        />
      ))}
    </View>
  );
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <View style={styles.segment}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <Pressable
            key={opt.value}
            onPress={() => {
              void Haptics.selectionAsync();
              onChange(opt.value);
            }}
            style={[styles.segmentItem, active && styles.segmentItemActive]}
          >
            <AppText
              variant="label"
              color={active ? palette.void : palette.inkMuted}
            >
              {opt.label}
            </AppText>
          </Pressable>
        );
      })}
    </View>
  );
}

export function NumberStepper({
  label,
  value,
  onChange,
  step = 1,
  min = 0,
  max = 9999,
  suffix,
  format,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
  suffix?: string;
  format?: (v: number) => string;
}) {
  const bump = (dir: number) => {
    const next = Math.min(max, Math.max(min, Math.round((value + dir * step) * 10) / 10));
    void Haptics.selectionAsync();
    onChange(next);
  };
  return (
    <View style={{ gap: spacing.sm }}>
      <Overline color={palette.inkMuted}>{label}</Overline>
      <View style={styles.stepper}>
        <Pressable onPress={() => bump(-1)} style={styles.stepBtn} hitSlop={8}>
          <Feather name="minus" size={20} color={palette.ink} />
        </Pressable>
        <View style={styles.stepValue}>
          <AppText variant="numeral" style={{ fontSize: 28 }}>
            {format ? format(value) : value}
          </AppText>
          {suffix && (
            <AppText variant="bodyMedium" color={palette.inkMuted}>{suffix}</AppText>
          )}
        </View>
        <Pressable onPress={() => bump(1)} style={styles.stepBtn} hitSlop={8}>
          <Feather name="plus" size={20} color={palette.ink} />
        </Pressable>
      </View>
    </View>
  );
}

export function OptionRow({
  title,
  subtitle,
  selected,
  onPress,
  icon,
}: {
  title: string;
  subtitle?: string;
  selected: boolean;
  onPress: () => void;
  icon?: keyof typeof Feather.glyphMap;
}) {
  return (
    <Pressable
      onPress={() => {
        void Haptics.selectionAsync();
        onPress();
      }}
      style={[
        styles.option,
        {
          borderColor: selected ? 'rgba(91,231,168,0.5)' : palette.hairline,
          backgroundColor: selected ? palette.glowDeep : palette.surface,
        },
      ]}
    >
      {icon && (
        <View style={styles.optionIcon}>
          <Feather name={icon} size={18} color={selected ? palette.glow : palette.inkMuted} />
        </View>
      )}
      <View style={{ flex: 1 }}>
        <AppText variant="bodyMedium">{title}</AppText>
        {subtitle && (
          <AppText variant="caption" color={palette.inkMuted}>{subtitle}</AppText>
        )}
      </View>
      <View
        style={[
          styles.radio,
          { borderColor: selected ? palette.glow : palette.hairlineStrong },
        ]}
      >
        {selected && <View style={styles.radioDot} />}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  input: {
    backgroundColor: palette.surface,
    borderWidth: 1,
    borderColor: palette.hairline,
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
    height: 54,
    color: palette.ink,
    fontFamily: 'HankenGrotesk_500Medium',
    fontSize: 16,
  },
  dots: { flexDirection: 'row', gap: 6, alignItems: 'center' },
  dot: { height: 7, borderRadius: 4 },
  segment: {
    flexDirection: 'row',
    backgroundColor: palette.surface,
    borderRadius: radii.pill,
    padding: 4,
    borderWidth: 1,
    borderColor: palette.hairline,
  },
  segmentItem: {
    flex: 1,
    height: 42,
    borderRadius: radii.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  segmentItemActive: { backgroundColor: palette.glow },
  stepper: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: palette.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: palette.hairline,
    paddingHorizontal: spacing.sm,
    height: 72,
  },
  stepBtn: {
    width: 52,
    height: 52,
    borderRadius: radii.sm,
    backgroundColor: palette.surfaceRaised,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepValue: { flexDirection: 'row', alignItems: 'baseline', gap: 4 },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.lg,
    borderRadius: radii.md,
    borderWidth: 1,
  },
  optionIcon: {
    width: 40,
    height: 40,
    borderRadius: radii.sm,
    backgroundColor: palette.surfaceRaised,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radio: {
    width: 24,
    height: 24,
    borderRadius: radii.pill,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioDot: { width: 12, height: 12, borderRadius: radii.pill, backgroundColor: palette.glow },
});
