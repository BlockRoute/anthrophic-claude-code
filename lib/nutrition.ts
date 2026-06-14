import type {
  ActivityLevel,
  Goal,
  GoalId,
  Profile,
  Sex,
  Targets,
} from './types';

export const GOALS: Goal[] = [
  {
    id: 'lose_weight',
    label: 'Lose weight',
    blurb: 'Steady fat loss in a moderate deficit',
    calorieDelta: -450,
    macroSplit: [0.35, 0.35, 0.3],
    proteinPerKg: 2.0,
  },
  {
    id: 'build_muscle',
    label: 'Build muscle',
    blurb: 'Lean surplus with high protein',
    calorieDelta: 250,
    macroSplit: [0.3, 0.45, 0.25],
    proteinPerKg: 2.0,
  },
  {
    id: 'improve_endurance',
    label: 'Improve endurance',
    blurb: 'Fuel longer, more frequent sessions',
    calorieDelta: 0,
    macroSplit: [0.25, 0.55, 0.2],
    proteinPerKg: 1.6,
  },
  {
    id: 'marathon',
    label: 'Train for a marathon',
    blurb: 'Carb-forward fuelling for high mileage',
    calorieDelta: 150,
    macroSplit: [0.2, 0.6, 0.2],
    proteinPerKg: 1.6,
  },
  {
    id: 'ironman',
    label: 'Train for an Ironman',
    blurb: 'Big aerobic load across three disciplines',
    calorieDelta: 300,
    macroSplit: [0.22, 0.58, 0.2],
    proteinPerKg: 1.8,
  },
  {
    id: 'beach_body',
    label: 'Beach body',
    blurb: 'Recomp — hold muscle, drop a little fat',
    calorieDelta: -250,
    macroSplit: [0.35, 0.35, 0.3],
    proteinPerKg: 2.0,
  },
  {
    id: 'maintain',
    label: 'Maintain & feel good',
    blurb: 'Balanced intake at maintenance',
    calorieDelta: 0,
    macroSplit: [0.3, 0.4, 0.3],
    proteinPerKg: 1.6,
  },
];

export function goalById(id: GoalId): Goal {
  return GOALS.find((g) => g.id === id) ?? GOALS[GOALS.length - 1];
}

const ACTIVITY_MULTIPLIER: Record<ActivityLevel, number> = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
  athlete: 1.9,
};

export const ACTIVITY_OPTIONS: { id: ActivityLevel; label: string; hint: string }[] = [
  { id: 'sedentary', label: 'Mostly still', hint: 'Desk job, little exercise' },
  { id: 'light', label: 'Lightly active', hint: 'Light movement 1–3 days/wk' },
  { id: 'moderate', label: 'Active', hint: 'Training 3–5 days/wk' },
  { id: 'active', label: 'Very active', hint: 'Hard training 6–7 days/wk' },
  { id: 'athlete', label: 'Athlete', hint: 'Twice-a-day or physical job' },
];

/** Mifflin–St Jeor basal metabolic rate. */
export function bmr(sex: Sex, weightKg: number, heightCm: number, age: number): number {
  const base = 10 * weightKg + 6.25 * heightCm - 5 * age;
  return Math.round(sex === 'male' ? base + 5 : base - 161);
}

export function computeTargets(profile: Profile): Targets {
  const goal = goalById(profile.goal);
  const restingRate = bmr(profile.sex, profile.weightKg, profile.heightCm, profile.age);
  const tdee = Math.round(restingRate * ACTIVITY_MULTIPLIER[profile.activity]);
  const calories = Math.max(1200, tdee + goal.calorieDelta);

  // Protein: take the larger of the per-kg target and the split.
  const proteinFromKg = goal.proteinPerKg * profile.weightKg;
  const proteinFromSplit = (calories * goal.macroSplit[0]) / 4;
  const protein = Math.round(Math.max(proteinFromKg, proteinFromSplit));

  const proteinCals = protein * 4;
  const remaining = Math.max(0, calories - proteinCals);
  // Distribute the rest across carbs/fat by their relative split weight.
  const carbWeight = goal.macroSplit[1];
  const fatWeight = goal.macroSplit[2];
  const carbShare = carbWeight / (carbWeight + fatWeight);

  const carbs = Math.round((remaining * carbShare) / 4);
  const fat = Math.round((remaining * (1 - carbShare)) / 9);

  return { bmr: restingRate, tdee, calories, protein, carbs, fat };
}

// ---- unit helpers -------------------------------------------------------

export const cmToFtIn = (cm: number) => {
  const totalInches = cm / 2.54;
  const ft = Math.floor(totalInches / 12);
  const inch = Math.round(totalInches - ft * 12);
  return { ft, inch };
};

export const ftInToCm = (ft: number, inch: number) =>
  Math.round((ft * 12 + inch) * 2.54);

export const kgToLb = (kg: number) => Math.round(kg * 2.20462 * 10) / 10;
export const lbToKg = (lb: number) => Math.round((lb / 2.20462) * 10) / 10;

export const macroCalories = (p: number, c: number, f: number) =>
  Math.round(p * 4 + c * 4 + f * 9);
