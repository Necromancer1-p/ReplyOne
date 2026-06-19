import { create } from 'zustand';

interface AuthState {
  token: string | null;
  role: string | null;
  tenantId: number | null;
  onboardingComplete: boolean;
  isAuthenticated: boolean;
  login: (token: string, role: string, tenantId: number, onboardingComplete: boolean) => void;
  logout: () => void;
  setOnboardingComplete: (complete: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => {
  // Load initial values from localStorage
  const savedToken = localStorage.getItem('replyone_token');
  const savedRole = localStorage.getItem('replyone_role');
  const savedTenantId = localStorage.getItem('replyone_tenant_id');
  const savedOnboarding = localStorage.getItem('replyone_onboarding_complete');

  return {
    token: savedToken,
    role: savedRole,
    tenantId: savedTenantId ? parseInt(savedTenantId, 10) : null,
    onboardingComplete: savedOnboarding === 'true',
    isAuthenticated: !!savedToken,

    login: (token, role, tenantId, onboardingComplete) => {
      localStorage.setItem('replyone_token', token);
      localStorage.setItem('replyone_role', role);
      localStorage.setItem('replyone_tenant_id', tenantId.toString());
      localStorage.setItem('replyone_onboarding_complete', onboardingComplete.toString());
      
      set({
        token,
        role,
        tenantId,
        onboardingComplete,
        isAuthenticated: true,
      });
    },

    logout: () => {
      localStorage.removeItem('replyone_token');
      localStorage.removeItem('replyone_role');
      localStorage.removeItem('replyone_tenant_id');
      localStorage.removeItem('replyone_onboarding_complete');
      
      set({
        token: null,
        role: null,
        tenantId: null,
        onboardingComplete: false,
        isAuthenticated: false,
      });
    },

    setOnboardingComplete: (complete) => {
      localStorage.setItem('replyone_onboarding_complete', complete.toString());
      set({ onboardingComplete: complete });
    },
  };
});
