import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  type PressableProps,
  ScrollView,
  type StyleProp,
  StyleSheet,
  Text,
  type TextProps,
  type TextStyle,
  View,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { palette, radii, spacing, type as typeScale } from '../lib/theme';

type Variant = keyof typeof typeScale;

export function AppText({
  variant = 'body',
  color = palette.ink,
  style,
  children,
  ...rest
}: TextProps & { variant?: Variant; color?: string }) {
  return (
    <Text {...rest} style={[typeScale[variant] as TextStyle, { color }, style]}>
      {children}
    </Text>
  );
}

export function Overline({ children, color = palette.glowSoft, style }: {
  children: React.ReactNode;
  color?: string;
  style?: StyleProp<TextStyle>;
}) {
  return (
    <Text style={[typeScale.overline, { color }, style]}>{children}</Text>
  );
}

export function Screen({
  children,
  scroll = true,
  edges = ['top'],
  contentStyle,
}: {
  children: React.ReactNode;
  scroll?: boolean;
  edges?: ('top' | 'bottom' | 'left' | 'right')[];
  contentStyle?: StyleProp<ViewStyle>;
}) {
  const inner = scroll ? (
    <ScrollView
      contentContainerStyle={[styles.scrollContent, contentStyle]}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
    >
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.flex, contentStyle]}>{children}</View>
  );

  return (
    <View style={styles.flex}>
      <LinearGradient
        colors={[palette.base, '#0C1512']}
        style={StyleSheet.absoluteFill}
        start={{ x: 0, y: 0 }}
        end={{ x: 0.6, y: 1 }}
      />
      <SafeAreaView style={styles.flex} edges={edges}>
        {inner}
      </SafeAreaView>
    </View>
  );
}

export function Card({
  children,
  style,
  raised = false,
  padding = spacing.lg,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  raised?: boolean;
  padding?: number;
}) {
  return (
    <View
      style={[
        styles.card,
        { backgroundColor: raised ? palette.surfaceRaised : palette.surface, padding },
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function Button({
  label,
  onPress,
  variant = 'solid',
  loading = false,
  disabled = false,
  icon,
  style,
}: {
  label: string;
  onPress?: () => void;
  variant?: 'solid' | 'ghost' | 'outline';
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const isSolid = variant === 'solid';
  const content = (
    <View style={styles.btnInner}>
      {loading ? (
        <ActivityIndicator color={isSolid ? palette.void : palette.glow} />
      ) : (
        <>
          {icon}
          <Text
            style={[
              typeScale.label,
              {
                color: isSolid ? palette.void : palette.ink,
                fontSize: 15,
                letterSpacing: 0.2,
              },
            ]}
          >
            {label}
          </Text>
        </>
      )}
    </View>
  );

  const handle = () => {
    if (disabled || loading) return;
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onPress?.();
  };

  if (isSolid) {
    return (
      <Pressable onPress={handle} disabled={disabled || loading} style={style}>
        {({ pressed }) => (
          <LinearGradient
            colors={['#74F0BA', palette.glowSoft]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={[
              styles.btn,
              { opacity: disabled ? 0.4 : pressed ? 0.86 : 1 },
            ]}
          >
            {content}
          </LinearGradient>
        )}
      </Pressable>
    );
  }

  return (
    <Pressable
      onPress={handle}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.btn,
        variant === 'outline' ? styles.btnOutline : styles.btnGhost,
        { opacity: disabled ? 0.4 : pressed ? 0.7 : 1 },
        style,
      ]}
    >
      {content}
    </Pressable>
  );
}

export function Pill({
  label,
  tone = 'neutral',
}: {
  label: string;
  tone?: 'neutral' | 'good' | 'warn' | 'bad';
}) {
  const map = {
    neutral: { bg: palette.glowWash, fg: palette.glow },
    good: { bg: 'rgba(111,230,160,0.14)', fg: palette.protein },
    warn: { bg: 'rgba(232,178,122,0.14)', fg: palette.warn },
    bad: { bg: 'rgba(226,115,94,0.14)', fg: palette.danger },
  }[tone];
  return (
    <View style={[styles.pill, { backgroundColor: map.bg }]}>
      <Text style={[typeScale.caption, { color: map.fg }]}>{label}</Text>
    </View>
  );
}

export function Divider({ style }: { style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.divider, style]} />;
}

export function PressFx({ children, onPress, style, disabled }: PressableProps & {
  children: React.ReactNode;
}) {
  return (
    <Pressable
      onPress={(e) => {
        if (disabled) return;
        void Haptics.selectionAsync();
        onPress?.(e);
      }}
      style={({ pressed }) => [{ opacity: pressed ? 0.6 : 1 }, style as StyleProp<ViewStyle>]}
    >
      {children}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  scrollContent: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xxxl * 2,
  },
  card: {
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: palette.hairline,
  },
  btn: {
    height: 54,
    borderRadius: radii.pill,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
  },
  btnInner: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  btnOutline: { borderWidth: 1, borderColor: palette.hairlineStrong, backgroundColor: 'transparent' },
  btnGhost: { backgroundColor: palette.surfaceRaised },
  pill: {
    paddingHorizontal: spacing.md,
    paddingVertical: 5,
    borderRadius: radii.pill,
    alignSelf: 'flex-start',
  },
  divider: { height: 1, backgroundColor: palette.hairline, marginVertical: spacing.lg },
});
