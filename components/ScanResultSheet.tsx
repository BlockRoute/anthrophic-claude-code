import { Feather } from '@expo/vector-icons';
import { Image } from 'react-native';
import React, { useEffect, useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { ScoreDial, VERDICT_COLOR, VERDICT_LABEL } from './ScoreDial';
import { AppText, Button, Card, Overline, Pill } from './ui';
import { fetchAlternatives } from '../lib/openfoodfacts';
import { todayKey } from '../lib/date';
import { useStore } from '../lib/store';
import { palette, radii, spacing } from '../lib/theme';
import type { ScannedProduct } from '../lib/types';

export function ScanResultSheet({
  product,
  onClose,
}: {
  product: ScannedProduct;
  onClose: () => void;
}) {
  const addFood = useStore((s) => s.addFood);
  const [alts, setAlts] = useState<ScannedProduct[]>([]);
  const [added, setAdded] = useState(false);

  const macros = product.perServing ?? product.per100g;
  const macroBasis = product.perServing ? (product.serving ?? 'per serving') : 'per 100g';

  useEffect(() => {
    let active = true;
    fetchAlternatives(product).then((a) => active && setAlts(a));
    return () => {
      active = false;
    };
  }, [product]);

  const add = () => {
    addFood({
      date: todayKey(),
      name: product.name,
      brand: product.brand,
      serving: macroBasis,
      calories: macros.calories,
      protein: macros.protein,
      carbs: macros.carbs,
      fat: macros.fat,
      source: 'scan',
      barcode: product.barcode,
      healthScore: product.healthScore,
    });
    setAdded(true);
    setTimeout(onClose, 650);
  };

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.root}>
        <Pressable style={{ flex: 1 }} onPress={onClose} />
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: spacing.xl }}>
            {/* Header */}
            <View style={styles.head}>
              {product.imageUrl ? (
                <Image source={{ uri: product.imageUrl }} style={styles.thumb} />
              ) : (
                <View style={[styles.thumb, styles.thumbFallback]}>
                  <Feather name="package" size={24} color={palette.inkFaint} />
                </View>
              )}
              <View style={{ flex: 1 }}>
                {product.brand && <Overline color={palette.inkMuted}>{product.brand}</Overline>}
                <AppText variant="heading" style={{ marginTop: 2 }}>{product.name}</AppText>
                <View style={{ flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm }}>
                  <Pill
                    label={VERDICT_LABEL[product.verdict]}
                    tone={
                      product.verdict === 'excellent' || product.verdict === 'good'
                        ? 'good'
                        : product.verdict === 'fair'
                        ? 'warn'
                        : 'bad'
                    }
                  />
                  {product.nutriScore && <Pill label={`Nutri-Score ${product.nutriScore}`} />}
                </View>
              </View>
            </View>

            {/* Score + macros */}
            <Card raised style={styles.scoreCard}>
              <ScoreDial score={product.healthScore} verdict={product.verdict} />
              <View style={styles.macroGrid}>
                <Macro label="kcal" value={macros.calories} color={palette.glow} />
                <Macro label="Protein" value={macros.protein} color={palette.protein} unit="g" />
                <Macro label="Carbs" value={macros.carbs} color={palette.carbs} unit="g" />
                <Macro label="Fat" value={macros.fat} color={palette.fat} unit="g" />
                <AppText variant="caption" color={palette.inkFaint} style={{ width: '100%', marginTop: 2 }}>
                  {macroBasis}
                </AppText>
              </View>
            </Card>

            {/* Why */}
            {(product.positives.length > 0 || product.negatives.length > 0) && (
              <View style={styles.reasons}>
                {product.positives.map((p) => (
                  <Reason key={p} text={p} good />
                ))}
                {product.negatives.map((n) => (
                  <Reason key={n} text={n} good={false} />
                ))}
              </View>
            )}

            {/* Alternatives */}
            {alts.length > 0 && (
              <View style={{ marginTop: spacing.xl }}>
                <Overline color={palette.glowSoft}>Better picks</Overline>
                <View style={{ gap: spacing.sm, marginTop: spacing.md }}>
                  {alts.map((a) => (
                    <Card key={a.barcode + a.name} style={styles.alt} padding={spacing.md}>
                      <View
                        style={[
                          styles.altScore,
                          { borderColor: VERDICT_COLOR[a.verdict] },
                        ]}
                      >
                        <AppText variant="label" color={VERDICT_COLOR[a.verdict]}>{a.healthScore}</AppText>
                      </View>
                      <View style={{ flex: 1 }}>
                        <AppText variant="bodyMedium" numberOfLines={1}>{a.name}</AppText>
                        {a.brand && (
                          <AppText variant="caption" color={palette.inkMuted}>{a.brand}</AppText>
                        )}
                      </View>
                      <Feather name="arrow-up-right" size={18} color={palette.glowSoft} />
                    </Card>
                  ))}
                </View>
              </View>
            )}

            <Button
              label={added ? 'Added to today ✓' : 'Add to today’s log'}
              onPress={add}
              disabled={added}
              style={{ marginTop: spacing.xl }}
            />
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

function Macro({ label, value, color, unit = '' }: { label: string; value: number; color: string; unit?: string }) {
  return (
    <View style={styles.macro}>
      <AppText variant="numeral" style={{ fontSize: 22 }} color={color}>
        {value}
        <AppText variant="caption" color={palette.inkMuted}>{unit}</AppText>
      </AppText>
      <Overline color={palette.inkFaint}>{label}</Overline>
    </View>
  );
}

function Reason({ text, good }: { text: string; good: boolean }) {
  return (
    <View style={styles.reason}>
      <Feather
        name={good ? 'check-circle' : 'alert-triangle'}
        size={16}
        color={good ? palette.protein : palette.warn}
      />
      <AppText variant="bodyMedium" color={palette.inkMuted}>{text}</AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: 'rgba(4,7,6,0.7)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: palette.base,
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    borderWidth: 1,
    borderColor: palette.hairline,
    padding: spacing.xl,
    maxHeight: '88%',
  },
  handle: {
    alignSelf: 'center',
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: palette.hairlineStrong,
    marginBottom: spacing.lg,
  },
  head: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  thumb: { width: 64, height: 64, borderRadius: radii.md, backgroundColor: palette.surface },
  thumbFallback: { alignItems: 'center', justifyContent: 'center' },
  scoreCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
    marginTop: spacing.lg,
  },
  macroGrid: { flex: 1, flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  macro: { width: '40%' },
  reasons: { marginTop: spacing.lg, gap: spacing.sm },
  reason: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  alt: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  altScore: {
    width: 42,
    height: 42,
    borderRadius: radii.pill,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
