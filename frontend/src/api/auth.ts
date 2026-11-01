import { api } from "../lib/api-client";
import type { User } from "../types";

export const authApi = {
  register: (email: string, password: string, display_name?: string) =>
    api.post<User>("/auth/register", { email, password, display_name }),
  login: (email: string, password: string) =>
    api.post<User>("/auth/login", { email, password }),
  logout: () => api.post<void>("/auth/logout"),
  me: () => api.get<User>("/me"),
  completeOnboarding: () => api.post<User>("/me/complete-onboarding"),
};
