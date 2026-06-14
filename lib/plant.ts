import type { DayLog, Habit } from './types';
import { dateKey, daysBetween, shiftDate, todayKey } from './date';

export type PlantStage = 'seed' | 'sprout' | 'sapling' | 'young' | 'flourishing' | 'ancient';

export interface PlantState {
  stage: PlantStage;
  stageIndex: number; // 0..5
  /** 0..1 progress toward the next stage. */
  stageProgress: number;
  growthPoints: number;
  /** 0..1 — recent consistency. Low vitality = withering. */
  vitality: number;
  withering: boolean;
  streak: number;
  longestStreak: number;
  todayRatio: number; // 0..1 of core habits done today
}

const STAGES: { stage: PlantStage; at: number }[] = [
  { stage: 'seed', at: 0 },
  { stage: 'sprout', at: 1 },
  { stage: 'sapling', at: 4 },
  { stage: 'young', at: 9 },
  { stage: 'flourishing', at: 18 },
  { stage: 'ancient', at: 32 },
];

export const STAGE_LABEL: Record<PlantStage, string> = {
  seed: 'Seed',
  sprout: 'Sprout',
  sapling: 'Sapling',
  young: 'Young tree',
  flourishing: 'Flourishing',
  ancient: 'Ancient',
};

function ratioForDay(log: DayLog | undefined, coreIds: string[]): number {
  if (!log || coreIds.length === 0) return 0;
  const done = coreIds.filter((id) => log.completedHabits.includes(id)).length;
  return done / coreIds.length;
}

/**
 * Derive the whole plant state from the log history. Pure + idempotent so it
 * can be recomputed any time without drifting.
 */
export function computePlant(
  logs: Record<string, DayLog>,
  habits: Habit[],
  today = todayKey(),
): PlantState {
  const coreIds = habits.filter((h) => h.core).map((h) => h.id);

  // Walk from the earliest log to today accumulating growth points.
  const keys = Object.keys(logs).sort();
  const start = keys.length ? keys[0] : today;
  const span = Math.max(0, daysBetween(start, today));

  let growth = 0;
  for (let i = 0; i <= span; i++) {
    const key = shiftDate(start, i);
    if (key > today) break;
    const ratio = ratioForDay(logs[key], coreIds);
    if (key === today) {
      // Today only ever adds — never penalise an in-progress day.
      growth += ratio;
    } else if (ratio >= 0.999) {
      growth += 1;
    } else if (ratio > 0) {
      growth += ratio * 0.6; // partial credit
    } else {
      growth -= 0.5; // a fully missed day withers the tree
    }
  }
  growth = Math.max(0, growth);

  // Vitality from the last 7 days (excludes today's incomplete state).
  let recentSum = 0;
  for (let i = 1; i <= 7; i++) {
    recentSum += ratioForDay(logs[shiftDate(today, -i)], coreIds);
  }
  const vitality = Math.round((recentSum / 7) * 100) / 100;

  // Streaks (consecutive fully-complete days, today counts if complete).
  let streak = 0;
  for (let i = 0; i < 400; i++) {
    const key = shiftDate(today, -i);
    const ratio = ratioForDay(logs[key], coreIds);
    if (ratio >= 0.999) streak++;
    else if (i === 0) continue; // allow today to still be in progress
    else break;
  }
  let longest = 0;
  let run = 0;
  for (let i = span; i >= 0; i--) {
    const key = shiftDate(start, i);
    if (ratioForDay(logs[key], coreIds) >= 0.999) {
      run++;
      longest = Math.max(longest, run);
    } else run = 0;
  }

  // Resolve stage.
  let stageIndex = 0;
  for (let i = STAGES.length - 1; i >= 0; i--) {
    if (growth >= STAGES[i].at) {
      stageIndex = i;
      break;
    }
  }
  const current = STAGES[stageIndex];
  const next = STAGES[stageIndex + 1];
  const stageProgress = next
    ? Math.min(1, (growth - current.at) / (next.at - current.at))
    : 1;

  return {
    stage: current.stage,
    stageIndex,
    stageProgress,
    growthPoints: Math.round(growth * 10) / 10,
    vitality,
    withering: vitality < 0.4 && stageIndex > 0,
    streak,
    longestStreak: longest,
    todayRatio: ratioForDay(logs[today], coreIds),
  };
}

export function encouragement(plant: PlantState): string {
  if (plant.todayRatio >= 0.999) return 'Fully nurtured today. Beautiful work.';
  if (plant.withering) return 'Your tree is thirsty — a small win revives it.';
  if (plant.streak >= 7) return `${plant.streak} days strong. The roots run deep.`;
  if (plant.stage === 'seed') return 'Complete a habit to break the soil.';
  if (plant.todayRatio > 0) return 'Good start — finish the day to grow.';
  return 'Tend your habits to help it grow.';
}

export { dateKey };
