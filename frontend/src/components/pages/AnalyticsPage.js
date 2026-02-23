import React, { useState, useEffect } from 'react';
import { 
  BarChart3, TrendingUp, TrendingDown, Clock, Users, 
  TicketIcon, CheckCircle2, AlertCircle, Target,
  ArrowUpRight, ArrowDownRight, Loader2, Calendar,
  PieChart, Activity, Zap, Star, MessageSquareHeart
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const StatCard = ({ title, value, subValue, icon: Icon, trend, trendValue, color = "primary" }) => {
  const colorClasses = {
    primary: "from-primary/20 to-primary/5 border-primary/20",
    success: "from-emerald-500/20 to-emerald-500/5 border-emerald-500/20",
    warning: "from-amber-500/20 to-amber-500/5 border-amber-500/20",
    danger: "from-red-500/20 to-red-500/5 border-red-500/20",
    info: "from-blue-500/20 to-blue-500/5 border-blue-500/20"
  };
  
  const iconColors = {
    primary: "text-primary",
    success: "text-emerald-400",
    warning: "text-amber-400",
    danger: "text-red-400",
    info: "text-blue-400"
  };
  
  return (
    <div className={`p-5 rounded-xl bg-gradient-to-br ${colorClasses[color]} border backdrop-blur-sm`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</p>
          <p className="text-3xl font-bold mt-2">{value}</p>
          {subValue && (
            <p className="text-sm text-muted-foreground mt-1">{subValue}</p>
          )}
        </div>
        <div className={`p-3 rounded-xl bg-background/50 ${iconColors[color]}`}>
          <Icon size={24} />
        </div>
      </div>
      {trend !== undefined && (
        <div className={`flex items-center gap-1 mt-3 text-sm ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {trend >= 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
          <span>{Math.abs(trend)}% {trendValue || 'vs last period'}</span>
        </div>
      )}
    </div>
  );
};

const MiniBarChart = ({ data, height = 120 }) => {
  if (!data || data.length === 0) return null;
  
  const maxValue = Math.max(...data.map(d => d.count), 1);
  
  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {data.slice(-14).map((item, index) => (
        <div
          key={index}
          className="flex-1 group relative"
        >
          <div
            className="w-full bg-primary/60 rounded-t transition-all hover:bg-primary"
            style={{ height: `${(item.count / maxValue) * 100}%`, minHeight: item.count > 0 ? '4px' : '0' }}
          />
          <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
            <div className="bg-popover border border-border rounded px-2 py-1 text-xs whitespace-nowrap shadow-lg">
              <div className="font-medium">{item.count} tickets</div>
              <div className="text-muted-foreground">{item.date}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

const PriorityBar = ({ priority, count, total, color }) => {
  const percentage = total > 0 ? (count / total) * 100 : 0;
  
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-medium w-16 capitalize">{priority}</span>
      <div className="flex-1 h-2 bg-secondary/30 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground w-8 text-right">{count}</span>
    </div>
  );
};

const AgentCard = ({ agent, rank }) => {
  const rankColors = {
    1: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    2: 'bg-slate-400/20 text-slate-300 border-slate-400/30',
    3: 'bg-amber-600/20 text-amber-500 border-amber-600/30'
  };
  
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/20 border border-border/30 hover:bg-secondary/30 transition-colors">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border ${rankColors[rank] || 'bg-secondary/30 text-muted-foreground border-border/30'}`}>
        {rank}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{agent.name}</p>
        <p className="text-xs text-muted-foreground">{agent.tickets_resolved} resolved</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-medium text-emerald-400">{agent.resolution_rate}%</p>
        <p className="text-xs text-muted-foreground">rate</p>
      </div>
    </div>
  );
};

const AnalyticsPage = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [agents, setAgents] = useState([]);
  const [csatAnalytics, setCsatAnalytics] = useState(null);
  const [period, setPeriod] = useState(30);
  
  useEffect(() => {
    fetchAnalytics();
  }, [period]);
  
  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [overviewRes, agentsRes, csatRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/analytics/overview?days=${period}`, { credentials: 'include' }),
        fetch(`${BACKEND_URL}/api/analytics/agents?days=${period}`, { credentials: 'include' }),
        fetch(`${BACKEND_URL}/api/csat/analytics?days=${period}`, { credentials: 'include' })
      ]);
      
      if (overviewRes.ok) {
        setOverview(await overviewRes.json());
      }
      if (agentsRes.ok) {
        const agentsData = await agentsRes.json();
        setAgents(agentsData.agents || []);
      }
      if (csatRes.ok) {
        setCsatAnalytics(await csatRes.json());
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-primary" size={48} />
      </div>
    );
  }
  
  const summary = overview?.summary || {};
  const priorityTotal = Object.values(overview?.priority_breakdown || {}).reduce((a, b) => a + b, 0);
  
  return (
    <div className="p-6 space-y-6" data-testid="analytics-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-3">
            <BarChart3 className="text-primary" />
            Analytics Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Monitor team performance and ticket metrics
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(Number(e.target.value))}
            className="h-10 px-4 rounded-lg bg-secondary/30 border border-border/30 focus:outline-none focus:ring-2 focus:ring-primary/50"
            data-testid="analytics-period-select"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Tickets"
          value={summary.total_tickets || 0}
          subValue={`${summary.tickets_in_period || 0} in last ${period} days`}
          icon={TicketIcon}
          color="primary"
        />
        <StatCard
          title="Open Tickets"
          value={summary.open_tickets || 0}
          subValue="Requiring attention"
          icon={AlertCircle}
          color="warning"
        />
        <StatCard
          title="Resolved"
          value={summary.resolved_in_period || 0}
          subValue={`In last ${period} days`}
          icon={CheckCircle2}
          color="success"
        />
        <StatCard
          title="Avg Resolution"
          value={summary.avg_resolution_hours ? `${summary.avg_resolution_hours}h` : '-'}
          subValue="Time to resolve"
          icon={Clock}
          color="info"
        />
      </div>
      
      {/* SLA & Volume Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SLA Compliance */}
        <div className="p-5 rounded-xl bg-card border border-border/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2">
              <Target size={18} className="text-primary" />
              SLA Compliance
            </h3>
          </div>
          
          <div className="flex items-center justify-center py-6">
            <div className="relative">
              <svg className="w-32 h-32 transform -rotate-90">
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="12"
                  className="text-secondary/30"
                />
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="12"
                  strokeDasharray={`${(summary.sla_compliance_percent || 0) * 3.52} 352`}
                  strokeLinecap="round"
                  className={summary.sla_compliance_percent >= 90 ? 'text-emerald-400' : summary.sla_compliance_percent >= 70 ? 'text-amber-400' : 'text-red-400'}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center flex-col">
                <span className="text-3xl font-bold">
                  {summary.sla_compliance_percent ? `${summary.sla_compliance_percent}%` : '-'}
                </span>
                <span className="text-xs text-muted-foreground">compliance</span>
              </div>
            </div>
          </div>
          
          <p className="text-center text-sm text-muted-foreground">
            Based on 24h resolution target
          </p>
        </div>
        
        {/* Volume Trend */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-card border border-border/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2">
              <Activity size={18} className="text-primary" />
              Ticket Volume Trend
            </h3>
            <span className="text-xs text-muted-foreground">Last {period} days</span>
          </div>
          
          <MiniBarChart data={overview?.volume_trend || []} height={140} />
          
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/30 text-sm">
            <span className="text-muted-foreground">
              Total: <span className="font-medium text-foreground">{summary.tickets_in_period || 0}</span> tickets
            </span>
            <span className="text-muted-foreground">
              Avg: <span className="font-medium text-foreground">
                {summary.tickets_in_period ? Math.round(summary.tickets_in_period / period) : 0}
              </span> /day
            </span>
          </div>
        </div>
      </div>
      
      {/* Priority & Agents Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Priority Breakdown */}
        <div className="p-5 rounded-xl bg-card border border-border/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2">
              <Zap size={18} className="text-primary" />
              Open by Priority
            </h3>
            <span className="text-xs text-muted-foreground">{priorityTotal} open</span>
          </div>
          
          <div className="space-y-3">
            <PriorityBar 
              priority="urgent" 
              count={overview?.priority_breakdown?.urgent || 0} 
              total={priorityTotal}
              color="bg-red-500"
            />
            <PriorityBar 
              priority="high" 
              count={overview?.priority_breakdown?.high || 0} 
              total={priorityTotal}
              color="bg-orange-500"
            />
            <PriorityBar 
              priority="medium" 
              count={overview?.priority_breakdown?.medium || 0} 
              total={priorityTotal}
              color="bg-yellow-500"
            />
            <PriorityBar 
              priority="low" 
              count={overview?.priority_breakdown?.low || 0} 
              total={priorityTotal}
              color="bg-green-500"
            />
          </div>
          
          {/* Status breakdown */}
          <div className="mt-6 pt-4 border-t border-border/30">
            <h4 className="text-sm font-medium text-muted-foreground mb-3">Status Distribution</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(overview?.status_breakdown || {}).map(([status, count]) => (
                <div key={status} className="px-3 py-1.5 rounded-lg bg-secondary/30 border border-border/30">
                  <span className="text-xs text-muted-foreground capitalize">{status.replace('_', ' ')}</span>
                  <span className="text-sm font-medium ml-2">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* Top Agents */}
        <div className="p-5 rounded-xl bg-card border border-border/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2">
              <Users size={18} className="text-primary" />
              Top Performers
            </h3>
            <span className="text-xs text-muted-foreground">By resolution rate</span>
          </div>
          
          <div className="space-y-2">
            {agents.slice(0, 5).map((agent, index) => (
              <AgentCard key={agent.user_id} agent={agent} rank={index + 1} />
            ))}
            
            {agents.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <Users size={32} className="mx-auto mb-2 opacity-30" />
                <p>No agent data available</p>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Agent Performance Table */}
      {agents.length > 0 && (
        <div className="p-5 rounded-xl bg-card border border-border/50">
          <h3 className="font-semibold flex items-center gap-2 mb-4">
            <BarChart3 size={18} className="text-primary" />
            Agent Performance Details
          </h3>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border/30">
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground uppercase">Agent</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-muted-foreground uppercase">Assigned</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-muted-foreground uppercase">Resolved</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-muted-foreground uppercase">Rate</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-muted-foreground uppercase">Avg Time</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-muted-foreground uppercase">Urgent</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-muted-foreground uppercase">High</th>
                </tr>
              </thead>
              <tbody>
                {agents.map(agent => (
                  <tr key={agent.user_id} className="border-b border-border/20 hover:bg-secondary/20">
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium">{agent.name}</p>
                        <p className="text-xs text-muted-foreground">{agent.email}</p>
                      </div>
                    </td>
                    <td className="text-right py-3 px-4 font-medium">{agent.tickets_assigned}</td>
                    <td className="text-right py-3 px-4 font-medium text-emerald-400">{agent.tickets_resolved}</td>
                    <td className="text-right py-3 px-4">
                      <span className={`font-medium ${agent.resolution_rate >= 80 ? 'text-emerald-400' : agent.resolution_rate >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                        {agent.resolution_rate}%
                      </span>
                    </td>
                    <td className="text-right py-3 px-4 text-muted-foreground">
                      {agent.avg_resolution_hours ? `${agent.avg_resolution_hours}h` : '-'}
                    </td>
                    <td className="text-right py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs">
                        {agent.priority_breakdown?.urgent || 0}
                      </span>
                    </td>
                    <td className="text-right py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-orange-500/20 text-orange-400 text-xs">
                        {agent.priority_breakdown?.high || 0}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      
      {/* CSAT Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CSAT Overview */}
        <div className="p-5 rounded-xl bg-card border border-border/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2">
              <MessageSquareHeart size={18} className="text-primary" />
              Customer Satisfaction (CSAT)
            </h3>
            <span className="text-xs text-muted-foreground">
              {csatAnalytics?.total_responses || 0} responses
            </span>
          </div>
          
          {csatAnalytics?.total_responses > 0 ? (
            <>
              {/* Average Rating */}
              <div className="text-center py-6">
                <div className="flex items-center justify-center gap-1 mb-2">
                  {[1, 2, 3, 4, 5].map(star => (
                    <Star
                      key={star}
                      size={28}
                      className={star <= Math.round(csatAnalytics?.average_rating || 0)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'fill-transparent text-gray-400'
                      }
                    />
                  ))}
                </div>
                <p className="text-3xl font-bold">{csatAnalytics?.average_rating || '-'}</p>
                <p className="text-sm text-muted-foreground">Average Rating</p>
              </div>
              
              {/* Rating Distribution */}
              <div className="space-y-2 mb-4">
                {[5, 4, 3, 2, 1].map(rating => {
                  const count = csatAnalytics?.rating_distribution?.[rating] || 0;
                  const total = csatAnalytics?.total_responses || 1;
                  const percentage = (count / total) * 100;
                  
                  return (
                    <div key={rating} className="flex items-center gap-2">
                      <span className="text-xs w-8">{rating} ⭐</span>
                      <div className="flex-1 h-2 bg-secondary/30 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            rating >= 4 ? 'bg-emerald-500' : 
                            rating >= 3 ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-8 text-right">{count}</span>
                    </div>
                  );
                })}
              </div>
              
              {/* Satisfaction Rate */}
              <div className="p-3 rounded-lg bg-secondary/20 text-center">
                <p className={`text-2xl font-bold ${
                  (csatAnalytics?.satisfaction_rate || 0) >= 80 ? 'text-emerald-400' :
                  (csatAnalytics?.satisfaction_rate || 0) >= 60 ? 'text-amber-400' : 'text-red-400'
                }`}>
                  {csatAnalytics?.satisfaction_rate || 0}%
                </p>
                <p className="text-xs text-muted-foreground">Satisfaction Rate (4-5 stars)</p>
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <MessageSquareHeart size={32} className="mx-auto mb-2 opacity-30" />
              <p>No CSAT responses yet</p>
              <p className="text-xs mt-1">Send surveys after resolving tickets</p>
            </div>
          )}
        </div>
        
        {/* Low Ratings / Alerts */}
        <div className="p-5 rounded-xl bg-card border border-border/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2">
              <AlertCircle size={18} className="text-red-400" />
              Low Ratings Alerts
            </h3>
            <span className="text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400">
              {csatAnalytics?.low_ratings?.length || 0} alerts
            </span>
          </div>
          
          {csatAnalytics?.low_ratings?.length > 0 ? (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {csatAnalytics.low_ratings.map((item, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-red-500/5 border border-red-500/20">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-muted-foreground">{item.ticket_id}</span>
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map(star => (
                        <Star
                          key={star}
                          size={12}
                          className={star <= item.rating
                            ? 'fill-red-400 text-red-400'
                            : 'fill-transparent text-gray-500'
                          }
                        />
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {item.customer_email}
                    {item.resolved_by_name && ` → ${item.resolved_by_name}`}
                  </p>
                  {item.feedback && (
                    <p className="text-xs text-red-300 mt-1 italic">&ldquo;{item.feedback}&rdquo;</p>
                  )}
                  <p className="text-[10px] text-muted-foreground/60 mt-1">
                    {new Date(item.created_at).toLocaleString('en-US', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <CheckCircle2 size={32} className="mx-auto mb-2 text-emerald-400/30" />
              <p className="text-emerald-400">No low ratings!</p>
              <p className="text-xs mt-1">All customers are satisfied</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;
