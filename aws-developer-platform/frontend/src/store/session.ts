import { create } from 'zustand';

export interface SessionState {
  readonly identity: string | null;
  readonly role: 'Developer' | 'Team_Lead' | 'Platform_Admin' | null;
  readonly setSession: (identity: string, role: SessionState['role']) => void;
  readonly clear: () => void;
}

export const useSession = create<SessionState>((set) => ({
  identity: null,
  role: null,
  setSession: (identity, role) => set({ identity, role }),
  clear: () => set({ identity: null, role: null }),
}));
