"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState } from "react";
import type { User } from "firebase/auth";
import { auth, onIdTokenChanged } from "@/lib/firebase";
import { tokenStore } from "@/lib/token-store";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
}

const AuthContext = createContext<AuthContextValue>({ user: null, loading: true });

export function useAuth() {
  return useContext(AuthContext);
}

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

export function Providers({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_AUTH_BYPASS === "1") {
      tokenStore.set("local-dev");
      setLoading(false);
      return;
    }

    const unsubscribe = onIdTokenChanged(auth, async (u) => {
      if (u) {
        const token = await u.getIdToken();
        tokenStore.set(token);
        setUser(u);
      } else {
        tokenStore.set("");
        setUser(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading }}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </AuthContext.Provider>
  );
}
