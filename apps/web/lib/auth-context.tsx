"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch } from "./api-client";
import type { AuthResponse, MeResponse, Membership, User } from "./types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: User | null;
  organizations: Membership[];
  accessToken: string | null;
  currentOrganizationId: string | null;
  setCurrentOrganizationId: (id: string) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (
    organizationName: string,
    fullName: string,
    email: string,
    password: string
  ) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [organizations, setOrganizations] = useState<Membership[]>([]);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [currentOrganizationId, setCurrentOrganizationId] = useState<string | null>(null);

  const loadMe = useCallback(async (token: string) => {
    const me = await apiFetch<MeResponse>("/api/v1/users/me", { accessToken: token });
    setUser(me.user);
    setOrganizations(me.organizations);
    setCurrentOrganizationId((prev) => prev ?? me.organizations[0]?.organization.id ?? null);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const tokens = await apiFetch<AuthResponse>("/api/v1/auth/refresh", { method: "POST" });
        setAccessToken(tokens.access_token);
        await loadMe(tokens.access_token);
        setStatus("authenticated");
      } catch {
        setStatus("unauthenticated");
      }
    })();
  }, [loadMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await apiFetch<AuthResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setAccessToken(tokens.access_token);
      await loadMe(tokens.access_token);
      setStatus("authenticated");
    },
    [loadMe]
  );

  const register = useCallback(
    async (organizationName: string, fullName: string, email: string, password: string) => {
      const tokens = await apiFetch<AuthResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          organization_name: organizationName,
          full_name: fullName || null,
          email,
          password,
        }),
      });
      setAccessToken(tokens.access_token);
      await loadMe(tokens.access_token);
      setStatus("authenticated");
    },
    [loadMe]
  );

  const logout = useCallback(async () => {
    await apiFetch("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    setAccessToken(null);
    setUser(null);
    setOrganizations([]);
    setCurrentOrganizationId(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider
      value={{
        status,
        user,
        organizations,
        accessToken,
        currentOrganizationId,
        setCurrentOrganizationId,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
