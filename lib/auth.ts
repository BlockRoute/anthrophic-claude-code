import * as Linking from 'expo-linking';
import { isCloudEnabled, supabase } from './supabase';

export interface AuthResult {
  ok: boolean;
  error?: string;
  needsConfirmation?: boolean;
}

/** Deep link Supabase returns to after the user taps the confirmation email. */
export function authRedirectTo(): string {
  return Linking.createURL('auth-callback');
}

export async function signUp(email: string, password: string): Promise<AuthResult> {
  if (!isCloudEnabled || !supabase) return { ok: true };
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: { emailRedirectTo: authRedirectTo() },
  });
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

/** Exchange the `code` from a confirmation/magic-link deep link for a session. */
export async function exchangeCode(code: string): Promise<AuthResult> {
  if (!isCloudEnabled || !supabase) return { ok: true };
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) return { ok: false, error: error.message };
  return { ok: true };
}

export async function currentUserId(): Promise<string | null> {
  if (!isCloudEnabled || !supabase) return null;
  const { data } = await supabase.auth.getUser();
  return data.user?.id ?? null;
}
