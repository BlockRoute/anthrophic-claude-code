import { isCloudEnabled, supabase } from './supabase';

export interface AuthResult {
  ok: boolean;
  error?: string;
  needsConfirmation?: boolean;
}

export async function signUp(email: string, password: string): Promise<AuthResult> {
  if (!isCloudEnabled || !supabase) return { ok: true };
  const { data, error } = await supabase.auth.signUp({ email, password });
  if (error) return { ok: false, error: error.message };
  return { ok: true, needsConfirmation: !data.session };
}

export async function signIn(email: string, password: string): Promise<AuthResult> {
  if (!isCloudEnabled || !supabase) return { ok: true };
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { ok: false, error: error.message };
  return { ok: true };
}

export async function signOut(): Promise<void> {
  if (isCloudEnabled && supabase) await supabase.auth.signOut();
}

export async function currentUserId(): Promise<string | null> {
  if (!isCloudEnabled || !supabase) return null;
  const { data } = await supabase.auth.getUser();
  return data.user?.id ?? null;
}
