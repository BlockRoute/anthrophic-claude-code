# Verdant 🌱

A gamified fitness & nutrition tracker for mobile. Track calories and macros,
check off daily habits, and watch a tree grow as you stay consistent — neglect
it and it withers. Built with Expo (React Native).

> **Design direction:** "deep calm" — a near-black, green-tinted canvas, muted
> bioluminescent accents, soft glass surfaces, and a Fraunces × Hanken Grotesk
> type pairing. Deliberately not the default RN / "vibe-coded" look.

## Features

- **Living tree gamification** — core habits feed a tree that grows through six
  stages (seed → ancient) and withers when you fall off. Streaks, vitality, and
  stage progress are all derived from your habit history.
- **Calories & macros** — personalized targets from the Mifflin–St Jeor
  equation + activity level + goal. Animated calorie ring and macro bars.
- **Daily habits / to-dos** — tap to complete, with haptics; add your own.
- **Barcode food scanning** — scan a product (Open Food Facts) to auto-log
  calories/macros, get a Yuka-style 0–100 health score with the *why*, and see
  **healthier alternatives**.
- **Progress** — weight trend chart, 7-day consistency bars, streak & vitality.
- **Smart reminders** — schedulable morning nudge, evening wind-down, and
  workout reminder via local notifications.
- **Personalized onboarding** — weight, height, age, sex, activity, and a goal
  picked from a dropdown (lose weight, build muscle, endurance, marathon,
  Ironman, beach body, maintain).
- **Accounts & sync** — optional Supabase auth with snapshot sync; runs fully
  on-device in *local mode* without any credentials.

## Run it

```bash
npm install
npx expo start          # press i / a, or scan the QR with Expo Go
```

The app works immediately in **local mode** (data stored on-device).

### Enable cloud accounts + sync (optional)

1. Create a project at [supabase.com](https://supabase.com).
2. Run [`supabase/schema.sql`](supabase/schema.sql) in the SQL editor.
3. Copy `.env.example` to `.env` and fill in:
   ```
   EXPO_PUBLIC_SUPABASE_URL=...
   EXPO_PUBLIC_SUPABASE_ANON_KEY=...
   ```
4. Restart the dev server. Sign-up now creates a real account and your data
   syncs across devices.

**Email confirmation deep link.** Sign-up uses Supabase's PKCE flow; the
confirmation email returns to `verdant://auth-callback`, which is handled by
`app/auth-callback.tsx` (exchanges the code for a session, then continues
onboarding). In the Supabase dashboard add this under
**Authentication → URL Configuration → Redirect URLs**:

```
verdant://auth-callback
exp://127.0.0.1:8081/--/auth-callback   # for Expo Go during development
```

Email delivery needs an SMTP provider configured under
**Authentication → Emails → SMTP Settings** (Resend or Brevo both have free
tiers); the built-in sender is rate-limited and for testing only.

## Architecture

```
app/                     expo-router screens
  (onboarding)/          welcome → auth → profile → goal → targets
  (tabs)/                today · nutrition · scan · progress · profile
components/               UI primitives, Plant (SVG), rings, charts, sheets
lib/
  theme.ts               design tokens (color, type, spacing)
  nutrition.ts           BMR/TDEE + macro targeting, unit conversions
  plant.ts               growth/withering engine (pure, derived from logs)
  openfoodfacts.ts       product lookup + health scoring + alternatives
  notifications.ts       local reminder scheduling
  store.ts               Zustand store, AsyncStorage-persisted
  supabase.ts / auth.ts / sync.ts   optional cloud layer
supabase/schema.sql      app_state table + RLS for cloud mode
```

State lives in a persisted Zustand store. The tree, streaks, calorie totals,
and charts are all *derived* from your logs, so they can be recomputed any time
without drifting.

## Notes & next steps

- Health scoring is a transparent heuristic over Open Food Facts data
  (nutrients + NOVA processing + additives). It approximates Yuka; it is not
  medical advice.
- Cloud sync uses a single JSON snapshot per user (simple and conflict-free for
  one device-owner). `supabase/schema.sql` includes commented normalized tables
  for teams that outgrow it.
- Camera scanning requires a device/dev build; the Scan screen also accepts a
  typed-in barcode so it works in the simulator and on web.
