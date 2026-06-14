import { useRouter } from 'expo-router';
import React from 'react';
import { View } from 'react-native';
import { AppText, Button, Overline, Screen } from '../../components/ui';
import {
  NumberStepper,
  OptionRow,
  SegmentedControl,
  StepDots,
} from '../../components/inputs';
import { ACTIVITY_OPTIONS, cmToFtIn, kgToLb } from '../../lib/nutrition';
import { useOnboarding } from '../../lib/onboarding';
import { spacing } from '../../lib/theme';

export default function ProfileStep() {
  const router = useRouter();
  const d = useOnboarding();

  const heightLabel = (cm: number) => {
    if (d.units === 'metric') return `${cm}`;
    const { ft, inch } = cmToFtIn(cm);
    return `${ft}'${inch}"`;
  };
  const weightLabel = (kg: number) =>
    d.units === 'metric' ? `${kg}` : `${kgToLb(kg)}`;

  return (
    <Screen edges={['top', 'bottom']}>
      <StepDots total={4} index={1} />
      <Overline style={{ marginTop: spacing.xl }}>About you</Overline>
      <AppText variant="title" style={{ marginTop: spacing.sm, marginBottom: spacing.xl }}>
        The numbers behind your plan
      </AppText>

      <View style={{ gap: spacing.xl }}>
        <View style={{ gap: spacing.sm }}>
          <Overline>Units</Overline>
          <SegmentedControl
            value={d.units}
            onChange={(units) => d.set({ units })}
            options={[
              { value: 'metric', label: 'Metric' },
              { value: 'imperial', label: 'Imperial' },
            ]}
          />
        </View>

        <View style={{ gap: spacing.sm }}>
          <Overline>Sex (for metabolic rate)</Overline>
          <SegmentedControl
            value={d.sex}
            onChange={(sex) => d.set({ sex })}
            options={[
              { value: 'female', label: 'Female' },
              { value: 'male', label: 'Male' },
            ]}
          />
        </View>

        <NumberStepper
          label="Age"
          value={d.age}
          onChange={(age) => d.set({ age })}
          min={13}
          max={100}
          suffix="yrs"
        />

        <NumberStepper
          label="Height"
          value={d.heightCm}
          onChange={(heightCm) => d.set({ heightCm })}
          step={d.units === 'metric' ? 1 : 2}
          min={120}
          max={220}
          suffix={d.units === 'metric' ? 'cm' : ''}
          format={heightLabel}
        />

        <NumberStepper
          label="Weight"
          value={d.weightKg}
          onChange={(weightKg) => d.set({ weightKg })}
          step={d.units === 'metric' ? 0.5 : 1}
          min={35}
          max={250}
          suffix={d.units === 'metric' ? 'kg' : 'lb'}
          format={weightLabel}
        />

        <View style={{ gap: spacing.sm }}>
          <Overline>Activity level</Overline>
          <View style={{ gap: spacing.sm }}>
            {ACTIVITY_OPTIONS.map((opt) => (
              <OptionRow
                key={opt.id}
                title={opt.label}
                subtitle={opt.hint}
                selected={d.activity === opt.id}
                onPress={() => d.set({ activity: opt.id })}
              />
            ))}
          </View>
        </View>
      </View>

      <Button
        label="Choose your goal"
        onPress={() => router.push('/(onboarding)/goal')}
        style={{ marginTop: spacing.xxl }}
      />
    </Screen>
  );
}
