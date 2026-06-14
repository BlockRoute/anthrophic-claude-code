import type { ScanVerdict, ScannedProduct } from './types';

const ENDPOINT = 'https://world.openfoodfacts.org/api/v2/product';
const FIELDS = [
  'code',
  'product_name',
  'brands',
  'image_front_small_url',
  'serving_size',
  'nutriments',
  'nutriscore_grade',
  'nova_group',
  'nutrient_levels',
  'additives_tags',
  'ingredients_analysis_tags',
].join(',');

interface OFFNutriments {
  ['energy-kcal_100g']?: number;
  ['energy-kcal_serving']?: number;
  proteins_100g?: number;
  proteins_serving?: number;
  carbohydrates_100g?: number;
  carbohydrates_serving?: number;
  fat_100g?: number;
  fat_serving?: number;
  sugars_100g?: number;
  ['saturated-fat_100g']?: number;
  salt_100g?: number;
  fiber_100g?: number;
}

const num = (v: unknown, fallback = 0): number =>
  typeof v === 'number' && !Number.isNaN(v) ? v : fallback;

/**
 * Yuka-style 0–100 health score, transparent and rebuildable.
 *  - 60% nutritional quality (energy, sugar, sat fat, salt vs. protein/fibre)
 *  - 30% additives (NOVA processing + flagged additives)
 *  - 10% organic/clean ingredients signal
 */
function scoreProduct(n: OFFNutriments, nova: number, additives: number) {
  const sugar = num(n.sugars_100g);
  const satFat = num(n['saturated-fat_100g']);
  const salt = num(n.salt_100g);
  const energy = num(n['energy-kcal_100g']);
  const protein = num(n.proteins_100g);
  const fiber = num(n.fiber_100g);

  // Negative load (0 best, 1 worst) for each axis, then averaged.
  const sugarPart = Math.min(sugar / 27, 1);
  const satPart = Math.min(satFat / 15, 1);
  const saltPart = Math.min(salt / 2.3, 1);
  const energyPart = Math.min(energy / 600, 1);
  const negative = (sugarPart + satPart + saltPart + energyPart) / 4;

  const proteinBonus = Math.min(protein / 25, 1);
  const fiberBonus = Math.min(fiber / 10, 1);
  const positive = (proteinBonus + fiberBonus) / 2;

  let nutrition = (1 - negative) * 0.75 + positive * 0.25; // 0..1

  // Processing penalty (NOVA 1 clean → 4 ultra-processed).
  const novaPenalty = nova >= 4 ? 0.35 : nova === 3 ? 0.18 : nova === 2 ? 0.06 : 0;
  const additivePenalty = Math.min(additives * 0.04, 0.2);

  const score = Math.round(
    Math.max(0, Math.min(1, nutrition * 0.7 + 0.3 - novaPenalty - additivePenalty)) * 100,
  );
  return score;
}

function verdictFor(score: number): ScanVerdict {
  if (score >= 75) return 'excellent';
  if (score >= 55) return 'good';
  if (score >= 35) return 'fair';
  return 'poor';
}

