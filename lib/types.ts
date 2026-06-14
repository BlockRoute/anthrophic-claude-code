export type Sex = 'male' | 'female';

export type ActivityLevel =
  | 'sedentary'
  | 'light'
  | 'moderate'
  | 'active'
  | 'athlete';

export type GoalId =
  | 'lose_weight'
  | 'build_muscle'
  | 'improve_endurance'
  | 'marathon'
  | 'ironman'
  | 'beach_body'
  | 'maintain';

export interface Goal {
  id: GoalId;
  label: string;
  blurb: string;
  /** kcal delta vs. maintenance (TDEE). */
  calorieDelta: number;
  /** macro split as fractions of total calories: [protein, carbs, fat]. */
  macroSplit: [number, number, number];
  /** grams protein per kg bodyweight target (overrides split when higher). */
  proteinPerKg: number;
}

export interface Targets {
  bmr: number;
  tdee: number;
  calories: number;
  protein: number; // grams
  carbs: number; // grams
  fat: number; // grams
}

export interface Profile {
  name: string;
  sex: Sex;
  age: number;
  heightCm: number;
  weightKg: number;
  activity: ActivityLevel;
  goal: GoalId;
  units: 'metric' | 'imperial';
}

export interface FoodEntry {
  id: string;
  date: string; // YYYY-MM-DD
  name: string;
  brand?: string;
  serving?: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  source: 'scan' | 'manual';
  barcode?: string;
  healthScore?: number; // 0-100
  createdAt: number;
}

export interface Habit {
  id: string;
  label: string;
  icon: string; // emoji-free: we map to a Feather-ish name
  /** core habits feed the plant's growth each day. */
  core: boolean;
}

export interface DayLog {
  date: string; // YYYY-MM-DD
  completedHabits: string[]; // habit ids
  weightKg?: number;
}

export type ScanVerdict = 'excellent' | 'good' | 'fair' | 'poor';

export interface ScannedProduct {
  barcode: string;
  name: string;
  brand?: string;
  imageUrl?: string;
  serving?: string;
  per100g: { calories: number; protein: number; carbs: number; fat: number };
  perServing?: { calories: number; protein: number; carbs: number; fat: number };
  healthScore: number; // 0-100
  verdict: ScanVerdict;
  positives: string[];
  negatives: string[];
  nutriScore?: string;
  novaGroup?: number;
}
