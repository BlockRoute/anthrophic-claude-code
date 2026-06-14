/**
 * Verdant design system.
 *
 * Direction: "deep calm" — a near-black canvas tinted with green, muted
 * bioluminescent accents, and soft glass surfaces. Deliberately avoids the
 * default RN look (pure #FFF text on #000, Inter/Roboto, candy gradients).
 *
 * Type pairing: Fraunces (an optical serif with personality) for display,
 * Hanken Grotesk for UI text. Neither is a "vibe-coded" default.
 */

export const palette = {
  // Canvas — black with a faint forest tint, layered for depth.
  void: '#070A09',
  base: '#0A0E0D',
  surface: '#101614',
  surfaceRaised: '#16201D',
  hairline: 'rgba(170, 220, 200, 0.08)',
  hairlineStrong: 'rgba(170, 220, 200, 0.16)',

  // Text.
  ink: '#EAF2EE',
  inkMuted: '#9FB1A9',
  inkFaint: '#5E6F69',

  // Primary accent — muted bioluminescent green (the "living" colour).
  glow: '#5BE7A8',
  glowSoft: '#3DBF8A',
  glowDeep: '#0F2A21',
  glowWash: 'rgba(91, 231, 168, 0.12)',

  // Macro / data hues, kept desaturated to sit in the dark.
  protein: '#6FE6A0',
  carbs: '#7CA8FF',
  fat: '#E8B27A',

  // States.
  wither: '#C2785A', // warm rust for "withering" / behind
  warn: '#E8B27A',
  danger: '#E2735E',
  gold: '#E9C97A',
} as const;

export const gradients = {
  // Used sparingly, never as a flat "pretty" backdrop.
  canopy: ['#0A0E0D', '#0E1A15'] as const,
  glow: ['#5BE7A8', '#3DBF8A'] as const,
  dusk: ['#10211B', '#0A0E0D'] as const,
} as const;

export const radii = {
  sm: 10,
  md: 16,
  lg: 22,
  xl: 30,
  pill: 999,
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

export const fonts = {
  display: 'Fraunces_600SemiBold',
  displayLight: 'Fraunces_400Regular',
  serifItalic: 'Fraunces_400Regular_Italic',
  body: 'HankenGrotesk_400Regular',
  medium: 'HankenGrotesk_500Medium',
  semibold: 'HankenGrotesk_600SemiBold',
  bold: 'HankenGrotesk_700Bold',
} as const;

export const type = {
  hero: { fontFamily: fonts.display, fontSize: 40, lineHeight: 44, letterSpacing: -0.5 },
  title: { fontFamily: fonts.display, fontSize: 28, lineHeight: 32, letterSpacing: -0.3 },
  heading: { fontFamily: fonts.semibold, fontSize: 19, lineHeight: 24 },
  body: { fontFamily: fonts.body, fontSize: 15, lineHeight: 22 },
  bodyMedium: { fontFamily: fonts.medium, fontSize: 15, lineHeight: 22 },
  label: { fontFamily: fonts.semibold, fontSize: 13, lineHeight: 16, letterSpacing: 0.2 },
  caption: { fontFamily: fonts.medium, fontSize: 12, lineHeight: 16, letterSpacing: 0.3 },
  // ALL-CAPS micro labels — the one "editorial" flourish.
  overline: {
    fontFamily: fonts.semibold,
    fontSize: 11,
    lineHeight: 14,
    letterSpacing: 1.6,
    textTransform: 'uppercase' as const,
  },
  numeral: { fontFamily: fonts.display, fontSize: 34, lineHeight: 36, letterSpacing: -0.5 },
} as const;

export const theme = { palette, gradients, radii, spacing, fonts, type } as const;
export type Theme = typeof theme;
