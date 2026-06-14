import {
  Fraunces_400Regular,
  Fraunces_400Regular_Italic,
  Fraunces_600SemiBold,
  useFonts as useFraunces,
} from '@expo-google-fonts/fraunces';
import {
  HankenGrotesk_400Regular,
  HankenGrotesk_500Medium,
  HankenGrotesk_600SemiBold,
  HankenGrotesk_700Bold,
  useFonts as useHanken,
} from '@expo-google-fonts/hanken-grotesk';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { palette } from '../lib/theme';
import { useStore } from '../lib/store';
import { currentUserId } from '../lib/auth';
import { isCloudEnabled } from '../lib/supabase';
import { pullSnapshot, startAutoSync } from '../lib/sync';

SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const [fraunces] = useFraunces({
    Fraunces_400Regular,
    Fraunces_400Regular_Italic,
    Fraunces_600SemiBold,
  });
  const [hanken] = useHanken({
    HankenGrotesk_400Regular,
    HankenGrotesk_500Medium,
    HankenGrotesk_600SemiBold,
    HankenGrotesk_700Bold,
  });
  const hydrated = useStore((s) => s.hydrated);
  const ready = fraunces && hanken && hydrated;

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  // Restore a cloud session on launch and resume syncing.
  useEffect(() => {
    if (!ready || !isCloudEnabled) return;
    let stop: (() => void) | undefined;
    currentUserId().then((uid) => {
      if (!uid) return;
      pullSnapshot(uid).finally(() => {
        stop = startAutoSync(uid);
      });
    });
    return () => stop?.();
  }, [ready]);

  if (!ready) return <View style={{ flex: 1, backgroundColor: palette.base }} />;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: palette.base },
            animation: 'fade',
          }}
        >
          <Stack.Screen name="index" />
          <Stack.Screen name="(onboarding)" />
          <Stack.Screen name="(tabs)" />
        </Stack>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
