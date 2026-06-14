import { Feather } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, View } from 'react-native';
import { AppText, Button, Card, Overline, Screen } from '../../components/ui';
import { SegmentedControl, StepDots, TextField } from '../../components/inputs';
import { currentUserId, signIn, signUp } from '../../lib/auth';
import { useOnboarding } from '../../lib/onboarding';
import { useStore } from '../../lib/store';
import { isCloudEnabled } from '../../lib/supabase';
import { pullSnapshot, startAutoSync } from '../../lib/sync';
import { palette, spacing } from '../../lib/theme';

export default function Auth() {
  const router = useRouter();
  const setDraft = useOnboarding((s) => s.set);
  const setLocalUser = useStore((s) => s.setLocalUser);

  const [mode, setMode] = useState<'signup' | 'signin'>('signup');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [awaitingEmail, setAwaitingEmail] = useState<string | null>(null);

  // After a session exists, hydrate from cloud and route onward.
  const proceed = async () => {
    setLocalUser({ email, name: name || email.split('@')[0] });
    setDraft({ name: name || email.split('@')[0] });
    if (isCloudEnabled) {
      const uid = await currentUserId();
      if (uid) {
        await pullSnapshot(uid);
        startAutoSync(uid);
        if (useStore.getState().onboarded) {
          router.replace('/(tabs)');
          return;
        }
      }
    }
    router.push('/(onboarding)/profile');
  };

  const submit = async () => {
    setError(null);
    if (!email.includes('@') || password.length < 6) {
      setError('Enter a valid email and a 6+ character password.');
      return;
    }
    setBusy(true);
    const res = mode === 'signup' ? await signUp(email, password) : await signIn(email, password);
    if (!res.ok) {
      setBusy(false);
      setError(res.error ?? 'Something went wrong.');
      return;
    }
    setBusy(false);

    // Cloud signup that needs email confirmation: show the "check inbox" state.
    // Tapping the email link reopens the app at /auth-callback and signs in.
    if (mode === 'signup' && res.needsConfirmation && isCloudEnabled) {
      setDraft({ name: name || email.split('@')[0] });
      setAwaitingEmail(email);
      return;
    }
    await proceed();
  };

  if (awaitingEmail) {
    return (
      <Screen edges={['top', 'bottom']} contentStyle={styles.confirmWrap}>
        <View style={styles.confirmIcon}>
          <Feather name="mail" size={28} color={palette.glow} />
        </View>
        <Overline color={palette.glowSoft}>Almost there</Overline>
        <AppText variant="title" style={{ textAlign: 'center', marginTop: spacing.sm }}>
          Confirm your email
        </AppText>
        <AppText variant="body" color={palette.inkMuted} style={styles.confirmBody}>
          We sent a link to{'\n'}
          <AppText variant="bodyMedium" color={palette.ink}>{awaitingEmail}</AppText>
          {'\n'}Tap it and you’ll land right back here, signed in.
        </AppText>
        <Card style={styles.tipCard} padding={spacing.md}>
          <Feather name="info" size={15} color={palette.inkMuted} />
          <AppText variant="caption" color={palette.inkMuted} style={{ flex: 1 }}>
            No email after a minute? Check spam, or go back and try a different address.
          </AppText>
        </Card>
        <View style={{ flex: 1 }} />
        <Button
          label="Use a different email"
          variant="ghost"
          onPress={() => {
            setAwaitingEmail(null);
            setError(null);
          }}
        />
      </Screen>
    );
  }

  return (
    <Screen edges={['top', 'bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <StepDots total={4} index={0} />
        <Overline style={{ marginTop: spacing.xl }}>
          {mode === 'signup' ? 'Create your account' : 'Welcome back'}
        </Overline>
        <AppText variant="title" style={{ marginTop: spacing.sm }}>
          {mode === 'signup' ? 'Let’s get you set up' : 'Sign back in'}
        </AppText>

        <View style={{ marginTop: spacing.xl, marginBottom: spacing.xl }}>
          <SegmentedControl
            value={mode}
            onChange={setMode}
            options={[
              { value: 'signup', label: 'Sign up' },
              { value: 'signin', label: 'Sign in' },
            ]}
          />
        </View>

        <View style={{ gap: spacing.lg }}>
          {mode === 'signup' && (
            <TextField
              label="First name"
              placeholder="Dylan"
              value={name}
              onChangeText={setName}
              autoCapitalize="words"
            />
          )}
          <TextField
            label="Email"
            placeholder="you@example.com"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            autoComplete="email"
          />
          <TextField
            label="Password"
            placeholder="••••••••"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />
        </View>

        {error && (
          <AppText variant="caption" color={palette.danger} style={{ marginTop: spacing.md }}>
            {error}
          </AppText>
        )}

        {!isCloudEnabled && (
          <AppText variant="caption" color={palette.inkFaint} style={styles.localNote}>
            Running in local mode — your data stays on this device. Add Supabase
            keys to sync across devices.
          </AppText>
        )}

        <Button
          label={mode === 'signup' ? 'Continue' : 'Sign in'}
          onPress={submit}
          loading={busy}
          style={{ marginTop: spacing.xl }}
        />
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  localNote: {
    marginTop: spacing.lg,
    lineHeight: 17,
  },
  confirmWrap: { flex: 1, alignItems: 'center', paddingTop: spacing.xxxl },
  confirmIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: palette.glowDeep,
    borderWidth: 1,
    borderColor: 'rgba(91,231,168,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  confirmBody: { textAlign: 'center', marginTop: spacing.md, lineHeight: 22 },
  tipCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.xl,
  },
});
