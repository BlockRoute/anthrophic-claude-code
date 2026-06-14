import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

export interface ReminderPrefs {
  enabled: boolean;
  morningHour: number; // habit nudge
  morningMinute: number;
  eveningHour: number; // "tend your tree" wind-down
  eveningMinute: number;
  workoutEnabled: boolean;
  workoutHour: number;
  workoutMinute: number;
}

export const DEFAULT_REMINDERS: ReminderPrefs = {
  enabled: true,
  morningHour: 8,
  morningMinute: 0,
  eveningHour: 20,
  eveningMinute: 30,
  workoutEnabled: true,
  workoutHour: 17,
  workoutMinute: 30,
};

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

export async function requestPermission(): Promise<boolean> {
  const { status } = await Notifications.getPermissionsAsync();
  if (status === 'granted') return true;
  const req = await Notifications.requestPermissionsAsync();
  return req.status === 'granted';
}

async function daily(hour: number, minute: number, title: string, body: string) {
  await Notifications.scheduleNotificationAsync({
    content: { title, body },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DAILY,
      hour,
      minute,
    },
  });
}

/** Rebuild the full schedule from prefs (clears the old one first). */
export async function syncReminders(prefs: ReminderPrefs): Promise<void> {
  if (Platform.OS === 'web') return;
  await Notifications.cancelAllScheduledNotificationsAsync();
  if (!prefs.enabled) return;
  const granted = await requestPermission();
  if (!granted) return;

  await daily(
    prefs.morningHour,
    prefs.morningMinute,
    'Plant the day',
    'Check in with your habits — your tree is waiting to grow.',
  );
  await daily(
    prefs.eveningHour,
    prefs.eveningMinute,
    'Tend before bed',
    "A few unchecked habits left. Don't let today's growth slip away.",
  );
  if (prefs.workoutEnabled) {
    await daily(
      prefs.workoutHour,
      prefs.workoutMinute,
      'Movement window',
      'Time to train. Logging it nurtures your tree.',
    );
  }
}

export const fmtTime = (h: number, m: number) => {
  const ampm = h >= 12 ? 'PM' : 'AM';
  const hr = h % 12 === 0 ? 12 : h % 12;
  return `${hr}:${String(m).padStart(2, '0')} ${ampm}`;
};
