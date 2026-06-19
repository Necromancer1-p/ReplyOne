import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { Settings, Save, Bot, Bell, Clock, CheckCircle, Loader2 } from 'lucide-react';

interface SettingsData {
  tenant_id: number;
  ai_tone: string;
  ai_auto_reply_enabled: boolean;
  ai_confidence_threshold: number;
  notify_email_on_escalation: boolean;
  notify_push_on_escalation: boolean;
  business_hours_json: any;
  updated_at: string;
}

export const SettingsView: React.FC = () => {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Form states
  const [aiTone, setAiTone] = useState('balanced');
  const [aiEnabled, setAiEnabled] = useState(true);
  const [threshold, setThreshold] = useState(0.70);
  const [notifyEmail, setNotifyEmail] = useState(true);
  const [notifyPush, setNotifyPush] = useState(true);

  // Business Hours
  const [businessDays, setBusinessDays] = useState<{ [key: string]: boolean }>({
    Monday: true, Tuesday: true, Wednesday: true, Thursday: true, Friday: true, Saturday: false, Sunday: false
  });
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('18:00');

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await api.get<SettingsData>('/dashboard/settings');
      setSettings(data);
      setAiTone(data.ai_tone);
      setAiEnabled(data.ai_auto_reply_enabled);
      setThreshold(data.ai_confidence_threshold);
      setNotifyEmail(data.notify_email_on_escalation);
      setNotifyPush(data.notify_push_on_escalation);

      if (data.business_hours_json) {
        const bh = data.business_hours_json;
        if (bh.days) setBusinessDays(bh.days);
        if (bh.start) setStartTime(bh.start);
        if (bh.end) setEndTime(bh.end);
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);

    try {
      const hoursPayload = {
        days: businessDays,
        start: startTime,
        end: endTime
      };

      const updated = await api.put<SettingsData>('/dashboard/settings', {
        ai_tone: aiTone,
        ai_auto_reply_enabled: aiEnabled,
        ai_confidence_threshold: threshold,
        notify_email_on_escalation: notifyEmail,
        notify_push_on_escalation: notifyPush,
        business_hours_json: hoursPayload
      });

      setSettings(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDayToggle = (day: string) => {
    setBusinessDays(prev => ({ ...prev, [day]: !prev[day] }));
  };

  if (loading && !settings) {
    return (
      <div className="min-h-[calc(100vh-64px)] flex items-center justify-center bg-deepNavy text-cloudWhite">
        <Loader2 className="animate-spin text-indigoBrand" size={32} />
      </div>
    );
  }

  return (
    <div className="p-lg space-y-lg bg-deepNavy min-h-[calc(100vh-64px)] overflow-y-auto text-cloudWhite">
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-xs">
          <Settings className="text-electricBlue" size={24} />
          Settings Panel
        </h2>
        <p className="text-xs text-darkSecondaryText mt-xs">
          Configure notification thresholds, customer experience guidelines, business operation schedules, and AI engine tones.
        </p>
      </div>

      {saveSuccess && (
        <div className="p-md bg-successGreen/15 border border-successGreen/30 text-successGreen rounded-default text-xs flex items-center gap-xs">
          <CheckCircle size={16} /> Settings saved successfully!
        </div>
      )}

      <form onSubmit={handleSaveSettings} className="grid grid-cols-1 lg:grid-cols-2 gap-lg text-xs">
        
        {/* Left Column: AI Engine */}
        <div className="space-y-lg bg-darkCardBg border border-darkBorder rounded-large p-md">
          <h3 className="text-sm font-bold border-b border-darkBorder pb-xs text-cloudWhite flex items-center gap-xs">
            <Bot className="text-cyberTeal" size={16} />
            AI Autopilot Preferences
          </h3>

          <div className="space-y-md">
            {/* Auto Reply Enable */}
            <div className="flex justify-between items-center bg-deepNavy/40 p-md rounded-large border border-darkBorder/40">
              <div>
                <h4 className="font-semibold text-sm">Autopilot Auto-Reply</h4>
                <p className="text-xs text-darkSecondaryText mt-[2px]">Allow AI to respond to incoming DMs automatically</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={aiEnabled} 
                  onChange={(e) => setAiEnabled(e.target.checked)} 
                  className="sr-only peer cursor-pointer" 
                />
                <div className="w-11 h-6 bg-darkBorder peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-cloudWhite after:border-softSlate after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyberTeal"></div>
              </label>
            </div>

            {/* AI Confidence slider */}
            <div className="space-y-xs">
              <div className="flex justify-between items-center text-sm font-semibold">
                <span className="text-darkSecondaryText font-semibold">Confidence Threshold</span>
                <span className="text-cyberTeal font-mono">{Math.round(threshold * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.50"
                max="0.95"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full accent-cyberTeal bg-darkBorder h-2 rounded-full outline-none cursor-pointer"
              />
              <p className="text-[10px] text-darkSecondaryText leading-relaxed">
                Threshold for auto-replies. Messages classified below this confidence level are enqueued as pending for human agents.
              </p>
            </div>

            {/* Tone Dropdown */}
            <div className="space-y-xs">
              <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">AI Conversation Tone</label>
              <div className="grid grid-cols-3 gap-sm">
                {['friendly', 'balanced', 'formal'].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setAiTone(t)}
                    className={`py-md-sm px-md border rounded-default text-xs font-semibold capitalize transition-all cursor-pointer ${
                      aiTone === t
                        ? 'bg-indigoBrand/20 border-indigoBrand text-indigoBrand shadow-md'
                        : 'bg-darkSidebarBg border-darkBorder text-darkSecondaryText hover:border-darkBorder/80'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Notifications & Business Hours */}
        <div className="space-y-lg flex flex-col justify-between">
          {/* Notifications Panel */}
          <div className="space-y-lg bg-darkCardBg border border-darkBorder rounded-large p-md">
            <h3 className="text-sm font-bold border-b border-darkBorder pb-xs text-cloudWhite flex items-center gap-xs">
              <span className="text-alertRed"><Bell size={16} /></span>
              Escalation Notifications
            </h3>

            <div className="space-y-md">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="font-semibold text-sm">Email Alerts</h4>
                  <p className="text-xs text-darkSecondaryText mt-[2px]">Notify owner on urgent customer escalations</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={notifyEmail} 
                    onChange={(e) => setNotifyEmail(e.target.checked)} 
                    className="sr-only peer cursor-pointer" 
                  />
                  <div className="w-11 h-6 bg-darkBorder peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-cloudWhite after:border-softSlate after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-electricBlue"></div>
                </label>
              </div>

              <div className="flex justify-between items-center">
                <div>
                  <h4 className="font-semibold text-sm">Browser Push Alerts</h4>
                  <p className="text-xs text-darkSecondaryText mt-[2px]">Send immediate desktop browser alerts for manual takeover</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={notifyPush} 
                    onChange={(e) => setNotifyPush(e.target.checked)} 
                    className="sr-only peer cursor-pointer" 
                  />
                  <div className="w-11 h-6 bg-darkBorder peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-cloudWhite after:border-softSlate after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-electricBlue"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Business Hours Panel */}
          <div className="space-y-lg bg-darkCardBg border border-darkBorder rounded-large p-md">
            <h3 className="text-sm font-bold border-b border-darkBorder pb-xs text-cloudWhite flex items-center gap-xs">
              <Clock className="text-signalAmber" size={16} />
              Business Operations Schedule
            </h3>

            <div className="space-y-md">
              <div className="space-y-xs">
                <span className="text-[10px] uppercase font-bold text-darkSecondaryText">Select Active Days</span>
                <div className="flex gap-xs flex-wrap">
                  {Object.keys(businessDays).map((day) => {
                    const active = businessDays[day];
                    return (
                      <button
                        key={day}
                        type="button"
                        onClick={() => handleDayToggle(day)}
                        className={`px-sm py-xs border rounded-default text-[10px] font-semibold transition-all cursor-pointer ${
                          active
                            ? 'bg-electricBlue/20 border-electricBlue text-electricBlue'
                            : 'bg-darkSidebarBg border-darkBorder text-darkSecondaryText hover:text-cloudWhite'
                        }`}
                      >
                        {day.substring(0, 3)}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-md">
                <div className="space-y-xs">
                  <span className="text-[10px] uppercase font-bold text-darkSecondaryText">Start Time</span>
                  <input
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="w-full px-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite focus:outline-none focus:border-electricBlue text-sm font-mono cursor-pointer"
                  />
                </div>
                <div className="space-y-xs">
                  <span className="text-[10px] uppercase font-bold text-darkSecondaryText">End Time</span>
                  <input
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="w-full px-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite focus:outline-none focus:border-electricBlue text-sm font-mono cursor-pointer"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Global Save Button */}
        <div className="lg:col-span-2 flex justify-end pt-md border-t border-darkBorder/40">
          <button
            type="submit"
            disabled={saving}
            className="py-md-sm px-lg bg-gradient-to-r from-electricBlue to-indigoBrand text-white font-bold rounded-default shadow hover:from-electricBlue/95 hover:to-indigoBrand/95 active:scale-[0.98] transition-all flex items-center justify-center gap-xs disabled:opacity-50 cursor-pointer border-none text-xs"
          >
            {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
            Save Configuration Changes
          </button>
        </div>

      </form>
    </div>
  );
};
