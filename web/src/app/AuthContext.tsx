import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, AUTH_SESSION_EXPIRED_EVENT } from "../lib/api";
import type { AuthUser, BillingCapabilities, Subscription } from "../lib/types";

const AuthContext = createContext<{
  user: AuthUser | null;
  subscription: Subscription | null;
  billingCapabilities: BillingCapabilities | null;
  freeAccess: boolean;
  demoMode: boolean;
  isOperator: boolean;
  sessionExpired: boolean;
  loading: boolean;
  login: (email: string, password: string, otp?: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
} | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [billingCapabilities, setBillingCapabilities] =
    useState<BillingCapabilities | null>(null);
  const [isOperator, setIsOperator] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [loading, setLoading] = useState(true);
  const loadAccess = useCallback(async () => {
    const [subscriptionResult, capabilitiesResult] = await Promise.allSettled([
      api.subscription(),
      api.billingCapabilities(),
    ]);
    setSubscription(
      subscriptionResult.status === "fulfilled"
        ? subscriptionResult.value
        : null,
    );
    setBillingCapabilities(
      capabilitiesResult.status === "fulfilled"
        ? capabilitiesResult.value
        : null,
    );
  }, []);

  useEffect(() => {
    const expireSession = () => {
      setUser(null);
      setSubscription(null);
      setBillingCapabilities(null);
      setIsOperator(false);
      setDemoMode(false);
      setSessionExpired(true);
      setLoading(false);
    };
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, expireSession);
    return () =>
      window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, expireSession);
  }, []);

  useEffect(() => {
    let active = true;
    api
      .me()
      .then(async (result) => {
        if (!active) return;
        setUser(result.user);
        setIsOperator(result.is_operator);
        setDemoMode(result.demo_mode);
        setSessionExpired(false);
        await loadAccess();
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
        setSubscription(null);
        setBillingCapabilities(null);
        setIsOperator(false);
        setDemoMode(false);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadAccess]);
  const refresh = useCallback(async () => {
    const result = await api.me();
    setUser(result.user);
    setIsOperator(result.is_operator);
    setDemoMode(result.demo_mode);
    await loadAccess();
  }, [loadAccess]);
  const value = useMemo(
    () => ({
      user,
      subscription,
      billingCapabilities,
      freeAccess: billingCapabilities?.free_access ?? false,
      demoMode,
      isOperator,
      sessionExpired,
      loading,
      login: async (email: string, password: string, otp?: string) => {
        const result = await api.login(email, password, otp);
        setUser(result.user);
        setIsOperator(result.is_operator);
        setDemoMode(result.demo_mode);
        setSessionExpired(false);
        await loadAccess();
      },
      logout: async () => {
        await api.logout();
        setUser(null);
        setSubscription(null);
        setBillingCapabilities(null);
        setIsOperator(false);
        setDemoMode(false);
        setSessionExpired(false);
      },
      refresh,
    }),
    [
      user,
      subscription,
      billingCapabilities,
      demoMode,
      isOperator,
      sessionExpired,
      loading,
      refresh,
      loadAccess,
    ],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
