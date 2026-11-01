import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { findDemoUser, type DemoUser } from "./demoUsers";

const STORAGE_KEY = "brisamar.demoToken";

interface DemoUserContextValue {
  user: DemoUser;
  selectUser: (token: string) => void;
}

const DemoUserContext = createContext<DemoUserContextValue | null>(null);

function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, token);
  } catch {
    return;
  }
}

export function DemoUserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<DemoUser>(() => findDemoUser(readStoredToken()));

  const selectUser = useCallback((token: string) => {
    const next = findDemoUser(token);
    storeToken(next.token);
    setUser(next);
  }, []);

  const value = useMemo(() => ({ user, selectUser }), [user, selectUser]);

  return <DemoUserContext.Provider value={value}>{children}</DemoUserContext.Provider>;
}

export function useDemoUser(): DemoUserContextValue {
  const context = useContext(DemoUserContext);
  if (!context) throw new Error("useDemoUser must be used inside DemoUserProvider");
  return context;
}
