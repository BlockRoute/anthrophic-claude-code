import { create } from 'zustand';
import type { ActivityLevel, GoalId, Sex } from './types';

interface OnboardingDraft {
  name: string;
  sex: Sex;
  age: number;
  heightCm: number;
  weightKg: number;
  activity: ActivityLevel;
  goal: GoalId | null;
  units: 'metric' | 'imperial';
  set: (patch: Partial<Omit<OnboardingDraft, 'set'>>) => void;
}

export const useOnboarding = create<OnboardingDraft>((set) => ({
  name: '',
  sex: 'female',
  age: 28,
  heightCm: 168,
  weightKg: 68,
  activity: 'moderate',
  goal: null,
  units: 'metric',
  set: (patch) => set(patch),
}));
