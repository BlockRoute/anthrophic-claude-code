import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { todayKey } from './date';
import { habitsForGoal } from './habits';
import { DEFAULT_REMINDERS, type ReminderPrefs, syncReminders } from './notifications';
import { computeTargets } from './nutrition';
import type {
  DayLog,
  FoodEntry,
  Habit,
  Profile,
  Targets,
} from './types';

interface LocalUser {
  email: string;
  name: string;
}

interface AppState {
  hydrated: boolean;
  onboarded: boolean;
  localUser: LocalUser | null;
  profile: Profile | null;
  targets: Targets | null;
  habits: Habit[];
  logs: Record<string, DayLog>;
  foods: FoodEntry[];
  reminders: ReminderPrefs;

  // actions
  setLocalUser: (u: LocalUser | null) => void;
  completeOnboarding: (profile: Profile) => void;
  updateProfile: (patch: Partial<Profile>) => void;
  toggleHabit: (habitId: string, date?: string) => void;
  addHabit: (habit: Habit) => void;
  removeHabit: (habitId: string) => void;
  addFood: (entry: Omit<FoodEntry, 'id' | 'createdAt'> & Partial<Pick<FoodEntry, 'id'>>) => void;
  removeFood: (id: string) => void;
  logWeight: (kg: number, date?: string) => void;
  setReminders: (patch: Partial<ReminderPrefs>) => void;
  resetAll: () => void;
  markHydrated: () => void;
}

function ensureDay(logs: Record<string, DayLog>, date: string): DayLog {
  return logs[date] ?? { date, completedHabits: [] };
}

const uid = () =>
  `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      hydrated: false,
      onboarded: false,
      localUser: null,
      profile: null,
      targets: null,
      habits: [],
      logs: {},
      foods: [],
      reminders: DEFAULT_REMINDERS,

      setLocalUser: (u) => set({ localUser: u }),

      completeOnboarding: (profile) => {
        const targets = computeTargets(profile);
        const habits = habitsForGoal(profile.goal);
        const today = todayKey();
        const logs = { ...get().logs };
        if (!logs[today]) {
          logs[today] = { date: today, completedHabits: [], weightKg: profile.weightKg };
        }
        set({ onboarded: true, profile, targets, habits, logs });
        void syncReminders(get().reminders);
      },

      updateProfile: (patch) => {
        const current = get().profile;
        if (!current) return;
        const profile = { ...current, ...patch };
        set({ profile, targets: computeTargets(profile) });
      },

      toggleHabit: (habitId, date = todayKey()) => {
        const logs = { ...get().logs };
        const day = { ...ensureDay(logs, date) };
        const has = day.completedHabits.includes(habitId);
        day.completedHabits = has
          ? day.completedHabits.filter((id) => id !== habitId)
          : [...day.completedHabits, habitId];
        logs[date] = day;
        set({ logs });
      },

      addHabit: (habit) => set({ habits: [...get().habits, habit] }),

      removeHabit: (habitId) =>
        set({ habits: get().habits.filter((h) => h.id !== habitId) }),

      addFood: (entry) =>
        set({
          foods: [
            { ...entry, id: entry.id ?? uid(), createdAt: Date.now() },
            ...get().foods,
          ],
        }),

      removeFood: (id) => set({ foods: get().foods.filter((f) => f.id !== id) }),

      logWeight: (kg, date = todayKey()) => {
        const logs = { ...get().logs };
        const day = { ...ensureDay(logs, date), weightKg: kg };
        logs[date] = day;
        const profile = get().profile;
        set({
          logs,
          profile: profile ? { ...profile, weightKg: kg } : profile,
          targets: profile ? computeTargets({ ...profile, weightKg: kg }) : get().targets,
        });
      },

      setReminders: (patch) => {
        const reminders = { ...get().reminders, ...patch };
        set({ reminders });
        void syncReminders(reminders);
      },

      resetAll: () =>
        set({
          onboarded: false,
          localUser: null,
          profile: null,
          targets: null,
          habits: [],
          logs: {},
          foods: [],
          reminders: DEFAULT_REMINDERS,
        }),

      markHydrated: () => set({ hydrated: true }),
    }),
    {
      name: 'verdant-store-v1',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: ({ hydrated, markHydrated, ...rest }) => rest,
      onRehydrateStorage: () => (state) => {
        state?.markHydrated();
      },
    },
  ),
);

// ---- derived selectors --------------------------------------------------

export const selectFoodsForDate = (date: string) => (s: AppState) =>
  s.foods.filter((f) => f.date === date);

export function dayTotals(foods: FoodEntry[]) {
  return foods.reduce(
    (acc, f) => ({
      calories: acc.calories + f.calories,
      protein: acc.protein + f.protein,
      carbs: acc.carbs + f.carbs,
      fat: acc.fat + f.fat,
    }),
    { calories: 0, protein: 0, carbs: 0, fat: 0 },
  );
}
