import { Feather } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { HabitRow } from '../../components/HabitRow';
import { MacroTriplet } from '../../components/MacroBar';
import { Plant } from '../../components/Plant';
import { ProgressRing } from '../../components/ProgressRing';
import { AppText, Card, Overline, PressFx, Screen } from '../../components/ui';
import { prettyDate, todayKey } from '../../lib/date';
import { STAGE_LABEL, computePlant, encouragement } from '../../lib/plant';
import { dayTotals, useStore } from '../../lib/store';
import { palette, radii, spacing } from '../../lib/theme';

export default function Today() {
  const router = useRouter();
  const today = todayKey();

  const profile = useStore((s) => s.profile);
  const targets = useStore((s) => s.targets);
  const habits = useStore((s) => s.habits);
  const logs = useStore((s) => s.logs);
  const foods = useStore((s) => s.foods);
  const toggleHabit = useStore((s) => s.toggleHabit);

  const plant = useMemo(() => computePlant(logs, habits, today), [logs, habits, today]);
  const todayLog = logs[today];
  const todays = useMemo(() => foods.filter((f) => f.date === today), [foods, today]);
  const totals = useMemo(() => dayTotals(todays), [todays]);

  if (!targets || !profile) return <Screen><View /></Screen>;

  const greeting = greetByHour();

  return (
    <Screen>
      <View style={styles.header}>
        <View>
          <Overline color={palette.inkMuted}>{prettyDate(today)}</Overline>
          <AppText variant="title" style={{ marginTop: 2 }}>
            {greeting}, {profile.name || 'friend'}
          </AppText>
        </View>
        <View style={styles.streak}>
          <Feather name="zap" size={14} color={palette.glow} />
          <AppText variant="label" color={palette.glow}>{plant.streak}</AppText>
        </View>
      </View>

      {/* The tree */}
      <Card raised style={styles.treeCard} padding={spacing.lg}>
        <View style={styles.treeRow}>
          <Plant plant={plant} size={150} />
          <View style={styles.treeMeta}>
            <Overline color={palette.glowSoft}>{STAGE_LABEL[plant.stage]}</Overline>
            <AppText variant="heading" style={{ marginTop: 4 }}>
              {plant.withering ? 'Needs care' : plant.todayRatio >= 1 ? 'Thriving' : 'Growing'}
            </AppText>
            <View style={styles.growthTrack}>
              <View style={[styles.growthFill, { width: `${plant.stageProgress * 100}%` }]} />
            </View>
            <AppText variant="caption" color={palette.inkMuted}>
              {Math.round(plant.stageProgress * 100)}% to next stage
            </AppText>
          </View>
        </View>
        <View style={styles.encourage}>
          <Feather name="feather" size={14} color={palette.glowSoft} />
          <AppText variant="caption" color={palette.inkMuted} style={{ flex: 1 }}>
            {encouragement(plant)}
          </AppText>
        </View>
      </Card>

      {/* Calories + macros */}
      <PressFx onPress={() => router.push('/(tabs)/nutrition')}>
        <Card style={styles.nutriCard}>
          <ProgressRing value={totals.calories} goal={targets.calories} size={172} stroke={14} />
          <View style={styles.macros}>
            <MacroTriplet
              protein={totals.protein}
              carbs={totals.carbs}
              fat={totals.fat}
              goals={{ protein: targets.protein, carbs: targets.carbs, fat: targets.fat }}
            />
            <View style={styles.eaten}>
              <AppText variant="caption" color={palette.inkMuted}>
                {Math.round(totals.calories).toLocaleString()} eaten · {targets.calories.toLocaleString()} goal
              </AppText>
            </View>
          </View>
        </Card>
      </PressFx>

      {/* Habits */}
      <View style={styles.sectionHead}>
        <Overline color={palette.inkMuted}>Today’s habits</Overline>
        <AppText variant="caption" color={palette.glowSoft}>
          {todayLog?.completedHabits.length ?? 0}/{habits.length} done
        </AppText>
      </View>
      <View style={{ gap: spacing.sm }}>
        {habits.map((h) => (
          <HabitRow
            key={h.id}
            habit={h}
            done={todayLog?.completedHabits.includes(h.id) ?? false}
            onToggle={() => toggleHabit(h.id)}
          />
        ))}
      </View>
    </Screen>
  );
}

function greetByHour() {
  const h = new Date().getHours();
  if (h < 12) return 'Morning';
  if (h < 18) return 'Afternoon';
  return 'Evening';
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  streak: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: palette.glowDeep,
    borderColor: 'rgba(91,231,168,0.3)',
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radii.pill,
  },
  treeCard: { overflow: 'hidden' },
  treeRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  treeMeta: { flex: 1, gap: 6 },
  growthTrack: {
    height: 6,
    borderRadius: radii.pill,
    backgroundColor: palette.base,
    overflow: 'hidden',
    marginTop: 2,
  },
  growthFill: { height: '100%', backgroundColor: palette.glow, borderRadius: radii.pill },
  encourage: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: palette.hairline,
  },
  nutriCard: {
    marginTop: spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
  },
  macros: { flex: 1, gap: spacing.md },
  eaten: { marginTop: 2 },
  sectionHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.xl,
    marginBottom: spacing.md,
  },
});
