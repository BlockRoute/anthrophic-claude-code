import type { GoalId, Habit } from './types';

/** Baseline habits everyone starts with. `core` habits feed the plant. */
export const DEFAULT_HABITS: Habit[] = [
  { id: 'log_meals', label: 'Log every meal', icon: 'book-open', core: true },
  { id: 'protein', label: 'Hit protein target', icon: 'zap', core: true },
  { id: 'move', label: 'Move or train', icon: 'activity', core: true },
  { id: 'hydrate', label: 'Drink 2L water', icon: 'droplet', core: true },
  { id: 'steps', label: '8k steps', icon: 'trending-up', core: false },
  { id: 'sleep', label: 'Sleep 7+ hours', icon: 'moon', core: false },
];

/** A couple of goal-flavoured habits layered on during onboarding. */
const GOAL_HABITS: Partial<Record<GoalId, Habit[]>> = {
  marathon: [{ id: 'easy_run', label: 'Easy zone-2 run', icon: 'wind', core: false }],
  ironman: [
    { id: 'brick', label: 'Brick / swim session', icon: 'wind', core: false },
    { id: 'mobility', label: 'Mobility 10 min', icon: 'feather', core: false },
  ],
  build_muscle: [{ id: 'progressive', label: 'Log lifts (progressive)', icon: 'bar-chart-2', core: false }],
  improve_endurance: [{ id: 'cardio', label: 'Cardio base session', icon: 'wind', core: false }],
};

export function habitsForGoal(goal: GoalId): Habit[] {
  const extra = GOAL_HABITS[goal] ?? [];
  return [...DEFAULT_HABITS, ...extra];
}
