import { create } from "zustand";

interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem("mj_token"),
  user: null,
  setAuth: (token, user) => {
    localStorage.setItem("mj_token", token);
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem("mj_token");
    set({ token: null, user: null });
  },
  isAuthenticated: () => !!get().token,
}));
