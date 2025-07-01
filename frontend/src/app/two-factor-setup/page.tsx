'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Logo } from '../../components';

const TwoFactorSetupPage = () => {
  const router = useRouter();

  useEffect(() => {
    // Redirect to dashboard since 2FA is not supported in new schema
    const timer = setTimeout(() => {
      router.push('/dashboard');
    }, 3000);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-red-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo and Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-6">
            <Logo size="xl" showText={true} href={null} theme="dark" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Feature Not Available</h1>
          <p className="text-gray-400">Two-factor authentication is currently not available</p>
        </div>

        {/* Info Card */}
        <div className="glass rounded-2xl p-8 shadow-2xl text-center">
          <div className="mb-6">
            <svg className="w-16 h-16 text-yellow-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Two-Factor Authentication</h2>
            <p className="text-gray-600 mb-4">
              This feature is temporarily unavailable. You'll be redirected to your dashboard in a moment.
            </p>
          </div>
          
          <div className="space-y-3">
            <button
              onClick={() => router.push('/dashboard')}
              className="w-full bg-gradient-to-r from-red-600 to-orange-600 text-white py-3 px-4 rounded-xl font-medium hover:from-red-700 hover:to-orange-700 transition-all duration-200"
            >
              Go to Dashboard
            </button>
          </div>
        </div>

        {/* Security Notice */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-400">
            Your account is still secure with our advanced encryption and monitoring systems.
          </p>
        </div>
      </div>
    </div>
  );
};

export default TwoFactorSetupPage;
