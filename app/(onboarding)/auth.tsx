import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, View } from 'react-native';
import { AppText, Button, Overline, Screen } from '../../components/ui';
import { SegmentedControl, StepDots, TextField } from '../../components/inputs';
import { signIn, signUp } from '../../lib/auth';
import { useOnboarding } from '../../lib/onboarding';
import { useStore } from '../../lib/store';
import { isCloudEnabled } from '../../lib/supabase';
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

  const submit = async () => {
    setError(null);
    if (!email.includes('@') || password.length < 6) {
      setError('Enter a valid email and a 6+ character password.');
      return;
    }
    setBusy(true);
    const res = mode === 'signup' ? await signUp(email, password) : await signIn(email, password);
    setBusy(false);
    if (!res.ok) {
      setError(res.error ?? 'Something went wrong.');
      return;
    }
    setLocalUser({ email, name: name || email.split('@')[0] });
    setDraft({ name: name || email.split('@')[0] });
    router.push('/(onboarding)/profile');
  };

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
});
