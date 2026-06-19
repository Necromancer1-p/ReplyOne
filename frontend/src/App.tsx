import { useState } from 'react';
import { useAuthStore } from './store/useAuthStore';
import { AuthScreens } from './components/AuthScreens';
import { OnboardingWizard } from './components/OnboardingWizard';
import { InboxView } from './components/InboxView';
import { KnowledgeBaseView } from './components/KnowledgeBaseView';
import { ProductsView } from './components/ProductsView';
import { SettingsView } from './components/SettingsView';
import { AnalyticsView } from './components/AnalyticsView';

import { 
  MessageSquare, BookOpen, ShoppingBag, Settings, 
  TrendingUp, LogOut, Bot, Sparkles, User
} from 'lucide-react';

function App() {
  const { isAuthenticated, onboardingComplete, logout } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'inbox' | 'kb' | 'products' | 'settings' | 'analytics'>('inbox');
  const [, setAuthTrigger] = useState(0);

  // Force re-render on login success
  const handleAuthSuccess = () => {
    setAuthTrigger(prev => prev + 1);
  };

  // If not authenticated, render Login/Register
  if (!isAuthenticated) {
    return <AuthScreens onSuccess={handleAuthSuccess} />;
  }

  // If authenticated but onboarding is incomplete, render the Onboarding wizard
  if (!onboardingComplete) {
    return <OnboardingWizard onComplete={handleAuthSuccess} />;
  }

  return (
    <div className="flex h-screen bg-deepNavy text-cloudWhite font-sans">
      
      {/* 1. Sidebar Navigation */}
      <aside className="w-64 bg-darkSidebarBg border-r border-darkBorder flex flex-col justify-between shrink-0">
        
        {/* Top Logo Area */}
        <div className="space-y-lg">
          <div className="h-16 px-lg flex items-center border-b border-darkBorder">
            <h1 className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-electricBlue to-cyberTeal tracking-wider flex items-center gap-xs">
              <Bot size={22} className="text-electricBlue" />
              ReplyOne
            </h1>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-xs px-sm">
            {[
              { id: 'inbox', label: 'Conversations', icon: <MessageSquare size={16} /> },
              { id: 'kb', label: 'Knowledge Base', icon: <BookOpen size={16} /> },
              { id: 'products', label: 'Products Catalog', icon: <ShoppingBag size={16} /> },
              { id: 'settings', label: 'Settings Panel', icon: <Settings size={16} /> },
              { id: 'analytics', label: 'Performance', icon: <TrendingUp size={16} /> },
            ].map((item) => {
              const active = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id as any)}
                  className={`w-full flex items-center gap-md px-md py-md-sm rounded-default text-xs font-semibold tracking-wide transition-all border-none cursor-pointer ${
                    active 
                      ? 'bg-electricBlue/10 text-electricBlue border-l-4 border-l-electricBlue font-bold' 
                      : 'text-darkSecondaryText hover:text-cloudWhite hover:bg-darkCardBg/20'
                  }`}
                >
                  {item.icon}
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom Profile / Logout */}
        <div className="p-md border-t border-darkBorder space-y-md">
          <div className="flex items-center gap-md">
            <div className="w-8 h-8 rounded-full bg-darkCardBg border border-darkBorder flex items-center justify-center text-cyberTeal">
              <User size={16} />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-cloudWhite truncate">Admin Account</p>
              <span className="text-[10px] text-darkSecondaryText">Owner Role</span>
            </div>
          </div>

          <button
            onClick={() => {
              logout();
              handleAuthSuccess();
            }}
            className="w-full py-xs px-sm bg-darkBorder/40 hover:bg-alertRed/10 hover:text-alertRed text-darkSecondaryText border border-darkBorder rounded-default text-xs font-semibold flex items-center justify-center gap-xs cursor-pointer transition-all"
          >
            <LogOut size={14} />
            Log Out
          </button>
        </div>

      </aside>

      {/* 2. Main Workspace */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-deepNavy">
        {/* Header Bar */}
        <header className="h-16 px-lg border-b border-darkBorder flex items-center justify-between bg-darkSidebarBg select-none shrink-0">
          <div>
            <h2 className="text-sm font-bold text-cloudWhite capitalize">
              {activeTab === 'inbox' && 'Unified Inbox Workspace'}
              {activeTab === 'kb' && 'LLM Context FAQs'}
              {activeTab === 'products' && 'Product Specifications'}
              {activeTab === 'settings' && 'System Parameters'}
              {activeTab === 'analytics' && 'Operational Analytics'}
            </h2>
          </div>
          <div className="flex items-center gap-sm">
            <span className="bg-cyberTeal/10 text-cyberTeal text-[10px] px-sm py-[2px] rounded-pill border border-cyberTeal/20 flex items-center gap-[2px] font-mono">
              <Sparkles size={10} /> Active Copilot Engine
            </span>
          </div>
        </header>

        {/* Tab Contents */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'inbox' && <InboxView />}
          {activeTab === 'kb' && <KnowledgeBaseView />}
          {activeTab === 'products' && <ProductsView />}
          {activeTab === 'settings' && <SettingsView />}
          {activeTab === 'analytics' && <AnalyticsView />}
        </div>
      </main>

    </div>
  );
}

export default App;
