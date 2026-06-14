import { Feather } from '@expo/vector-icons';
import React, { useMemo, useState } from 'react';
import { Dimensions, Pressable, StyleSheet, View } from 'react-native';
import { LineChart, type Point } from '../../components/LineChart';
import { Plant } from '../../components/Plant';
import { AppText, Button, Card, Overline, Screen } from '../../components/ui';
import { lastNDays, todayKey, weekdayShort } from '../../lib/date';
import { kgToLb } from '../../lib/nutrition';
import { STAGE_LABEL, computePlant } from '../../lib/plant';
import { useStore } from '../../lib/store';
import { palette, radii, spacing } from '../../lib/theme';

export default function Progress() {
  const profile = useStore((s) => s.profile);
  const habits = useStore((s) => s.habits);
  const logs = useStore((s) => s.logs);
  const logWeight = useStore((s) => s.logWeight);
  const [logging, setLogging] = useState(false);

  const plant = useMemo(() => computePlant(logs, habits, todayKey()), [logs, habits]);

  const weightPoints: Point[] = useMemo(() => {
    const entries = Object.values(logs)
      .filter((l) => typeof l.weightKg === 'number')
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-12);
    return entries.map((l) => ({ x: l.date, y: l.weightKg as number }));
  }, [logs]);

  const coreIds = habits.filter((h) => h.core).map((h) => h.id);
  const week = useMemo(() => {
    return lastNDays(7).map((key) => {
      const log = logs[key];
      const done = coreIds.length
        ? coreIds.filter((id) => log?.completedHabits.includes(id)).length / coreIds.length
        : 0;
      return { key, ratio: done };
    });
  }, [logs, coreIds]);

  if (!profile) return <Screen><View /></Screen>;

  const metric = profile.units === 'metric';
  const startW = weightPoints[0]?.y;
  const nowW = weightPoints[weightPoints.length - 1]?.y ?? profile.weightKg;
  const delta = startW != null ? nowW - startW : 0;
  const fmtW = (kg: number) => (metric ? `${kg.toFixed(1)} kg` : `${kgToLb(kg)} lb`);
  const chartWidth = Dimensions.get('window').width - spacing.xl * 2 - spacing.lg * 2;

  return (
    <Screen>
      <Overline color={palette.inkMuted}>Progress</Overline>
      <AppText variant="title" style={{ marginTop: 2, marginBottom: spacing.lg }}>
        How you’re growing
      </AppText>

      {/* Plant summary */}
      <Card raised style={styles.plantCard} padding={spacing.lg}>
        <Plant plant={plant} size={120} />
        <View style={{ flex: 1, gap: spacing.sm }}>
          <Overline color={palette.glowSoft}>{STAGE_LABEL[plant.stage]}</Overline>
          <View style={styles.statRow}>
            <Stat value={`${plant.streak}`} label="Day streak" />
            <Stat value={`${plant.longestStreak}`} label="Best" />
            <Stat value={`${Math.round(plant.vitality * 100)}%`} label="Vitality" />
          </View>
        </View>
      </Card>

      {/* Weekly consistency */}
      <Overline color={palette.inkMuted} style={styles.sectionLabel}>Last 7 days</Overline>
      <Card style={styles.weekCard}>
        {week.map((d) => (
          <View key={d.key} style={styles.dayCol}>
            <View style={styles.barTrack}>
              <View
                style={[
                  styles.barFill,
                  {
                    height: `${Math.max(6, d.ratio * 100)}%`,
                    backgroundColor: d.ratio >= 0.999 ? palette.glow : d.ratio > 0 ? palette.glowSoft : palette.surfaceRaised,
                  },
                ]}
              />
            </View>
            <AppText variant="caption" color={palette.inkFaint} style={{ fontSize: 10 }}>
              {weekdayShort(d.key)[0]}
            </AppText>
          </View>
        ))}
      </Card>

      {/* Weight */}
      <View style={styles.sectionHead}>
        <Overline color={palette.inkMuted}>Weight trend</Overline>
        <Pressable onPress={() => setLogging(true)} hitSlop={8} style={styles.addWeight}>
          <Feather name="plus" size={14} color={palette.glow} />
          <AppText variant="caption" color={palette.glow}>Log</AppText>
        </Pressable>
      </View>
      <Card style={{ gap: spacing.md }}>
        <View style={styles.weightHead}>
          <View>
            <AppText variant="numeral" style={{ fontSize: 30 }}>{fmtW(nowW)}</AppText>
            <Overline color={palette.inkFaint}>Current</Overline>
          </View>
          {startW != null && (
            <View style={{ alignItems: 'flex-end' }}>
              <AppText
                variant="heading"
                color={delta <= 0 ? palette.protein : palette.warn}
              >
                {delta > 0 ? '+' : ''}{metric ? delta.toFixed(1) : kgToLb(delta)}
              </AppText>
              <Overline color={palette.inkFaint}>{metric ? 'kg' : 'lb'} change</Overline>
            </View>
          )}
        </View>
        <LineChart points={weightPoints} width={chartWidth} />
      </Card>

      {logging && (
        <WeightLogger
          unit={metric ? 'kg' : 'lb'}
          current={metric ? nowW : kgToLb(nowW)}
          onCancel={() => setLogging(false)}
          onSave={(value) => {
            const kg = metric ? value : value / 2.20462;
            logWeight(Math.round(kg * 10) / 10);
            setLogging(false);
          }}
        />
      )}
    </Screen>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <View>
      <AppText variant="numeral" style={{ fontSize: 22 }}>{value}</AppText>
      <Overline color={palette.inkFaint}>{label}</Overline>
    </View>
  );
}

