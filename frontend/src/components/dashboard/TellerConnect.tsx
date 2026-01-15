'use client';

import { useEffect, useState } from 'react';
import { saveTellerConnection } from '@/lib/api';

declare global {
  interface Window {
    TellerConnect: {
      setup: (config: any) => { open: () => void };
    };
  }
}

interface TellerConnectProps {
  onSuccess?: () => void;
}

export function TellerConnect({ onSuccess }: TellerConnectProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // Load Teller Connect script
    const script = document.createElement('script');
    script.src = 'https://cdn.teller.io/connect/connect.js';
    script.async = true;
    script.onload = () => setIsReady(true);
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const openTellerConnect = () => {
    if (!window.TellerConnect) {
      console.error('Teller Connect not loaded');
      return;
    }

    const tellerConnect = window.TellerConnect.setup({
      applicationId: process.env.NEXT_PUBLIC_TELLER_APP_ID || 'app_pn55bmnf8k4papve7o000',
      environment: process.env.NEXT_PUBLIC_TELLER_ENV || 'sandbox',
      products: ['balance', 'transactions', 'identity'],

      onSuccess: async (enrollment: any) => {
        console.log('Teller Connect success:', enrollment);
        setIsLoading(true);

        try {
          await saveTellerConnection({
            accessToken: enrollment.accessToken,
            enrollment: enrollment.enrollment,
            user: enrollment.user || {},
          });

          if (onSuccess) {
            onSuccess();
          }
        } catch (error) {
          console.error('Error saving connection:', error);
        } finally {
          setIsLoading(false);
        }
      },

      onExit: () => {
        console.log('User closed Teller Connect');
      },

      onFailure: (error: any) => {
        console.error('Teller Connect error:', error);
      },
    });

    tellerConnect.open();
  };

  return (
    <button
      onClick={openTellerConnect}
      disabled={!isReady || isLoading}
      className="inline-flex items-center justify-center gap-2 px-6 py-3 text-white bg-primary-500 rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
    >
      {isLoading ? (
        <>
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Connecting...
        </>
      ) : (
        <>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 6v6m0 0v6m0-6h6m-6 0H6"
            />
          </svg>
          Connect Bank Account
        </>
      )}
    </button>
  );
}
