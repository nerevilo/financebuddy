'use client';

import { SWRConfig } from 'swr';
import { AuthProvider } from '@/lib/auth';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <SWRConfig
        value={{
          revalidateOnFocus: true,
          revalidateOnReconnect: true,
          dedupingInterval: 2000,
          keepPreviousData: true,
        }}
      >
        {children}
      </SWRConfig>
    </AuthProvider>
  );
}
