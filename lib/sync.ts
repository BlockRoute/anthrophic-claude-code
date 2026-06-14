import { isCloudEnabled, supabase } from './supabase';
import { useStore } from './store';

/** Fields of the store that represent durable user data. */
function snapshot() {
  const s = useStore.getState();
  return {
    onboarded: s.onboarded,
    profile: s.profile,
    targets: s.targets,
    habits: s.habits,
    logs: s.logs,
    foods: s.foods,
    reminders: s.reminders,
  };
}

let pushTimer: ReturnType<typeof setTimeout> | null = null;

/** Pull the cloud snapshot into the store on login. */
export async function pullSnapshot(userId: string): Promise<void> {
  if (!isCloudEnabled || !supabase) return;
  const { data, error } = await supabase
    .from('app_state')
    .select('snapshot')
    .eq('user_id', userId)
    .maybeSingle();
  if (error || !data?.snapshot) return;
  useStore.setState(data.snapshot);
}

async function flush(userId: string) {
  if (!isCloudEnabled || !supabase) return;
  await supabase
    .from('app_state')
    .upsert({ user_id: userId, snapshot: snapshot() }, { onConflict: 'user_id' });
}

/** Debounced push — call after any meaningful state change. */
export function schedulePush(userId: string): void {
  if (!isCloudEnabled) return;
  if (pushTimer) clearTimeout(pushTimer);
  pushTimer = setTimeout(() => void flush(userId), 1200);
}

/** Subscribe the store to auto-push while signed in. Returns unsubscribe. */
export function startAutoSync(userId: string): () => void {
  return useStore.subscribe(() => schedulePush(userId));
}