export async function fetchProduct(barcode: string): Promise<ScannedProduct | null> {
  const res = await fetch(`${ENDPOINT}/${encodeURIComponent(barcode)}.json?fields=${FIELDS}`);
  if (!res.ok) return null;
  const json = await res.json();
  if (json.status === 0 || !json.product) return null;

  const p = json.product;
  const n: OFFNutriments = p.nutriments ?? {};
  const nova = num(p.nova_group, 1);
  const additivesCount = Array.isArray(p.additives_tags) ? p.additives_tags.length : 0;
  const score = scoreProduct(n, nova, additivesCount);

  const per100g = {
    calories: Math.round(num(n['energy-kcal_100g'])),
    protein: Math.round(num(n.proteins_100g)),
    carbs: Math.round(num(n.carbohydrates_100g)),
    fat: Math.round(num(n.fat_100g)),
  };

  const hasServing = n['energy-kcal_serving'] != null;
  const perServing = hasServing
    ? {
        calories: Math.round(num(n['energy-kcal_serving'])),
        protein: Math.round(num(n.proteins_serving)),
        carbs: Math.round(num(n.carbohydrates_serving)),
        fat: Math.round(num(n.fat_serving)),
      }
    : undefined;

  // Build the qualitative reasons (the "why" Yuka shows).
  const positives: string[] = [];
  const negatives: string[] = [];
  const levels = p.nutrient_levels ?? {};

  if (num(n.proteins_100g) >= 12) positives.push('Good source of protein');
  if (num(n.fiber_100g) >= 5) positives.push('High in fibre');
  if (levels.sugars === 'low') positives.push('Low sugar');
  if (levels.salt === 'low') positives.push('Low salt');
  if (nova <= 1) positives.push('Unprocessed ingredients');
  if ((p.ingredients_analysis_tags ?? []).includes('en:palm-oil-free'))
    positives.push('Palm-oil free');

  if (levels.sugars === 'high') negatives.push('High in sugar');
  if (levels['saturated-fat'] === 'high') negatives.push('High in saturated fat');
  if (levels.salt === 'high') negatives.push('High in salt');
  if (nova >= 4) negatives.push('Ultra-processed (NOVA 4)');
  if (additivesCount >= 3) negatives.push(`${additivesCount} additives`);

  return {
    barcode: p.code ?? barcode,
    name: (p.product_name || '').trim() || 'Unknown product',
    brand: (p.brands || '').split(',')[0]?.trim() || undefined,
    imageUrl: p.image_front_small_url || undefined,
    serving: p.serving_size || undefined,
    per100g,
    perServing,
    healthScore: score,
    verdict: verdictFor(score),
    positives,
    negatives,
    nutriScore: p.nutriscore_grade ? String(p.nutriscore_grade).toUpperCase() : undefined,
    novaGroup: nova,
  };
}

/**
 * Suggest a healthier alternative in the same broad category.
 * OFF search is best-effort; we filter to higher-protein / better Nutri-Score.
 */
export async function fetchAlternatives(
  product: ScannedProduct,
  limit = 3,
): Promise<ScannedProduct[]> {
  const term = product.name.split(' ').slice(0, 2).join(' ') || product.brand || '';
  if (!term) return [];
  const url =
    `https://world.openfoodfacts.org/cgi/search.pl?search_terms=${encodeURIComponent(term)}` +
    `&search_simple=1&action=process&json=1&page_size=20&fields=${FIELDS}`;
  try {
    const res = await fetch(url);
    if (!res.ok) return [];
    const json = await res.json();
    const products = Array.isArray(json.products) ? json.products : [];
    const mapped: ScannedProduct[] = products
      .map((p: any): ScannedProduct | null => {
        const n: OFFNutriments = p.nutriments ?? {};
        if (!n['energy-kcal_100g']) return null;
        const nova = num(p.nova_group, 1);
        const additives = Array.isArray(p.additives_tags) ? p.additives_tags.length : 0;
        const score = scoreProduct(n, nova, additives);
        return {
          barcode: p.code ?? '',
          name: (p.product_name || '').trim(),
          brand: (p.brands || '').split(',')[0]?.trim() || undefined,
          imageUrl: p.image_front_small_url || undefined,
          per100g: {
            calories: Math.round(num(n['energy-kcal_100g'])),
            protein: Math.round(num(n.proteins_100g)),
            carbs: Math.round(num(n.carbohydrates_100g)),
            fat: Math.round(num(n.fat_100g)),
          },
          healthScore: score,
          verdict: verdictFor(score),
          positives: [],
          negatives: [],
        };
      })
      .filter((x: ScannedProduct | null): x is ScannedProduct => !!x && !!x.name);

    return mapped
      .filter((p) => p.barcode !== product.barcode && p.healthScore > product.healthScore + 8)
      .sort((a, b) => b.healthScore - a.healthScore)
      .slice(0, limit);
  } catch {
    return [];
  }
}
