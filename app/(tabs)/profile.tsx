import { Feather } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, StyleSheet, Switch, View } from 'react-native';
import { Dropdown } from '../../components/Dropdown';
import { AppText, Button, Card, Divider, Overline, Screen } from '../../components/ui';
import { TextField } from '../../components/inputs';
import { GOALS } from '../../lib/nutrition';
import { fmtTime } from '../../lib/notifications';
import { signOut } from '../../lib/auth';
import { useStore } from '../../lib/store';
import { isCloudEnabled } from '../../lib/supabase';
import { palette, radii, spacing } from '../../lib/theme';
import type { Habit } from '../../lib/types';

export default function ProfileTab() {
  const router = useRouter();
  const profile = useStore((s) => s.profile);
  const targets = useStore((s) => s.targets);
  const habits = useStore((s) => s.habits);
  const reminders = useStore((s) => s.reminders);
  const updateProfile = useStore((s) => s.updateProfile);
  const setReminders = useStore((s) => s.setReminders);
  const addHabit = useStore((s) => s.addHabit);
  const removeHabit = useStore((s) => s.removeHabit);
  const resetAll = useStore((s) => s.resetAll);
  const localUser = useStore((s) => s.localUser);

  const [newHabit, setNewHabit] = useState('');

  if (!profile || !targets) return <Screen><View /></Screen>;

  const logout = async () => {
    await signOut();
    resetAll();
    router.replace('/(onboarding)/welcome');
  };

  const addCustomHabit = () => {
    const label = newHabit.trim();
    if (!label) return;
    const habit: Habit = {
      id: `h_${Date.now().toString(36)}`,
      label,
      icon: 'star',
      core: false,
    };
    addHabit(habit);
    setNewHabit('');
  };

  return (
    <Screen>
      <View style={styles.head}>
        <View style={styles.avatar}>
          <AppText variant="title" color={palette.glow}>
            {(profile.name || 'Y')[0].toUpperCase()}
          </AppText>
        </View>
        <View>
          <AppText variant="title">{profile.name || 'You'}</AppText>
          <AppText variant="caption" color={palette.inkMuted}>
            {localUser?.email ?? (isCloudEnabled ? 'Synced account' : 'Local profile')}
          </AppText>
        </View>
      </View>

      {/* Goal */}
      <SectionTitle>Goal & targets</SectionTitle>
      <Card style={{ gap: spacing.lg }}>
        <Dropdown
          label="Current goal"
          value={profile.goal}
          onChange={(goal) => updateProfile({ goal })}
          options={GOALS.map((g) => ({ value: g.id, label: g.label, hint: g.blurb }))}
        />
        <Divider style={{ marginVertical: 0 }} />
        <View style={styles.targetRow}>
          <Target label="Calories" value={targets.calories.toLocaleString()} />
          <Target label="Protein" value={`${targets.protein}g`} />
          <Target label="Carbs" value={`${targets.carbs}g`} />
          <Target label="Fat" value={`${targets.fat}g`} />
        </View>
      </Card>

      {/* Reminders */}
      <SectionTitle>Reminders</SectionTitle>
      <Card style={{ gap: spacing.md }}>
        <ToggleRow
          icon="bell"
          label="Daily reminders"
          hint="Habit nudges & wind-down"
          value={reminders.enabled}
          onChange={(enabled) => setReminders({ enabled })}
        />
        {reminders.enabled && (
          <>
            <Divider style={{ marginVertical: spacing.xs }} />
            <TimeRow
              label="Morning nudge"
              hour={reminders.morningHour}
              minute={reminders.morningMinute}
              onChange={(h, m) => setReminders({ morningHour: h, morningMinute: m })}
            />
            <TimeRow
              label="Evening wind-down"
              hour={reminders.eveningHour}
              minute={reminders.eveningMinute}
              onChange={(h, m) => setReminders({ eveningHour: h, eveningMinute: m })}
            />
            <Divider style={{ marginVertical: spacing.xs }} />
            <ToggleRow
              icon="activity"
              label="Workout reminder"
              value={reminders.workoutEnabled}
              onChange={(workoutEnabled) => setReminders({ workoutEnabled })}
            />
            {reminders.workoutEnabled && (
              <TimeRow
                label="Workout time"
                hour={reminders.workoutHour}
                minute={reminders.workoutMinute}
                onChange={(h, m) => setReminders({ workoutHour: h, workoutMinute: m })}
              />
            )}
          </>
        )}
      </Card>

      {/* Habits */}
      <SectionTitle>Habits</SectionTitle>
      <Card style={{ gap: spacing.sm }}>
        {habits.map((h) => (
          <View key={h.id} style={styles.habitRow}>
            <Feather name={h.icon as any} size={16} color={h.core ? palette.glow : palette.inkMuted} />
            <AppText variant="bodyMedium" style={{ flex: 1 }}>{h.label}</AppText>
            {h.core ? (
              <AppText variant="caption" color={palette.glowSoft}>core</AppText>
            ) : (
              <Pressable onPress={() => removeHabit(h.id)} hitSlop={8}>
                <Feather name="trash-2" size={16} color={palette.inkFaint} />
              </Pressable>
            )}
          </View>
        ))}
        <View style={styles.addHabit}>
          <View style={{ flex: 1 }}>
            <TextField placeholder="Add a habit…" value={newHabit} onChangeText={setNewHabit} />
          </View>
          <Pressable onPress={addCustomHabit} style={styles.addBtn}>
            <Feather name="plus" size={20} color={palette.void} />
          </Pressable>
        </View>
      </Card>

      <View style={{ marginTop: spacing.xxl }}>
        <Button
          label={isCloudEnabled ? 'Sign out' : 'Reset & start over'}
          variant="ghost"
          icon={<Feather name="log-out" size={16} color={palette.ink} />}
          onPress={logout}
        />
      </View>

      <AppText variant="caption" color={palette.inkFaint} style={styles.footer}>
        Verdant · {isCloudEnabled ? 'Cloud sync on' : 'Local mode'} · Data from Open Food Facts
      </AppText>
    </Screen>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <Overline color={palette.inkMuted} style={{ marginTop: spacing.xl, marginBottom: spacing.md }}>{children}</Overline>;
}

function Target({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flex: 1 }}>
      <AppText variant="bodyMedium" color={palette.glow}>{value}</AppText>
      <Overline color={palette.inkFaint}>{label}</Overline>
    </View>
  );
}

