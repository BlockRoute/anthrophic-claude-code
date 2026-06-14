import React, { useEffect } from 'react';
import { View } from 'react-native';
import Animated, {
  useAnimatedProps,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle, Defs, LinearGradient, Stop } from 'react-native-svg';
import { AppText, Overline } from './ui';
import { palette } from '../lib/theme';

const ACircle = Animated.createAnimatedComponent(Circle);

export function ProgressRing({
  value,
  goal,
  size = 200,
  stroke = 16,
  label = 'kcal left',
  centerValue,
}: {
  value: number;
  goal: number;
  size?: number;
  stroke?: number;
  label?: string;
  centerValue?: string;
}) {
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const pct = goal > 0 ? Math.min(value / goal, 1) : 0;
  const over = value > goal;

  const progress = useSharedValue(0);
  useEffect(() => {
    progress.value = withTiming(pct, { duration: 900 });
  }, [pct, progress]);

  const animatedProps = useAnimatedProps(() => ({
    strokeDashoffset: circumference * (1 - progress.value),
  }));

  const remaining = Math.max(0, goal - value);

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute', transform: [{ rotate: '-90deg' }] }}>
        <Defs>
          <LinearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor="#74F0BA" />
            <Stop offset="1" stopColor={over ? palette.warn : palette.glowSoft} />
          </LinearGradient>
        </Defs>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={palette.surfaceRaised}
          strokeWidth={stroke}
          fill="none"
        />
        <ACircle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="url(#ring)"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={circumference}
          animatedProps={animatedProps}
        />
      </Svg>
      <View style={{ alignItems: 'center' }}>
        <AppText variant="numeral" style={{ fontSize: 46, lineHeight: 48 }}>
          {centerValue ?? remaining.toLocaleString()}
        </AppText>
        <Overline color={palette.inkMuted} style={{ marginTop: 4 }}>
          {over ? `${(value - goal).toLocaleString()} over` : label}
        </Overline>
      </View>
    </View>
  );
}
