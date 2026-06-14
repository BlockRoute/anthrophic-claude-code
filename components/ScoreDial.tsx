import React from 'react';
import { View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { AppText, Overline } from './ui';
import { palette } from '../lib/theme';
import type { ScanVerdict } from '../lib/types';

export const VERDICT_COLOR: Record<ScanVerdict, string> = {
  excellent: palette.protein,
  good: '#A6E06F',
  fair: palette.warn,
  poor: palette.danger,
};

export const VERDICT_LABEL: Record<ScanVerdict, string> = {
  excellent: 'Excellent',
  good: 'Good',
  fair: 'Fair',
  poor: 'Poor',
};

export function ScoreDial({
  score,
  verdict,
  size = 96,
}: {
  score: number;
  verdict: ScanVerdict;
  size?: number;
}) {
  const stroke = 7;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.min(score / 100, 1);
  const color = VERDICT_COLOR[verdict];

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute', transform: [{ rotate: '-90deg' }] }}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={palette.surfaceRaised} strokeWidth={stroke} fill="none" />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
        />
      </Svg>
      <AppText variant="numeral" style={{ fontSize: size * 0.3 }} color={color}>
        {score}
      </AppText>
      <Overline color={palette.inkFaint} style={{ fontSize: 9 }}>/ 100</Overline>
    </View>
  );
}