function ToggleRow({
  icon,
  label,
  hint,
  value,
  onChange,
}: {
  icon: keyof typeof Feather.glyphMap;
  label: string;
  hint?: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <View style={styles.toggleRow}>
      <View style={styles.toggleIcon}>
        <Feather name={icon} size={16} color={value ? palette.glow : palette.inkMuted} />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyMedium">{label}</AppText>
        {hint && <AppText variant="caption" color={palette.inkFaint}>{hint}</AppText>}
      </View>
      <Switch
        value={value}
        onValueChange={onChange}
        trackColor={{ false: palette.surfaceRaised, true: palette.glowSoft }}
        thumbColor={value ? palette.glow : palette.inkMuted}
      />
    </View>
  );
}

function TimeRow({
  label,
  hour,
  minute,
  onChange,
}: {
  label: string;
  hour: number;
  minute: number;
  onChange: (h: number, m: number) => void;
}) {
  const step = (dir: number) => {
    let total = hour * 60 + minute + dir * 15;
    total = (total + 1440) % 1440;
    onChange(Math.floor(total / 60), total % 60);
  };
  return (
    <View style={styles.timeRow}>
      <AppText variant="bodyMedium" color={palette.inkMuted}>{label}</AppText>
      <View style={styles.timeControl}>
        <Pressable onPress={() => step(-1)} hitSlop={6} style={styles.timeBtn}>
          <Feather name="chevron-down" size={16} color={palette.inkMuted} />
        </Pressable>
        <AppText variant="bodyMedium" style={{ minWidth: 78, textAlign: 'center' }}>
          {fmtTime(hour, minute)}
        </AppText>
        <Pressable onPress={() => step(1)} hitSlop={6} style={styles.timeBtn}>
          <Feather name="chevron-up" size={16} color={palette.inkMuted} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, marginTop: spacing.sm },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: radii.pill,
    backgroundColor: palette.glowDeep,
    borderWidth: 1,
    borderColor: 'rgba(91,231,168,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  targetRow: { flexDirection: 'row' },
  toggleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  toggleIcon: {
    width: 34, height: 34, borderRadius: radii.sm,
    backgroundColor: palette.surfaceRaised, alignItems: 'center', justifyContent: 'center',
  },
  timeRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  timeControl: { flexDirection: 'row', alignItems: 'center', backgroundColor: palette.surfaceRaised, borderRadius: radii.pill, paddingHorizontal: spacing.xs },
  timeBtn: { width: 32, height: 32, alignItems: 'center', justifyContent: 'center' },
  habitRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingVertical: 4 },
  addHabit: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center', marginTop: spacing.xs },
  addBtn: { width: 54, height: 54, borderRadius: radii.md, backgroundColor: palette.glow, alignItems: 'center', justifyContent: 'center' },
  footer: { textAlign: 'center', marginTop: spacing.xl },
});