function WeightLogger({
  current,
  unit,
  onSave,
  onCancel,
}: {
  current: number;
  unit: string;
  onSave: (v: number) => void;
  onCancel: () => void;
}) {
  const [v, setV] = useState(Math.round(current * 10) / 10);
  return (
    <View style={styles.loggerWrap}>
      <Card raised style={{ gap: spacing.lg }}>
        <Overline color={palette.glowSoft}>Log today’s weight</Overline>
        <View style={styles.logger}>
          <Pressable onPress={() => setV((x) => Math.max(20, Math.round((x - 0.1) * 10) / 10))} style={styles.logBtn}>
            <Feather name="minus" size={20} color={palette.ink} />
          </Pressable>
          <AppText variant="numeral" style={{ fontSize: 34 }}>
            {v.toFixed(1)}<AppText variant="body" color={palette.inkMuted}> {unit}</AppText>
          </AppText>
          <Pressable onPress={() => setV((x) => Math.round((x + 0.1) * 10) / 10)} style={styles.logBtn}>
            <Feather name="plus" size={20} color={palette.ink} />
          </Pressable>
        </View>
        <View style={{ flexDirection: 'row', gap: spacing.md }}>
          <Button label="Cancel" variant="ghost" onPress={onCancel} style={{ flex: 1 }} />
          <Button label="Save" onPress={() => onSave(v)} style={{ flex: 1 }} />
        </View>
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  plantCard: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  statRow: { flexDirection: 'row', gap: spacing.xl },
  sectionLabel: { marginTop: spacing.xl, marginBottom: spacing.md },
  weekCard: { flexDirection: 'row', justifyContent: 'space-between', height: 130, alignItems: 'flex-end' },
  dayCol: { flex: 1, alignItems: 'center', gap: spacing.sm, height: '100%', justifyContent: 'flex-end' },
  barTrack: { width: 14, flex: 1, justifyContent: 'flex-end', borderRadius: radii.pill, backgroundColor: palette.base, overflow: 'hidden' },
  barFill: { width: '100%', borderRadius: radii.pill },
  sectionHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: spacing.xl, marginBottom: spacing.md },
  addWeight: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  weightHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  loggerWrap: { marginTop: spacing.lg },
  logger: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  logBtn: { width: 52, height: 52, borderRadius: radii.sm, backgroundColor: palette.surfaceRaised, alignItems: 'center', justifyContent: 'center' },
});
