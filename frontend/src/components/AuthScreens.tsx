import React, { useState } from 'react';
import { useAuthStore } from '../store/useAuthStore';
import { api } from '../utils/api';
import { KeyRound, Mail, Building2, UserPlus, LogIn, Loader2 } from 'lucide-react';

interface AuthScreensProps {
  onSuccess: () => void;
}

export const AuthScreens: React.FC<AuthScreensProps> = ({ onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const loginStore = useAuthStore((state) => state.login);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (!isLogin) {
        if (password.length < 8) {
          throw new Error('Password must be at least 8 characters long.');
        }
        if (!businessName.trim()) {
          throw new Error('Business name is required.');
        }
      }

      if (isLogin) {
        // Login endpoint
        const response = await api.post<{
          access_token: string;
          role: string;
          tenant_id: number;
          onboarding_complete: boolean;
        }>('/auth/login', { email, password });
        
        loginStore(
          response.access_token,
          response.role,
          response.tenant_id,
          response.onboarding_complete
        );
        onSuccess();
      } else {
        // Register endpoint
        const response = await api.post<{
          access_token: string;
          role: string;
          tenant_id: number;
          onboarding_complete: boolean;
        }>('/auth/register', { 
          email, 
          password, 
          business_name: businessName 
        });
        
        loginStore(
          response.access_token,
          response.role,
          response.tenant_id,
          response.onboarding_complete
        );
        onSuccess();
      }
    } catch (err: any) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-deepNavy text-cloudWhite flex flex-col items-center justify-center p-md bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigoBrand/20 via-deepNavy to-deepNavy">
      <div className="w-full max-w-md bg-darkCardBg/60 backdrop-blur-md border border-darkBorder rounded-large p-xl shadow-lg relative overflow-hidden">
        {/* Glow effect */}
        <div className="absolute -top-16 -left-16 w-32 h-32 bg-electricBlue/20 rounded-full blur-xl"></div>
        <div className="absolute -bottom-16 -right-16 w-32 h-32 bg-cyberTeal/20 rounded-full blur-xl"></div>

        <div className="text-center mb-lg relative">
          <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-electricBlue to-cyberTeal tracking-wide font-sans">
            ReplyOne
          </h1>
          <p className="text-darkSecondaryText text-sm mt-xs">
            {isLogin ? 'Welcome back! Sign in to manage your AI support agent' : 'Empower your business with multi-tenant AI aggregation'}
          </p>
        </div>

        {error && (
          <div className="mb-md p-md-sm bg-alertRed/10 border border-alertRed/30 text-alertRed rounded-default text-sm flex items-center gap-xs">
            <span className="font-semibold">Error:</span> {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-md">
          {!isLogin && (
            <div className="space-y-xs">
              <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Business Name</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-md-sm flex items-center pointer-events-none text-softSlate">
                  <Building2 size={18} />
                </div>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Corporation"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  className="w-full pl-lg pr-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue transition-all text-sm"
                />
              </div>
            </div>
          )}

          <div className="space-y-xs">
            <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Email Address</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-md-sm flex items-center pointer-events-none text-softSlate">
                <Mail size={18} />
              </div>
              <input
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-lg pr-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue transition-all text-sm"
              />
            </div>
          </div>

          <div className="space-y-xs">
            <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Password</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-md-sm flex items-center pointer-events-none text-softSlate">
                <KeyRound size={18} />
              </div>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-lg pr-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue transition-all text-sm"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-md-sm px-md mt-lg bg-gradient-to-r from-electricBlue to-indigoBrand text-white font-semibold rounded-default shadow-md hover:from-electricBlue/95 hover:to-indigoBrand/95 active:scale-[0.98] transition-all flex items-center justify-center gap-xs disabled:opacity-50 disabled:pointer-events-none text-sm cursor-pointer"
          >
            {loading ? (
              <Loader2 className="animate-spin" size={18} />
            ) : isLogin ? (
              <>
                <LogIn size={18} />
                Sign In
              </>
            ) : (
              <>
                <UserPlus size={18} />
                Create Account
              </>
            )}
          </button>
        </form>

        <div className="mt-lg pt-md border-t border-darkBorder text-center">
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
            }}
            className="text-sm text-cyberTeal hover:underline focus:outline-none bg-transparent border-none cursor-pointer"
          >
            {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
          </button>
        </div>
      </div>
    </div>
  );
};
