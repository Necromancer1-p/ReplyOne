import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area
} from 'recharts';
import { TrendingUp, MessageSquare, Bot, CheckCircle, Clock, Loader2 } from 'lucide-react';

interface KPIs {
  total_conversations: number;
  total_messages: number;
  ai_auto_replies: number;
  escalated_conversations: number;
  resolved_conversations: number;
  avg_latency_ms: number;
}

interface ChartItem {
  date: string;
  conversations: number;
  messages: number;
  auto_replies: number;
  escalations: number;
}

interface AnalyticsData {
  kpis: KPIs;
  chart_data: ChartItem[];
}

export const AnalyticsView: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const resp = await api.get<AnalyticsData>('/dashboard/analytics');
      setData(resp);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (loading && !data) {
    return (
      <div className="min-h-[calc(100vh-64px)] flex items-center justify-center bg-deepNavy text-cloudWhite">
        <Loader2 className="animate-spin text-indigoBrand" size={32} />
      </div>
    );
  }

  const kpis = data?.kpis || {
    total_conversations: 0,
    total_messages: 0,
    ai_auto_replies: 0,
    escalated_conversations: 0,
    resolved_conversations: 0,
    avg_latency_ms: 150
  };

  const chartData = data?.chart_data || [];

  // Calculate percentages
  const resolutionRate = kpis.total_conversations 
    ? Math.round((kpis.resolved_conversations / kpis.total_conversations) * 100) 
    : 0;

  const autoReplyRate = kpis.total_messages 
    ? Math.round((kpis.ai_auto_replies / kpis.total_messages) * 100) 
    : 0;

  return (
    <div className="p-lg space-y-lg bg-deepNavy min-h-[calc(100vh-64px)] overflow-y-auto text-cloudWhite">
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-xs">
          <TrendingUp className="text-electricBlue" size={24} />
          Performance & Analytics
        </h2>
        <p className="text-xs text-darkSecondaryText mt-xs">
          Monitor your customer interactions, system volumes, AI automation efficiency, and support metrics.
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-md">
        
        {/* Conversations Card */}
        <div className="bg-darkCardBg border border-darkBorder rounded-large p-md flex items-center gap-md">
          <div className="p-sm bg-electricBlue/10 text-electricBlue rounded-large">
            <MessageSquare size={24} />
          </div>
          <div>
            <span className="text-[10px] text-darkSecondaryText uppercase tracking-wider font-semibold">Total Chats</span>
            <h3 className="text-2xl font-bold font-sans mt-xs">{kpis.total_conversations}</h3>
            <p className="text-[10px] text-darkSecondaryText mt-xs">Conversations enqueued</p>
          </div>
        </div>

        {/* AI Autopilot Card */}
        <div className="bg-darkCardBg border border-darkBorder rounded-large p-md flex items-center gap-md">
          <div className="p-sm bg-cyberTeal/10 text-cyberTeal rounded-large">
            <Bot size={24} />
          </div>
          <div>
            <span className="text-[10px] text-darkSecondaryText uppercase tracking-wider font-semibold">AI Automated</span>
            <h3 className="text-2xl font-bold font-sans mt-xs">{kpis.ai_auto_replies}</h3>
            <p className="text-[10px] text-cyberTeal mt-xs font-semibold">{autoReplyRate}% automated replies</p>
          </div>
        </div>

        {/* Resolution Rate Card */}
        <div className="bg-darkCardBg border border-darkBorder rounded-large p-md flex items-center gap-md">
          <div className="p-sm bg-successGreen/10 text-successGreen rounded-large">
            <CheckCircle size={24} />
          </div>
          <div>
            <span className="text-[10px] text-darkSecondaryText uppercase tracking-wider font-semibold">Resolution Rate</span>
            <h3 className="text-2xl font-bold font-sans mt-xs">{resolutionRate}%</h3>
            <p className="text-[10px] text-darkSecondaryText mt-xs">{kpis.resolved_conversations} issues resolved</p>
          </div>
        </div>

        {/* Latency Card */}
        <div className="bg-darkCardBg border border-darkBorder rounded-large p-md flex items-center gap-md">
          <div className="p-sm bg-signalAmber/10 text-signalAmber rounded-large">
            <Clock size={24} />
          </div>
          <div>
            <span className="text-[10px] text-darkSecondaryText uppercase tracking-wider font-semibold">Avg Latency</span>
            <h3 className="text-2xl font-bold font-sans mt-xs font-mono">{kpis.avg_latency_ms}ms</h3>
            <p className="text-[10px] text-darkSecondaryText mt-xs">AI response inference speed</p>
          </div>
        </div>

      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-lg">
        
        {/* Chat Activity AreaChart */}
        <div className="bg-darkCardBg border border-darkBorder rounded-large p-md space-y-md">
          <div>
            <h4 className="font-bold text-sm text-cloudWhite">Inbound Traffic Trends</h4>
            <p className="text-[10px] text-darkSecondaryText">Daily volume of incoming chats and messages</p>
          </div>
          <div className="h-64 text-[10px] font-mono">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorMsgs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorConvs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1E6FE8" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#1E6FE8" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#2D3F56" strokeDasharray="3 3" />
                <XAxis dataKey="date" stroke="#94A3B8" />
                <YAxis stroke="#94A3B8" />
                <Tooltip contentStyle={{ backgroundColor: '#1A2940', borderColor: '#2D3F56', borderRadius: '8px' }} />
                <Legend />
                <Area type="monotone" dataKey="messages" name="Messages" stroke="#6366F1" fillOpacity={1} fill="url(#colorMsgs)" />
                <Area type="monotone" dataKey="conversations" name="Conversations" stroke="#1E6FE8" fillOpacity={1} fill="url(#colorConvs)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Efficiency BarChart */}
        <div className="bg-darkCardBg border border-darkBorder rounded-large p-md space-y-md">
          <div>
            <h4 className="font-bold text-sm text-cloudWhite">Autopilot Efficiency</h4>
            <p className="text-[10px] text-darkSecondaryText">Comparison between automated replies and ticket escalations</p>
          </div>
          <div className="h-64 text-[10px] font-mono">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid stroke="#2D3F56" strokeDasharray="3 3" />
                <XAxis dataKey="date" stroke="#94A3B8" />
                <YAxis stroke="#94A3B8" />
                <Tooltip contentStyle={{ backgroundColor: '#1A2940', borderColor: '#2D3F56', borderRadius: '8px' }} />
                <Legend />
                <Bar dataKey="auto_replies" name="Auto Replies" fill="#00C8B4" radius={[4, 4, 0, 0]} />
                <Bar dataKey="escalations" name="Escalations" fill="#EF4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
};
