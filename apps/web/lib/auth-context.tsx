"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, ApiError } from "./api-client";
import type { AuthResponse, MeResponse, Membership, User } from "./types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: User | null;
  organizations: Membership[];
  accessToken: string | null;
  currentOrganizationId: string | null;
  setCurrentOrganizationId: (id: string) => void;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (
    organizationName: string,
    fullName: string,
    email: string,
    password: string
  ) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const REFRESH_STORAGE_KEY = "studio_refresh_token";
const REFRESH_INTERVAL_MS = 10 * 60 * 1000;

function readStoredRefreshToken(): string | null {
  try {
    return window.localStorage.getItem(REFRESH_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStoredRefreshToken(token: string | null): void {
  try {
    if (token) window.localStorage.setItem(REFRESH_STORAGE_KEY, token);
    else window.localStorage.removeItem(REFRESH_STORAGE_KEY);
  } catch {
    // storage unavailable (private mode etc.) - cookie-only session
  }
}

// Refresh tokens rotate on use, so two concurrent refreshes with the same
// token would make the second fail and log the user out; share one call.
let refreshInFlight: Promise<AuthResponse> | null = null;

function refreshSession(): Promise<AuthResponse> {
  if (!refreshInFlight) {
    const stored = readStoredRefreshToken();
    refreshInFlight = apiFetch<AuthResponse>("/api/v1/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: stored }),
    })
      .then((tokens) => {
        if (stored && tokens.refresh_token) writeStoredRefreshToken(tokens.refresh_token);
        return tokens;
      })
      .catch((err) => {
        if (stored && err instanceof ApiError && err.status === 401) writeStoredRefreshToken(null);
        throw err;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

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
        const tokens = await refreshSession();
        setAccessToken(tokens.access_token);
        await loadMe(tokens.access_token);
        setStatus("authenticated");
      } catch {
        setStatus("unauthenticated");
      }
    })();
  }, [loadMe]);

  useEffect(() => {
    if (status !== "authenticated") return;
    const intervalId = setInterval(() => {
      refreshSession()
        .then((tokens) => setAccessToken(tokens.access_token))
        .catch(() => undefined);
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [status]);

  const login = useCallback(
    async (email: string, password: string, rememberMe = false) => {
      const tokens = await apiFetch<AuthResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, remember_me: rememberMe }),
      });
      writeStoredRefreshToken(rememberMe ? (tokens.refresh_token ?? null) : null);
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
    await apiFetch("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: readStoredRefreshToken() }),
    }).catch(() => undefined);
    writeStoredRefreshToken(null);
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
