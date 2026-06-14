import { useRouter } from 'expo-router';
import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Plant } from '../../components/Plant';
import { AppText, Button, Card, Overline, Screen } from '../../components/ui';
import { StepDots } from '../../components/inputs';
import { computeTargets, goalById, macroCalories } from '../../lib/nutrition';
import { useOnboarding } from '../../lib/onboarding';
import { useStore } from '../../lib/store';
import type { PlantState } from '../../lib/plant';
import type { Profile } from '../../lib/types';
import { palette, spacing } from '../../lib/theme';

const SEED: PlantState = {
  stage: 'seed',
  stageIndex: 0,
  stageProgress: 0.3,
  growthPoints: 0,
  vitality: 1,
  withering: false,
  streak: 0,
  longestStreak: 0,
  todayRatio: 0,
};

export default function Targets() {
  const router = useRouter();
  const d = useOnboarding();
  const complete = useStore((s) => s.completeOnboarding);

  const profile: Profile = useMemo(
    () => ({
      name: d.name,
      sex: d.sex,
      age: d.age,
      heightCm: d.heightCm,
      weightKg: d.weightKg,
      activity: d.activity,
      goal: d.goal ?? 'maintain',
      units: d.units,
    }),
    [d],
  );

  const targets = useMemo(() => computeTargets(profile), [profile]);
  const goal = goalById(profile.goal);

  const finish = () => {
    complete(profile);
    router.replace('/(tabs)');
  };

  const macroPct = (grams: number, per: number) =>
    Math.round(((grams * per) / macroCalories(targets.protein, targets.carbs, targets.fat)) * 100);

  return (
    <Screen edges={['top', 'bottom']}>
      <StepDots total={4} index={3} />

      <View style={{ alignItems: 'center', marginTop: spacing.md }}>
        <Plant plant={SEED} size={150} />
        <Overline style={{ marginTop: spacing.xs }}>Your daily targets</Overline>
        <AppText variant="title" style={{ marginTop: spacing.xs, textAlign: 'center' }}>
          Tuned for {goal.label.toLowerCase()}
        </AppText>
      </View>

      <Card raised style={styles.calCard}>
        <View>
          <Overline color={palette.glowSoft}>Daily calories</Overline>
          <AppText variant="hero" color={palette.glow} style={{ marginTop: 4 }}>
            {targets.calories.toLocaleString()}
          </AppText>
        </View>
        <View style={styles.tdee}>
          <Row label="BMR" value={`${targets.bmr.toLocaleString()} kcal`} />
          <Row label="Maintenance" value={`${targets.tdee.toLocaleString()} kcal`} />
        </View>
      </Card>

      <View style={styles.macroGrid}>
        <MacroCard label="Protein" grams={targets.protein} pct={macroPct(targets.protein, 4)} color={palette.protein} />
        <MacroCard label="Carbs" grams={targets.carbs} pct={macroPct(targets.carbs, 4)} color={palette.carbs} />
        <MacroCard label="Fat" grams={targets.fat} pct={macroPct(targets.fat, 9)} color={palette.fat} />
      </View>

      <AppText variant="caption" color={palette.inkFaint} style={styles.note}>
        Estimates from the Mifflin–St Jeor equation. You can fine-tune anything
        later in your profile.
      </AppText>

      <View style={{ flex: 1 }} />
      <Button label="Plant my seed" onPress={finish} style={{ marginTop: spacing.xl }} />
    </Screen>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <AppText variant="caption" color={palette.inkMuted}>{label}</AppText>
      <AppText variant="caption" color={palette.ink}>{value}</AppText>
    </View>
  );
}

function MacroCard({ label, grams, pct, color }: { label: string; grams: number; pct: number; color: string }) {
  return (
    <Card style={styles.macroCard} padding={spacing.lg}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <AppText variant="numeral" style={{ fontSize: 24, marginTop: spacing.sm }}>{grams}<AppText variant="caption" color={palette.inkMuted}>g</AppText></AppText>
      <Overline color={palette.inkMuted} style={{ marginTop: 2 }}>{label}</Overline>
      <AppText variant="caption" color={palette.inkFaint}>{pct}% of intake</AppText>
    </Card>
  );
}

const styles = StyleSheet.create({
  calCard: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  tdee: { gap: spacing.sm, minWidth: 150 },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.lg },
  macroGrid: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.md },
  macroCard: { flex: 1 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  note: { marginTop: spacing.lg, lineHeight: 17 },
});
