import { useRouter } from 'expo-router';
import React from 'react';
import { View } from 'react-native';
import { Dropdown } from '../../components/Dropdown';
import { AppText, Button, Card, Overline, Screen } from '../../components/ui';
import { StepDots } from '../../components/inputs';
import { GOALS, goalById } from '../../lib/nutrition';
import { useOnboarding } from '../../lib/onboarding';
import { palette, spacing } from '../../lib/theme';

export default function GoalStep() {
  const router = useRouter();
  const d = useOnboarding();
  const goal = d.goal ? goalById(d.goal) : null;

  return (
    <Screen edges={['top', 'bottom']}>
      <StepDots total={4} index={2} />
      <Overline style={{ marginTop: spacing.xl }}>Your focus</Overline>
      <AppText variant="title" style={{ marginTop: spacing.sm, marginBottom: spacing.xl }}>
        What are you growing toward?
      </AppText>

      <Dropdown
        label="Goal"
        placeholder="Pick a goal…"
        value={d.goal}
        onChange={(goalId) => d.set({ goal: goalId })}
        options={GOALS.map((g) => ({ value: g.id, label: g.label, hint: g.blurb }))}
      />

      {goal && (
        <Card raised style={{ marginTop: spacing.xl, gap: spacing.md }}>
          <Overline color={palette.glowSoft}>{goal.label}</Overline>
          <AppText variant="body" color={palette.inkMuted}>{goal.blurb}.</AppText>
          <View style={{ flexDirection: 'row', gap: spacing.xl, marginTop: spacing.xs }}>
            <Stat
              label="Calories"
              value={
                goal.calorieDelta === 0
                  ? 'Maintenance'
                  : `${goal.calorieDelta > 0 ? '+' : ''}${goal.calorieDelta}`
              }
            />
            <Stat label="Protein" value={`${goal.proteinPerKg}g / kg`} />
          </View>
        </Card>
      )}

      <View style={{ flex: 1 }} />

      <Button
        label="See my plan"
        disabled={!d.goal}
        onPress={() => router.push('/(onboarding)/targets')}
        style={{ marginTop: spacing.xxl }}
      />
    </Screen>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View>
      <Overline color={palette.inkFaint}>{label}</Overline>
      <AppText variant="bodyMedium" style={{ marginTop: 4 }}>{value}</AppText>
    </View>
  );
}
