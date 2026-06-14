import { Feather } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import { AppText } from './ui';
import { palette, radii, spacing } from '../lib/theme';
import type { Habit } from '../lib/types';

export function HabitRow({
  habit,
  done,
  onToggle,
}: {
  habit: Habit;
  done: boolean;
  onToggle: () => void;
}) {
  const scale = useSharedValue(1);

  const press = () => {
    void Haptics.impactAsync(
      done ? Haptics.ImpactFeedbackStyle.Light : Haptics.ImpactFeedbackStyle.Medium,
    );
    scale.value = withSpring(0.96, { damping: 12 }, () => {
      scale.value = withSpring(1);
    });
    onToggle();
  };

  const boxStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <Pressable onPress={press}>
      <Animated.View
        style={[
          styles.row,
          boxStyle,
          {
            backgroundColor: done ? palette.glowDeep : palette.surface,
            borderColor: done ? 'rgba(91,231,168,0.35)' : palette.hairline,
          },
        ]}
      >
        <View
          style={[
            styles.icon,
            { backgroundColor: done ? 'rgba(91,231,168,0.18)' : palette.surfaceRaised },
          ]}
        >
          <Feather
            name={habit.icon as any}
            size={18}
            color={done ? palette.glow : palette.inkMuted}
          />
        </View>
        <View style={{ flex: 1 }}>
          <AppText variant="bodyMedium" color={done ? palette.ink : palette.ink}>
            {habit.label}
          </AppText>
          {habit.core && (
            <AppText variant="caption" color={done ? palette.glowSoft : palette.inkFaint}>
              Nurtures your tree
            </AppText>
          )}
        </View>
        <View
          style={[
            styles.check,
            {
              backgroundColor: done ? palette.glow : 'transparent',
              borderColor: done ? palette.glow : palette.hairlineStrong,
            },
          ]}
        >
          {done && <Feather name="check" size={15} color={palette.void} />}
        </View>
      </Animated.View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radii.md,
    borderWidth: 1,
  },
  icon: {
    width: 38,
    height: 38,
    borderRadius: radii.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  check: {
    width: 26,
    height: 26,
    borderRadius: radii.pill,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
