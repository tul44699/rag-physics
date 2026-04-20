import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import type { UserProfile } from '../api/types';
import { useAuth } from './AuthContext';

interface ProfileState {
  userId: string;
  profile: UserProfile | null;
  isLoading: boolean;
  loadProfile: () => Promise<void>;
  saveProfile: (updates: Record<string, unknown>) => Promise<void>;
  logEvent: (event: {
    event_type: string;
    chapter?: string | null;
    textbook_id?: number | null;
    minutes_spent?: number;
    score?: number | null;
  }) => Promise<void>;
}

const ProfileContext = createContext<ProfileState | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const userId = String(user?.user_id ?? '');
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadProfile = useCallback(async () => {
    if (!userId) return;
    setIsLoading(true);
    try {
      const res = await fetch('/api/profile', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      setProfile(data.profile);
    } catch {
      // Profile not found
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  // Auto-load on mount
  useEffect(() => { loadProfile(); }, [loadProfile]);

  const saveProfile = useCallback(
    async (updates: Record<string, unknown>) => {
      const merged = { ...profile, ...updates };
      const res = await fetch('/api/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ profile: merged }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      setProfile(data.profile);
    },
    [profile],
  );

  const logEvent = useCallback(
    async (event: {
      event_type: string;
      chapter?: string | null;
      textbook_id?: number | null;
      minutes_spent?: number;
      score?: number | null;
    }) => {
      await fetch('/api/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(event),
      });
    },
    [],
  );

  return (
    <ProfileContext.Provider
      value={{ userId, profile, isLoading, loadProfile, saveProfile, logEvent }}
    >
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile() {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error('useProfile must be inside ProfileProvider');
  return ctx;
}
