import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "../api/auth";
import type { User } from "../types";
import { ApiError } from "../lib/api-client";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, displayName?: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [checkedOnce, setCheckedOnce] = useState(false);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    retry: false,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (!meQuery.isLoading) setCheckedOnce(true);
  }, [meQuery.isLoading]);

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => authApi.login(email, password),
    onSuccess: (user) => queryClient.setQueryData(["me"], user),
  });

  const registerMutation = useMutation({
    mutationFn: ({ email, password, displayName }: { email: string; password: string; displayName?: string }) =>
      authApi.register(email, password, displayName),
    onSuccess: (user) => queryClient.setQueryData(["me"], user),
  });

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.setQueryData(["me"], null);
      queryClient.clear();
    },
  });

  const user = meQuery.data ?? null;
  const isAuthError = meQuery.error instanceof ApiError && meQuery.error.status === 401;

  const value: AuthContextValue = {
    user: isAuthError ? null : user,
    isLoading: !checkedOnce,
    login: async (email, password) => loginMutation.mutateAsync({ email, password }),
    register: async (email, password, displayName) => registerMutation.mutateAsync({ email, password, displayName }),
    logout: async () => {
      await logoutMutation.mutateAsync();
    },
    refreshUser: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
