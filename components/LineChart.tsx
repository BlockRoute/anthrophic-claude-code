import React from 'react';
import { View } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Stop } from 'react-native-svg';
import { AppText } from './ui';
import { palette } from '../lib/theme';

export interface Point {
  x: string; // label
  y: number;
}

export function LineChart({
  points,
  width = 320,
  height = 160,
}: {
  points: Point[];
  width?: number;
  height?: number;
}) {
  if (points.length < 2) {
    return (
      <View style={{ height, alignItems: 'center', justifyContent: 'center' }}>
        <AppText variant="caption" color={palette.inkFaint}>
          Log your weight a few times to see your trend.
        </AppText>
      </View>
    );
  }

  const padX = 8;
  const padY = 18;
  const ys = points.map((p) => p.y);
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const range = max - min || 1;

  const px = (i: number) => padX + (i / (points.length - 1)) * (width - padX * 2);
  const py = (v: number) => padY + (1 - (v - min) / range) * (height - padY * 2);

  const line = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${px(i).toFixed(1)} ${py(p.y).toFixed(1)}`)
    .join(' ');
  const area = `${line} L ${px(points.length - 1).toFixed(1)} ${height - padY} L ${px(0).toFixed(1)} ${height - padY} Z`;

  const last = points.length - 1;

  return (
    <Svg width={width} height={height}>
      <Defs>
        <LinearGradient id="area" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor={palette.glow} stopOpacity={0.22} />
          <Stop offset="1" stopColor={palette.glow} stopOpacity={0} />
        </LinearGradient>
      </Defs>
      <Path d={area} fill="url(#area)" />
      <Path d={line} stroke={palette.glow} strokeWidth={2.5} fill="none" strokeLinejoin="round" strokeLinecap="round" />
      {points.map((p, i) => (
        <Circle
          key={i}
          cx={px(i)}
          cy={py(p.y)}
          r={i === last ? 4.5 : 2.5}
          fill={i === last ? palette.glow : palette.surfaceRaised}
          stroke={i === last ? palette.base : palette.glowSoft}
          strokeWidth={i === last ? 3 : 1}
        />
      ))}
    </Svg>
  );
}
