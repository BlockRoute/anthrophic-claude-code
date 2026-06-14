import { useRouter } from 'expo-router';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Plant } from '../../components/Plant';
import { AppText, Button, Overline, Screen } from '../../components/ui';
import { palette, spacing } from '../../lib/theme';
import type { PlantState } from '../../lib/plant';

const DEMO: PlantState = {
  stage: 'flourishing',
  stageIndex: 4,
  stageProgress: 0.5,
  growthPoints: 18,
  vitality: 1,
  withering: false,
  streak: 24,
  longestStreak: 24,
  todayRatio: 1,
};

export default function Welcome() {
  const router = useRouter();
  return (
    <Screen scroll={false} contentStyle={styles.wrap}>
      <View style={styles.hero}>
        <Plant plant={DEMO} size={280} />
      </View>

      <View style={styles.copy}>
        <Overline>A living habit tracker</Overline>
        <AppText variant="hero" style={styles.title}>
          Grow something{'\n'}
          <AppText variant="hero" color={palette.glow} style={styles.title}>
            worth tending.
          </AppText>
        </AppText>
        <AppText variant="body" color={palette.inkMuted} style={styles.sub}>
          Track calories, macros, and daily habits. Every day you show up, your
          tree grows. Miss too many, and it withers — so you won't.
        </AppText>
      </View>

      <View style={styles.actions}>
        <Button label="Plant your seed" onPress={() => router.push('/(onboarding)/auth')} />
        <AppText variant="caption" color={palette.inkFaint} style={{ textAlign: 'center', marginTop: spacing.md }}>
          Takes about a minute · No card required
        </AppText>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, justifyContent: 'space-between', paddingHorizontal: spacing.xl, paddingVertical: spacing.xxl },
  hero: { alignItems: 'center', marginTop: spacing.xl },
  copy: { gap: spacing.md },
  title: { fontSize: 38, lineHeight: 42 },
  sub: { marginTop: spacing.xs },
  actions: { marginBottom: spacing.lg },
});
