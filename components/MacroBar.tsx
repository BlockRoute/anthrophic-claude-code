import React from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText, Overline } from './ui';
import { palette, radii } from '../lib/theme';

export function MacroBar({
  label,
  value,
  goal,
  unit = 'g',
  color,
}: {
  label: string;
  value: number;
  goal: number;
  unit?: string;
  color: string;
}) {
  const pct = goal > 0 ? Math.min(value / goal, 1) : 0;
  return (
    <View style={styles.row}>
      <View style={styles.head}>
        <Overline color={palette.inkMuted}>{label}</Overline>
        <AppText variant="caption" color={palette.inkMuted}>
          <AppText variant="caption" color={palette.ink}>{Math.round(value)}</AppText>
          {` / ${goal}${unit}`}
        </AppText>
      </View>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${pct * 100}%`, backgroundColor: color }]} />
      </View>
    </View>
  );
}

export function MacroTriplet({
  protein,
  carbs,
  fat,
  goals,
}: {
  protein: number;
  carbs: number;
  fat: number;
  goals: { protein: number; carbs: number; fat: number };
}) {
  return (
    <View style={{ gap: 14 }}>
      <MacroBar label="Protein" value={protein} goal={goals.protein} color={palette.protein} />
      <MacroBar label="Carbs" value={carbs} goal={goals.carbs} color={palette.carbs} />
      <MacroBar label="Fat" value={fat} goal={goals.fat} color={palette.fat} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { gap: 7 },
  head: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  track: {
    height: 7,
    borderRadius: radii.pill,
    backgroundColor: palette.surfaceRaised,
    overflow: 'hidden',
  },
  fill: { height: '100%', borderRadius: radii.pill },
});
