import { Feather } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { AppText, Button, Overline, Screen } from '../components/ui';
import { exchangeCode } from '../lib/auth';
import { currentUserId } from '../lib/auth';
import { useStore } from '../lib/store';
import { pullSnapshot, startAutoSync } from '../lib/sync';
import { palette, spacing } from '../lib/theme';

/**
 * Landing route for the Supabase email-confirmation deep link
 * (verdant://auth-callback?code=...). Exchanges the code for a session,
 * resumes cloud sync, then routes the user onward.
 */
export default function AuthCallback() {
  const router = useRouter();
  const params = useLocalSearchParams<{ code?: string; error_description?: string }>();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (params.error_description) {
        setError(String(params.error_description));
        return;
      }
      const code = typeof params.code === 'string' ? params.code : undefined;
      if (!code) {
        setError('This confirmation link is missing its code. Try signing in.');
        return;
      }

      const res = await exchangeCode(code);
      if (cancelled) return;
      if (!res.ok) {
        setError(res.error ?? 'We could not confirm this link. Try signing in.');
        return;
      }

      const uid = await currentUserId();
      if (uid) {
        await pullSnapshot(uid);
        startAutoSync(uid);
      }
      if (cancelled) return;

      router.replace(useStore.getState().onboarded ? '/(tabs)' : '/(onboarding)/profile');
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [params.code, params.error_description, router]);

  return (
    <Screen scroll={false} contentStyle={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.xl }}>
      {error ? (
        <View style={{ alignItems: 'center', gap: spacing.md }}>
          <Feather name="alert-circle" size={28} color={palette.warn} />
          <Overline color={palette.inkMuted}>Couldn’t confirm</Overline>
          <AppText variant="body" color={palette.inkMuted} style={{ textAlign: 'center' }}>
            {error}
          </AppText>
          <Button
            label="Back to sign in"
            variant="ghost"
            onPress={() => router.replace('/(onboarding)/auth')}
            style={{ marginTop: spacing.md }}
          />
        </View>
      ) : (
        <View style={{ alignItems: 'center', gap: spacing.lg }}>
          <ActivityIndicator color={palette.glow} />
          <AppText variant="heading">Confirming your email…</AppText>
          <AppText variant="caption" color={palette.inkMuted}>Planting your account</AppText>
        </View>
      )}
    </Screen>
  );
}
