"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import {
  checkAuthConfig,
  fetchAuthMe,
  setSessionToken,
  getSessionToken,
  getLoginUrl,
  logout as apiLogout,
} from "./api";
import type { AuthUser } from "./types";

type AuthStatus =
  | "loading"
  | "unauthenticated"
  | "authenticated"
  | "oauth_not_configured";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  networkLoaded: boolean;
  authError: string | null;
  login: () => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [networkLoaded, setNetworkLoaded] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      // 1. Check OAuth config
      let oauthEnabled = false;
      try {
        oauthEnabled = await checkAuthConfig();
      } catch {
        // Server unreachable — treat as not configured
      }
      if (cancelled) return;

      if (!oauthEnabled) {
        setStatus("oauth_not_configured");
        return;
      }

      // 2. Handle OAuth callback params
      const params = new URLSearchParams(window.location.search);
      const callbackToken = params.get("auth_token");
      const callbackError = params.get("auth_error");

      if (callbackToken) {
        setSessionToken(callbackToken);
        window.history.replaceState({}, "", window.location.pathname);
      }
      if (callbackError) {
        setAuthError(callbackError);
        window.history.replaceState({}, "", window.location.pathname);
      }

      // 3. Validate existing session
      const token = getSessionToken();
      if (!token) {
        setStatus("unauthenticated");
        return;
      }

      try {
        const me = await fetchAuthMe();
        if (cancelled) return;

        if (me.authenticated && me.user) {
          setUser(me.user);
          setNetworkLoaded(me.network_loaded ?? false);
          setStatus("authenticated");

          // Poll until network is loaded
          if (!me.network_loaded && me.network_loading) {
            pollNetwork(cancelled);
          }
        } else {
          setSessionToken(null);
          setStatus("unauthenticated");
        }
      } catch {
        setSessionToken(null);
        setStatus("unauthenticated");
      }
    }

    async function pollNetwork(parentCancelled: boolean) {
      while (!parentCancelled) {
        await new Promise((r) => setTimeout(r, 3000));
        if (parentCancelled) return;
        try {
          const me = await fetchAuthMe();
          if (me.network_loaded) {
            setNetworkLoaded(true);
            return;
          }
          if (!me.network_loading) return;
        } catch {
          return;
        }
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(() => {
    window.location.href = getLoginUrl();
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    setNetworkLoaded(false);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider
      value={{ status, user, networkLoaded, authError, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}
