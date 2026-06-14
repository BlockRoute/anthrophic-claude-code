import { Feather } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { Tabs } from 'expo-router';
import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AppText } from '../../components/ui';
import { palette, radii, spacing } from '../../lib/theme';

const TABS: { name: string; icon: keyof typeof Feather.glyphMap; label: string }[] = [
  { name: 'index', icon: 'home', label: 'Today' },
  { name: 'nutrition', icon: 'pie-chart', label: 'Food' },
  { name: 'scan', icon: 'maximize', label: 'Scan' },
  { name: 'progress', icon: 'trending-up', label: 'Progress' },
  { name: 'profile', icon: 'user', label: 'You' },
];

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{ headerShown: false }}
      tabBar={(props) => <TabBar {...props} />}
    >
      {TABS.map((t) => (
        <Tabs.Screen key={t.name} name={t.name} />
      ))}
    </Tabs>
  );
}

function TabBar({ state, navigation }: any) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.wrap, { paddingBottom: Math.max(insets.bottom, spacing.md) }]}>
      <View style={styles.bar}>
        {state.routes.map((route: any, index: number) => {
          const tab = TABS.find((t) => t.name === route.name);
          if (!tab) return null;
          const focused = state.index === index;
          const isScan = tab.name === 'scan';

          const onPress = () => {
            void Haptics.selectionAsync();
            const event = navigation.emit({
              type: 'tabPress',
              target: route.key,
              canPreventDefault: true,
            });
            if (!focused && !event.defaultPrevented) navigation.navigate(route.name);
          };

          if (isScan) {
            return (
              <Pressable key={route.key} onPress={onPress} style={styles.scanBtn}>
                <View style={styles.scanInner}>
                  <Feather name="maximize" size={24} color={palette.void} />
                </View>
              </Pressable>
            );
          }

          return (
            <Pressable key={route.key} onPress={onPress} style={styles.tab}>
              <Feather
                name={tab.icon}
                size={22}
                color={focused ? palette.glow : palette.inkFaint}
              />
              <AppText
                variant="caption"
                color={focused ? palette.glow : palette.inkFaint}
                style={{ fontSize: 10 }}
              >
                {tab.label}
              </AppText>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: spacing.lg,
    backgroundColor: 'transparent',
  },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(16,22,20,0.94)',
    borderRadius: radii.xl,
    borderWidth: 1,
    borderColor: palette.hairline,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
  },
  tab: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 3, paddingVertical: 4 },
  scanBtn: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scanInner: {
    width: 54,
    height: 54,
    borderRadius: radii.lg,
    backgroundColor: palette.glow,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: -22,
    shadowColor: palette.glow,
    shadowOpacity: 0.5,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
});
