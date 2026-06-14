import { Feather } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import React, { useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { AppText, Overline } from './ui';
import { palette, radii, spacing } from '../lib/theme';

export interface DropdownOption<T extends string> {
  value: T;
  label: string;
  hint?: string;
}

export function Dropdown<T extends string>({
  label,
  placeholder = 'Select…',
  options,
  value,
  onChange,
}: {
  label?: string;
  placeholder?: string;
  options: DropdownOption<T>[];
  value: T | null;
  onChange: (v: T) => void;
}) {
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.value === value) ?? null;

  return (
    <View style={{ gap: spacing.sm }}>
      {label && <Overline color={palette.inkMuted}>{label}</Overline>}
      <Pressable
        onPress={() => {
          void Haptics.selectionAsync();
          setOpen(true);
        }}
        style={styles.field}
      >
        <AppText variant="bodyMedium" color={selected ? palette.ink : palette.inkFaint}>
          {selected ? selected.label : placeholder}
        </AppText>
        <Feather name="chevron-down" size={20} color={palette.inkMuted} />
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <View style={styles.sheet}>
            <View style={styles.handle} />
            <AppText variant="heading" style={{ marginBottom: spacing.md }}>
              {label ?? 'Select an option'}
            </AppText>
            <ScrollView style={{ maxHeight: 420 }} showsVerticalScrollIndicator={false}>
              {options.map((opt) => {
                const active = opt.value === value;
                return (
                  <Pressable
                    key={opt.value}
                    onPress={() => {
                      void Haptics.selectionAsync();
                      onChange(opt.value);
                      setOpen(false);
                    }}
                    style={[
                      styles.row,
                      {
                        backgroundColor: active ? palette.glowDeep : 'transparent',
                        borderColor: active ? 'rgba(91,231,168,0.4)' : palette.hairline,
                      },
                    ]}
                  >
                    <View style={{ flex: 1 }}>
                      <AppText variant="bodyMedium" color={active ? palette.glow : palette.ink}>
                        {opt.label}
                      </AppText>
                      {opt.hint && (
                        <AppText variant="caption" color={palette.inkMuted}>{opt.hint}</AppText>
                      )}
                    </View>
                    {active && <Feather name="check" size={18} color={palette.glow} />}
                  </Pressable>
                );
              })}
            </ScrollView>
          </View>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: palette.surface,
    borderWidth: 1,
    borderColor: palette.hairline,
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
    height: 54,
  },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(4,7,6,0.7)',
    justifyContent: 'flex-end',
  },
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
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    borderRadius: radii.md,
    borderWidth: 1,
    marginBottom: spacing.sm,
  },
});
