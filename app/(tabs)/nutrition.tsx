import { Feather } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React, { useMemo, useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import { MacroTriplet } from '../../components/MacroBar';
import { ProgressRing } from '../../components/ProgressRing';
import { AppText, Button, Card, Overline, Screen } from '../../components/ui';
import { TextField } from '../../components/inputs';
import { todayKey } from '../../lib/date';
import { macroCalories } from '../../lib/nutrition';
import { dayTotals, useStore } from '../../lib/store';
import { palette, radii, spacing } from '../../lib/theme';

export default function Nutrition() {
  const router = useRouter();
  const today = todayKey();
  const targets = useStore((s) => s.targets);
  const foods = useStore((s) => s.foods);
  const addFood = useStore((s) => s.addFood);
  const removeFood = useStore((s) => s.removeFood);
  const [adding, setAdding] = useState(false);

  const todays = useMemo(() => foods.filter((f) => f.date === today), [foods, today]);
  const totals = useMemo(() => dayTotals(todays), [todays]);
  if (!targets) return <Screen><View /></Screen>;

  return (
    <Screen>
      <Overline color={palette.inkMuted}>Nutrition</Overline>
      <AppText variant="title" style={{ marginTop: 2, marginBottom: spacing.lg }}>
        Today’s plate
      </AppText>

      <Card raised style={styles.summary}>
        <ProgressRing value={totals.calories} goal={targets.calories} size={150} stroke={13} />
        <View style={styles.summaryMacros}>
          <MacroTriplet
            protein={totals.protein}
            carbs={totals.carbs}
            fat={totals.fat}
            goals={{ protein: targets.protein, carbs: targets.carbs, fat: targets.fat }}
          />
        </View>
      </Card>

      <View style={styles.actions}>
        <Button
          label="Scan a product"
          variant="ghost"
          icon={<Feather name="maximize" size={16} color={palette.glow} />}
          onPress={() => router.push('/(tabs)/scan')}
          style={{ flex: 1 }}
        />
        <Button
          label="Add manually"
          variant="outline"
          icon={<Feather name="plus" size={16} color={palette.ink} />}
          onPress={() => setAdding(true)}
          style={{ flex: 1 }}
        />
      </View>

      <Overline color={palette.inkMuted} style={{ marginTop: spacing.xl, marginBottom: spacing.md }}>
        {todays.length} {todays.length === 1 ? 'entry' : 'entries'}
      </Overline>

      {todays.length === 0 ? (
        <Card style={styles.empty}>
          <Feather name="coffee" size={26} color={palette.inkFaint} />
          <AppText variant="bodyMedium" color={palette.inkMuted} style={{ marginTop: spacing.sm }}>
            Nothing logged yet
          </AppText>
          <AppText variant="caption" color={palette.inkFaint} style={{ textAlign: 'center' }}>
            Scan a barcode or add a meal to start filling your ring.
          </AppText>
        </Card>
      ) : (
        <View style={{ gap: spacing.sm }}>
          {todays.map((f) => (
            <Card key={f.id} style={styles.entry} padding={spacing.md}>
              <View style={{ flex: 1 }}>
                <AppText variant="bodyMedium">{f.name}</AppText>
                <AppText variant="caption" color={palette.inkMuted}>
                  {f.brand ? `${f.brand} · ` : ''}
                  {f.protein}P · {f.carbs}C · {f.fat}F
                  {f.source === 'scan' ? ' · scanned' : ''}
                </AppText>
              </View>
              <AppText variant="bodyMedium" color={palette.glow}>{f.calories}</AppText>
              <Pressable onPress={() => removeFood(f.id)} hitSlop={10} style={{ marginLeft: spacing.md }}>
                <Feather name="x" size={18} color={palette.inkFaint} />
              </Pressable>
            </Card>
          ))}
        </View>
      )}

      <AddFoodSheet
        visible={adding}
        onClose={() => setAdding(false)}
        onSave={(entry) => {
          addFood({ ...entry, date: today, source: 'manual' });
          setAdding(false);
        }}
      />
    </Screen>
  );
}

function AddFoodSheet({
  visible,
  onClose,
  onSave,
}: {
  visible: boolean;
  onClose: () => void;
  onSave: (e: { name: string; calories: number; protein: number; carbs: number; fat: number }) => void;
}) {
  const [name, setName] = useState('');
  const [p, setP] = useState('');
  const [c, setC] = useState('');
  const [f, setF] = useState('');
  const [cal, setCal] = useState('');

  const reset = () => {
    setName(''); setP(''); setC(''); setF(''); setCal('');
  };
  const n = (v: string) => Math.max(0, Math.round(Number(v) || 0));
  const derivedCal = macroCalories(n(p), n(c), n(f));
  const finalCal = cal ? n(cal) : derivedCal;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.modalRoot}
      >
        <Pressable style={{ flex: 1 }} onPress={onClose} />
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <AppText variant="heading" style={{ marginBottom: spacing.lg }}>Add a meal</AppText>
          <View style={{ gap: spacing.md }}>
            <TextField label="Name" placeholder="Greek yoghurt bowl" value={name} onChangeText={setName} />
            <View style={styles.macroInputs}>
              <View style={{ flex: 1 }}>
                <TextField label="Protein g" placeholder="0" keyboardType="numeric" value={p} onChangeText={setP} />
              </View>
              <View style={{ flex: 1 }}>
                <TextField label="Carbs g" placeholder="0" keyboardType="numeric" value={c} onChangeText={setC} />
              </View>
              <View style={{ flex: 1 }}>
                <TextField label="Fat g" placeholder="0" keyboardType="numeric" value={f} onChangeText={setF} />
              </View>
            </View>
            <TextField
              label={`Calories (auto: ${derivedCal})`}
              placeholder={String(derivedCal)}
              keyboardType="numeric"
              value={cal}
              onChangeText={setCal}
            />
          </View>
          <Button
            label={`Add · ${finalCal} kcal`}
            disabled={!name.trim()}
            onPress={() => {
              onSave({ name: name.trim(), calories: finalCal, protein: n(p), carbs: n(c), fat: n(f) });
              reset();
            }}
            style={{ marginTop: spacing.xl }}
          />
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  summary: { flexDirection: 'row', alignItems: 'center', gap: spacing.lg },
  summaryMacros: { flex: 1 },
  actions: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.lg },
  empty: { alignItems: 'center', gap: 4, paddingVertical: spacing.xxl },
  entry: { flexDirection: 'row', alignItems: 'center' },
  modalRoot: { flex: 1, backgroundColor: 'rgba(4,7,6,0.6)' },
  sheet: {
    backgroundColor: palette.surface,
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    borderWidth: 1,
    borderColor: palette.hairline,
    padding: spacing.xl,
    paddingBottom: spacing.xxxl,
  },
  handle: {
    alignSelf: 'center',
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: palette.hairlineStrong,
    marginBottom: spacing.lg,
  },
  macroInputs: { flexDirection: 'row', gap: spacing.sm },
});
