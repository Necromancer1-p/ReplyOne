import React, { useState } from 'react';
import { api } from '../utils/api';
import { useAuthStore } from '../store/useAuthStore';
import { Bot, MessageSquare, Code, CheckCircle, ArrowRight, ArrowLeft, Loader2, Sparkles, MessageCircle, Copy, Check } from 'lucide-react';

interface OnboardingWizardProps {
  onComplete: () => void;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete }) => {
  const [step, setStep] = useState(1);
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [channelsConnected, setChannelsConnected] = useState<{ whatsapp: boolean; website: boolean }>({
    whatsapp: false,
    website: false,
  });
  const [aiTone, setAiTone] = useState('balanced');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.70);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const setOnboardingComplete = useAuthStore((state) => state.setOnboardingComplete);

  const businessSlug = 'test-boutique'; // Mock or computed slug from business name

  const handleConnectChannel = async (type: 'whatsapp' | 'website') => {
    try {
      const config = type === 'website' ? { color: '#6366F1' } : undefined;
      await api.post('/dashboard/channels', {
        channel_type: type,
        external_account_id: type === 'whatsapp' ? '1234567890' : 'widget_code_here',
        widget_config_json: config,
      });
      setChannelsConnected(prev => ({ ...prev, [type]: true }));
    } catch (err) {
      console.error('Channel connection failed:', err);
      // Even on failure (e.g. already exists), mock success for onboarding flow smoothness
      setChannelsConnected(prev => ({ ...prev, [type]: true }));
    }
  };

  const handleFinishOnboarding = async () => {
    setLoading(true);
    try {
      // Save AI settings
      await api.put('/dashboard/settings', {
        ai_tone: aiTone,
        ai_confidence_threshold: confidenceThreshold,
        ai_auto_reply_enabled: true,
      });

      // Complete Onboarding
      await api.post('/dashboard/onboarding/complete');
      
      setOnboardingComplete(true);
      onComplete();
    } catch (err) {
      console.error('Onboarding finalize failed:', err);
      // Fallback
      setOnboardingComplete(true);
      onComplete();
    } finally {
      setLoading(false);
    }
  };

  const copyWidgetCode = () => {
    const code = `<script>\n  (function(w,d,s,o,f,js,fjs){\n    w['ReplyOneWidget']=o;w[o]=w[o]||function(){(w[o].q=w[o].q||[]).push(arguments)};\n    js=d.createElement(s);fjs=d.getElementsByTagName(s)[0];\n    js.id='replyone-widget-script';js.src=f.src;js.async=1;fjs.parentNode.insertBefore(js,fjs);\n  }(window,document,'script','replyone',{\n    src: 'http://localhost:8000/static/widget.js',\n    tenant: '${businessSlug}'\n  }));\n</script>`;
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-deepNavy text-cloudWhite flex flex-col items-center justify-center p-md bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigoBrand/10 via-deepNavy to-deepNavy">
      <div className="w-full max-w-2xl bg-darkCardBg border border-darkBorder rounded-large p-xl shadow-lg relative">
        
        {/* Progress bar */}
        <div className="w-full bg-darkBorder h-1 rounded-full overflow-hidden mb-xl">
          <div 
            className="bg-gradient-to-r from-electricBlue to-cyberTeal h-full transition-all duration-300"
            style={{ width: `${(step / 4) * 100}%` }}
          ></div>
        </div>

        {/* Step Header */}
        <div className="mb-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-mono text-cyberTeal uppercase tracking-wider">Step {step} of 4</span>
            <h2 className="text-2xl font-bold font-sans mt-xs">
              {step === 1 && 'Configure Local Profile'}
              {step === 2 && 'Connect Messaging Channels'}
              {step === 3 && 'Configure AI Autopilot Settings'}
              {step === 4 && 'Launch Your Dashboard'}
            </h2>
          </div>
          <div className="p-sm bg-darkBorder/40 rounded-large text-indigoBrand">
            {step === 1 && <Bot size={24} />}
            {step === 2 && <MessageSquare size={24} />}
            {step === 3 && <Sparkles size={24} />}
            {step === 4 && <CheckCircle size={24} />}
          </div>
        </div>

        {/* Step Body */}
        <div className="py-md min-h-[220px]">
          
          {/* STEP 1: Settings */}
          {step === 1 && (
            <div className="space-y-md">
              <p className="text-darkSecondaryText text-sm leading-relaxed">
                Setup your local time zone so that AI automatic rules, analytics, and business hours operate in your local standard time.
              </p>
              <div className="space-y-xs">
                <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Timezone</label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full py-md-sm px-md bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite focus:outline-none focus:border-electricBlue text-sm cursor-pointer"
                >
                  <option value="Asia/Kolkata">Asia/Kolkata (GMT+5:30)</option>
                  <option value="UTC">UTC (Coordinated Universal Time)</option>
                  <option value="America/New_York">America/New_York (EST/EDT)</option>
                  <option value="Europe/London">Europe/London (BST/GMT)</option>
                </select>
              </div>
            </div>
          )}

          {/* STEP 2: Channels */}
          {step === 2 && (
            <div className="space-y-lg">
              <p className="text-darkSecondaryText text-sm leading-relaxed">
                Connect your business touchpoints to ReplyOne. You can connect multiple channels to aggregate customer conversations.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
                {/* WhatsApp Channel */}
                <div className="p-md bg-darkSidebarBg border border-darkBorder rounded-large hover:border-indigoBrand/50 transition-all flex flex-col justify-between">
                  <div className="flex items-start gap-sm mb-md">
                    <div className="p-sm bg-successGreen/10 text-successGreen rounded-default">
                      <MessageCircle size={24} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">WhatsApp Business</h3>
                      <p className="text-xs text-darkSecondaryText mt-xs">Auto-reply to customer DMs & notifications</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleConnectChannel('whatsapp')}
                    disabled={channelsConnected.whatsapp}
                    className={`w-full py-xs px-sm rounded-default text-xs font-semibold flex items-center justify-center gap-xs cursor-pointer ${
                      channelsConnected.whatsapp 
                        ? 'bg-successGreen/25 text-successGreen border border-successGreen/30'
                        : 'bg-darkBorder text-cloudWhite border border-transparent hover:bg-darkBorder/80'
                    }`}
                  >
                    {channelsConnected.whatsapp ? <CheckCircle size={14} /> : null}
                    {channelsConnected.whatsapp ? 'Connected' : 'Mock Connect'}
                  </button>
                </div>

                {/* Website Widget Channel */}
                <div className="p-md bg-darkSidebarBg border border-darkBorder rounded-large hover:border-indigoBrand/50 transition-all flex flex-col justify-between">
                  <div className="flex items-start gap-sm mb-md">
                    <div className="p-sm bg-electricBlue/10 text-electricBlue rounded-default">
                      <Code size={24} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">Website Widget</h3>
                      <p className="text-xs text-darkSecondaryText mt-xs">Add a custom live chat bubbles to your store</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleConnectChannel('website')}
                    disabled={channelsConnected.website}
                    className={`w-full py-xs px-sm rounded-default text-xs font-semibold flex items-center justify-center gap-xs cursor-pointer ${
                      channelsConnected.website 
                        ? 'bg-successGreen/25 text-successGreen border border-successGreen/30'
                        : 'bg-darkBorder text-cloudWhite border border-transparent hover:bg-darkBorder/80'
                    }`}
                  >
                    {channelsConnected.website ? <CheckCircle size={14} /> : null}
                    {channelsConnected.website ? 'Connected' : 'Mock Connect'}
                  </button>
                </div>
              </div>

              {channelsConnected.website && (
                <div className="mt-md p-md bg-darkSidebarBg border border-darkBorder rounded-large">
                  <div className="flex justify-between items-center mb-xs">
                    <span className="text-xs font-mono text-cyberTeal">Widget Snippet Code</span>
                    <button 
                      onClick={copyWidgetCode}
                      className="text-xs text-darkSecondaryText hover:text-cloudWhite flex items-center gap-xs cursor-pointer bg-transparent border-none"
                    >
                      {copied ? <Check size={12} className="text-successGreen" /> : <Copy size={12} />}
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="text-xs font-mono bg-deepNavy p-sm rounded-default overflow-x-auto text-darkSecondaryText whitespace-pre border border-darkBorder">
                    {`<!-- Paste inside <head> -->\n<script src="http://localhost:8000/static/widget.js" data-tenant="${businessSlug}"></script>`}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: AI Autopilot */}
          {step === 3 && (
            <div className="space-y-lg">
              <p className="text-darkSecondaryText text-sm leading-relaxed">
                Fine-tune the behavior of the AI Autopilot. Autopilot responds automatically to intents matching your FAQ database with high confidence.
              </p>

              <div className="space-y-md">
                {/* Confidence Threshold */}
                <div className="space-y-xs">
                  <div className="flex justify-between items-center text-sm font-semibold">
                    <span className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Confidence Threshold</span>
                    <span className="text-cyberTeal font-mono text-xs">{Math.round(confidenceThreshold * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.5"
                    max="0.95"
                    step="0.05"
                    value={confidenceThreshold}
                    onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                    className="w-full accent-cyberTeal bg-darkBorder h-2 rounded-full outline-none cursor-pointer"
                  />
                  <p className="text-[11px] text-darkSecondaryText">
                    Replies automatically only when the AI confidence matches or exceeds this threshold. Otherwise, escalates to agent queue.
                  </p>
                </div>

                {/* Tone Selector */}
                <div className="space-y-xs">
                  <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">AI Conversation Tone</label>
                  <div className="grid grid-cols-3 gap-sm">
                    {['friendly', 'balanced', 'formal'].map((tone) => (
                      <button
                        key={tone}
                        type="button"
                        onClick={() => setAiTone(tone)}
                        className={`py-md-sm px-md border rounded-default text-xs font-semibold capitalize transition-all cursor-pointer ${
                          aiTone === tone
                            ? 'bg-indigoBrand/25 border-indigoBrand text-indigoBrand shadow-md'
                            : 'bg-darkSidebarBg border-darkBorder text-darkSecondaryText hover:border-darkBorder/80'
                        }`}
                      >
                        {tone}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Launch */}
          {step === 4 && (
            <div className="text-center space-y-md py-lg">
              <div className="w-16 h-16 bg-successGreen/20 text-successGreen rounded-full flex items-center justify-center mx-auto shadow-lg animate-bounce">
                <CheckCircle size={36} />
              </div>
              <h3 className="text-xl font-bold">You are all set!</h3>
              <p className="text-darkSecondaryText text-sm max-w-md mx-auto leading-relaxed">
                Your channels are configured, your AI autopilot properties are saved, and you are ready to start automating your customer support queries.
              </p>
            </div>
          )}

        </div>

        {/* Step Navigation Footer */}
        <div className="mt-xl pt-lg border-t border-darkBorder flex justify-between">
          <button
            type="button"
            disabled={step === 1 || loading}
            onClick={() => setStep(prev => prev - 1)}
            className="py-md-sm px-md bg-darkSidebarBg hover:bg-darkBorder/30 border border-darkBorder text-cloudWhite font-semibold rounded-default text-xs transition-all flex items-center gap-xs disabled:opacity-30 disabled:pointer-events-none cursor-pointer"
          >
            <ArrowLeft size={16} />
            Back
          </button>

          {step < 4 ? (
            <button
              type="button"
              onClick={() => setStep(prev => prev + 1)}
              className="py-md-sm px-md bg-gradient-to-r from-electricBlue to-indigoBrand text-white font-semibold rounded-default text-xs shadow-md transition-all flex items-center gap-xs cursor-pointer"
            >
              Continue
              <ArrowRight size={16} />
            </button>
          ) : (
            <button
              type="button"
              disabled={loading}
              onClick={handleFinishOnboarding}
              className="py-md-sm px-lg bg-gradient-to-r from-cyberTeal to-electricBlue text-white font-bold rounded-default text-xs shadow-lg transition-all flex items-center gap-xs cursor-pointer"
            >
              {loading ? (
                <Loader2 className="animate-spin" size={16} />
              ) : (
                <>
                  Enter Dashboard
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          )}
        </div>

      </div>
    </div>
  );
};
