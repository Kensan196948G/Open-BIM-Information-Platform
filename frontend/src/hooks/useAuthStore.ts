import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types";

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  setAuth: (token: string, user: User, refreshToken?: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      setAuth: (token, user, refreshToken) => {
        localStorage.setItem("access_token", token);
        if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
        set({ token, user, refreshToken: refreshToken ?? null });
      },
      logout: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({ token: null, refreshToken: null, user: null });
      },
    }),
    { name: "bim-auth" },
  ),
);
