import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  Calendar, Plus, ChevronLeft, ChevronRight, X, 
  AlertTriangle, Clock, Trash2, Edit2, BarChart3,
  Users, TrendingUp, PieChart, Wifi, WifiOff
} from 'lucide-react';

import { useRealtime } from '../contexts/RealtimeContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 
                'July', 'August', 'September', 'October', 'November', 'December'];

// Chart colors for leave types
const TYPE_COLORS = {
  'Sick Leave': '#ef4444',
  'Vacation': '#3b82f6',
  'Personal': '#8b5cf6',
  'Work from Home': '#10b981',
  'Other': '#6b7280',
};

const getTypeColor = (type) => {
  return TYPE_COLORS[type] || `hsl(${Math.abs(type.charCodeAt(0) * 40) % 360}, 70%, 50%)`;
};

const LeavePage = ({ user }) => {
  const [searchParams] = useSearchParams();
  const { onLeaveUpdate, isConnected } = useRealtime();
  const [leaves, setLeaves] = useState([]);
  const [calendar, setCalendar] = useState([]);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingLeave, setEditingLeave] = useState(null);
  const [conflicts, setConflicts] = useState(null);
  const [activeTab, setActiveTab] = useState('calendar'); // 'calendar' | 'summary'
  const [summaryData, setSummaryData] = useState({});
  
  // Calendar navigation
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth() + 1);
  
  // Form state
  const [formData, setFormData] = useState({
    user_id: '',
    leave_type: '',
    start_date: '',
    end_date: '',
    reason: '',
    is_half_day: false,
    half_day_type: null
  });

  const fetchLeaves = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/leaves`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setLeaves(data);
      }
    } catch (error) {
      console.error('Failed to fetch leaves:', error);
    }
  }, []);

  const fetchCalendar = useCallback(async () => {
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/leaves/calendar/${viewYear}/${viewMonth}`,
        { credentials: 'include' }
      );
      if (response.ok) {
        const data = await response.json();
        setCalendar(data.days || []);
      }
    } catch (error) {
      console.error('Failed to fetch calendar:', error);
    }
  }, [viewYear, viewMonth]);

  const fetchLeaveTypes = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/leaves/types`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setLeaveTypes(data.types || []);
      }
    } catch (error) {
      console.error('Failed to fetch leave types:', error);
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  }, []);

  const fetchAllSummaries = useCallback(async () => {
    // Fetch summary for all users
    const summaries = {};
    for (const u of users) {
      try {
        const response = await fetch(
          `${BACKEND_URL}/api/leaves/summary/${u.user_id || u.id}?year=${viewYear}`,
          { credentials: 'include' }
        );
        if (response.ok) {
          const data = await response.json();
          summaries[u.user_id || u.id] = data;
        }
      } catch (error) {
        console.error('Failed to fetch summary:', error);
      }
    }
    setSummaryData(summaries);
  }, [users, viewYear]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchLeaves(), fetchCalendar(), fetchLeaveTypes(), fetchUsers()]);
      setLoading(false);
    };
    loadData();
  }, [fetchLeaves, fetchCalendar, fetchLeaveTypes, fetchUsers]);

  // Real-time updates subscription
  useEffect(() => {
    if (!onLeaveUpdate) return;
    
    const unsubscribe = onLeaveUpdate((data) => {
      // Refresh data on any leave event
      fetchLeaves();
      fetchCalendar();
      
      // Handle real-time updates (from other users)
      const currentUserId = user?.user_id;
      const eventUserId = data.created_by?.user_id || data.updated_by?.user_id || data.deleted_by?.user_id;
      
      if (eventUserId && eventUserId !== currentUserId) {
        // Silent update - no notification needed
        console.log('Leave update from another user');
      }
    });
    
    return unsubscribe;
  }, [onLeaveUpdate, fetchLeaves, fetchCalendar, user]);

  useEffect(() => {
    fetchCalendar();
  }, [viewYear, viewMonth, fetchCalendar]);

  useEffect(() => {
    if (users.length > 0 && activeTab === 'summary') {
      fetchAllSummaries();
    }
  }, [users, activeTab, fetchAllSummaries]);

  const checkConflicts = async (startDate, endDate) => {
    if (!startDate || !endDate) return;
    try {
      const excludeUser = editingLeave ? editingLeave.user_id : (formData.user_id || user?.user_id);
      const response = await fetch(
        `${BACKEND_URL}/api/leaves/conflicts?start_date=${startDate}&end_date=${endDate}&exclude_user_id=${excludeUser}`,
        { credentials: 'include' }
      );
      if (response.ok) {
        const data = await response.json();
        setConflicts(data);
      }
    } catch (error) {
      console.error('Failed to check conflicts:', error);
    }
  };

  useEffect(() => {
    if (formData.start_date && formData.end_date) {
      checkConflicts(formData.start_date, formData.end_date);
    }
  }, [formData.start_date, formData.end_date]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const payload = {
      ...formData,
      user_id: formData.user_id || user?.user_id
    };
    
    try {
      const url = editingLeave 
        ? `${BACKEND_URL}/api/leaves/${editingLeave.id}`
        : `${BACKEND_URL}/api/leaves`;
      
      const response = await fetch(url, {
        method: editingLeave ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        // Success
        setShowModal(false);
        resetForm();
        fetchLeaves();
        fetchCalendar();
      } else {
        const error = await response.json();
        console.error('Operation failed');
      }
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const handleEdit = (leave) => {
    setEditingLeave(leave);
    setFormData({
      user_id: leave.user_id,
      leave_type: leave.leave_type,
      start_date: leave.start_date,
      end_date: leave.end_date,
      reason: leave.reason || '',
      is_half_day: leave.is_half_day || false,
      half_day_type: leave.half_day_type || null
    });
    setShowModal(true);
  };

  const handleDelete = async (leaveId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/leaves/${leaveId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        // Success
        fetchLeaves();
        fetchCalendar();
      }
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const handleStatusChange = async (leaveId, newStatus) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/leaves/${leaveId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ status: newStatus })
      });
      
      if (response.ok) {
        // Success
        fetchLeaves();
        fetchCalendar();
      }
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const resetForm = () => {
    setFormData({
      user_id: '',
      leave_type: '',
      start_date: '',
      end_date: '',
      reason: '',
      is_half_day: false,
      half_day_type: null
    });
    setConflicts(null);
    setEditingLeave(null);
  };

  const openModalForDate = (date) => {
    resetForm();
    setFormData(prev => ({
      ...prev,
      start_date: date,
      end_date: date
    }));
    setShowModal(true);
  };

  const navigateMonth = (delta) => {
    let newMonth = viewMonth + delta;
    let newYear = viewYear;
    
    if (newMonth > 12) {
      newMonth = 1;
      newYear++;
    } else if (newMonth < 1) {
      newMonth = 12;
      newYear--;
    }
    
    setViewMonth(newMonth);
    setViewYear(newYear);
  };

  // Generate calendar grid
  const calendarGrid = useMemo(() => {
    const firstDay = new Date(viewYear, viewMonth - 1, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth, 0).getDate();
    const grid = [];
    
    for (let i = 0; i < firstDay; i++) {
      grid.push({ empty: true, index: `empty-${i}` });
    }
    
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${viewYear}-${String(viewMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const calendarDay = calendar.find(d => d.date === dateStr);
      grid.push({
        day,
        date: dateStr,
        ...calendarDay,
        isToday: dateStr === today.toISOString().split('T')[0]
      });
    }
    
    return grid;
  }, [viewYear, viewMonth, calendar, today]);

  // Summary statistics
  const summaryStats = useMemo(() => {
    const currentYear = viewYear;
    const yearLeaves = leaves.filter(l => l.start_date?.startsWith(currentYear));
    
    // By type
    const byType = {};
    yearLeaves.forEach(l => {
      if (!byType[l.leave_type]) byType[l.leave_type] = { count: 0, days: 0 };
      byType[l.leave_type].count++;
      byType[l.leave_type].days += l.days_count || 1;
    });
    
    // By user
    const byUser = {};
    yearLeaves.forEach(l => {
      const userName = l.user_name || 'Unknown';
      if (!byUser[userName]) byUser[userName] = { count: 0, days: 0 };
      byUser[userName].count++;
      byUser[userName].days += l.days_count || 1;
    });
    
    // By month
    const byMonth = Array(12).fill(0);
    yearLeaves.forEach(l => {
      const month = parseInt(l.start_date?.split('-')[1]) - 1;
      if (month >= 0 && month < 12) byMonth[month] += l.days_count || 1;
    });
    
    const totalDays = yearLeaves.reduce((sum, l) => sum + (l.days_count || 1), 0);
    
    return { byType, byUser, byMonth, totalDays, totalLeaves: yearLeaves.length };
  }, [leaves, viewYear]);

  const getConflictColor = (level) => {
    switch (level) {
      case 'high': return 'bg-red-500/20 border-red-500/50';
      case 'medium': return 'bg-amber-500/20 border-amber-500/50';
      case 'low': return 'bg-emerald-500/20 border-emerald-500/50';
      default: return '';
    }
  };

  const upcomingLeaves = useMemo(() => {
    const todayStr = today.toISOString().split('T')[0];
    return leaves
      .filter(l => l.status === 'approved' && l.start_date >= todayStr)
      .sort((a, b) => a.start_date.localeCompare(b.start_date))
      .slice(0, 10);
  }, [leaves, today]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
        <div className="px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Calendar className="text-primary" size={20} />
            <h1 className="text-lg font-semibold">Leave Management</h1>
            
            {/* Tab Switcher */}
            <div className="flex items-center bg-secondary/50 rounded-lg p-1 ml-4">
              <button
                onClick={() => setActiveTab('calendar')}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'calendar' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Calendar size={14} className="inline mr-1.5" />
                Calendar
              </button>
              <button
                onClick={() => setActiveTab('summary')}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'summary' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <BarChart3 size={14} className="inline mr-1.5" />
                Summary
              </button>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Connection Status */}
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs ${
              isConnected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
            }`}>
              {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
              <span>{isConnected ? 'Live' : 'Offline'}</span>
            </div>
            
            <button
              onClick={() => { resetForm(); setShowModal(true); }}
              className="flex items-center gap-2 h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
              data-testid="add-leave-btn"
            >
              <Plus size={16} />
              Add Leave
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === 'calendar' ? (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Team Calendar */}
            <div className="xl:col-span-2 glass rounded-xl border border-border/60 p-4">
              {/* Calendar Header */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">{MONTHS[viewMonth - 1]} {viewYear}</h2>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigateMonth(-1)}
                    className="p-2 rounded-lg hover:bg-secondary/50 transition-colors"
                  >
                    <ChevronLeft size={18} />
                  </button>
                  <button
                    onClick={() => { setViewMonth(today.getMonth() + 1); setViewYear(today.getFullYear()); }}
                    className="px-3 py-1.5 text-sm rounded-lg hover:bg-secondary/50 transition-colors"
                  >
                    Today
                  </button>
                  <button
                    onClick={() => navigateMonth(1)}
                    className="p-2 rounded-lg hover:bg-secondary/50 transition-colors"
                  >
                    <ChevronRight size={18} />
                  </button>
                </div>
              </div>

              {/* Weekday Headers */}
              <div className="grid grid-cols-7 mb-2">
                {WEEKDAYS.map(day => (
                  <div key={day} className="text-center text-xs font-medium text-muted-foreground py-2">
                    {day}
                  </div>
                ))}
              </div>

              {/* Calendar Grid */}
              <div className="grid grid-cols-7 gap-1">
                {calendarGrid.map((cell, idx) => (
                  <div
                    key={cell.index || cell.date || idx}
                    onClick={() => !cell.empty && openModalForDate(cell.date)}
                    className={`
                      min-h-[80px] p-1.5 rounded-lg border cursor-pointer transition-all
                      ${cell.empty ? 'bg-transparent border-transparent' : 'hover:border-primary/50'}
                      ${cell.isToday ? 'ring-2 ring-primary/50' : ''}
                      ${cell.is_weekend ? 'bg-secondary/20' : 'bg-secondary/5'}
                      ${cell.conflict_level ? getConflictColor(cell.conflict_level) : 'border-border/30'}
                    `}
                    data-testid={`calendar-day-${cell.date}`}
                  >
                    {!cell.empty && (
                      <>
                        <div className={`text-xs font-medium mb-1 ${cell.isToday ? 'text-primary' : ''}`}>
                          {cell.day}
                        </div>
                        {cell.leaves && cell.leaves.length > 0 && (
                          <div className="space-y-0.5">
                            {cell.leaves.slice(0, 3).map((leave, i) => (
                              <div
                                key={i}
                                className="text-[9px] px-1 py-0.5 rounded truncate"
                                style={{ backgroundColor: `${getTypeColor(leave.leave_type)}20`, color: getTypeColor(leave.leave_type) }}
                                title={`${leave.user_name} - ${leave.leave_type}`}
                              >
                                {leave.user_name?.split(' ')[0]}
                              </div>
                            ))}
                            {cell.leaves.length > 3 && (
                              <div className="text-[9px] text-muted-foreground">
                                +{cell.leaves.length - 3} more
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>

              {/* Legend */}
              <div className="flex items-center gap-4 mt-4 pt-4 border-t border-border/30">
                <span className="text-xs text-muted-foreground">Conflict level:</span>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-emerald-500/30 border border-emerald-500/50" />
                  <span className="text-xs">Low (1)</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-amber-500/30 border border-amber-500/50" />
                  <span className="text-xs">Medium (2)</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded bg-red-500/30 border border-red-500/50" />
                  <span className="text-xs">High (3+)</span>
                </div>
              </div>
            </div>

            {/* Upcoming Leaves */}
            <div className="glass rounded-xl border border-border/60 p-4">
              <h2 className="text-lg font-semibold mb-4">Upcoming Leaves</h2>
              
              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {upcomingLeaves.map(leave => (
                  <div
                    key={leave.id}
                    className="p-3 rounded-lg bg-secondary/30 border border-border/30 group"
                    data-testid={`leave-card-${leave.id}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium"
                          style={{ backgroundColor: `${getTypeColor(leave.leave_type)}20`, color: getTypeColor(leave.leave_type) }}
                        >
                          {leave.user_name?.charAt(0) || 'U'}
                        </div>
                        <span className="font-medium text-sm">{leave.user_name}</span>
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => handleEdit(leave)}
                          className="p-1.5 rounded hover:bg-secondary transition-colors"
                          title="Edit"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(leave.id)}
                          className="p-1.5 rounded hover:bg-destructive/20 hover:text-destructive transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div className="flex items-center gap-2">
                        <span 
                          className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                          style={{ backgroundColor: `${getTypeColor(leave.leave_type)}20`, color: getTypeColor(leave.leave_type) }}
                        >
                          {leave.leave_type}
                        </span>
                        {leave.is_half_day && (
                          <span className="text-[10px]">Half day</span>
                        )}
                        {leave.status === 'denied' && (
                          <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-[10px]">Denied</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock size={12} />
                        {leave.start_date === leave.end_date 
                          ? leave.start_date 
                          : `${leave.start_date} → ${leave.end_date}`
                        }
                        <span className="ml-1">({leave.days_count} day{leave.days_count !== 1 ? 's' : ''})</span>
                      </div>
                    </div>
                  </div>
                ))}
                
                {upcomingLeaves.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Calendar size={32} className="mx-auto mb-2 opacity-30" />
                    <p className="text-sm">No upcoming leaves</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* Summary Dashboard */
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="glass rounded-xl border border-border/60 p-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                    <Calendar size={20} className="text-primary" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{summaryStats.totalLeaves}</p>
                    <p className="text-xs text-muted-foreground">Total Leaves in {viewYear}</p>
                  </div>
                </div>
              </div>
              
              <div className="glass rounded-xl border border-border/60 p-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <TrendingUp size={20} className="text-blue-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{summaryStats.totalDays}</p>
                    <p className="text-xs text-muted-foreground">Total Days Off</p>
                  </div>
                </div>
              </div>
              
              <div className="glass rounded-xl border border-border/60 p-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <PieChart size={20} className="text-purple-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{Object.keys(summaryStats.byType).length}</p>
                    <p className="text-xs text-muted-foreground">Leave Types Used</p>
                  </div>
                </div>
              </div>
              
              <div className="glass rounded-xl border border-border/60 p-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                    <Users size={20} className="text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{Object.keys(summaryStats.byUser).length}</p>
                    <p className="text-xs text-muted-foreground">Team Members</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Leave by Type Chart */}
              <div className="glass rounded-xl border border-border/60 p-4">
                <h3 className="text-lg font-semibold mb-4">Leave by Type</h3>
                <div className="space-y-3">
                  {Object.entries(summaryStats.byType)
                    .sort((a, b) => b[1].days - a[1].days)
                    .map(([type, data]) => (
                      <div key={type} className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <div 
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: getTypeColor(type) }}
                            />
                            <span>{type}</span>
                          </div>
                          <span className="text-muted-foreground">{data.days} days ({data.count} leaves)</span>
                        </div>
                        <div className="h-2 bg-secondary/50 rounded-full overflow-hidden">
                          <div 
                            className="h-full rounded-full transition-all duration-500"
                            style={{ 
                              width: `${(data.days / summaryStats.totalDays) * 100}%`,
                              backgroundColor: getTypeColor(type)
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  {Object.keys(summaryStats.byType).length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">No leave data for {viewYear}</p>
                  )}
                </div>
              </div>

              {/* Leave by User Chart */}
              <div className="glass rounded-xl border border-border/60 p-4">
                <h3 className="text-lg font-semibold mb-4">Leave by Team Member</h3>
                <div className="space-y-3">
                  {Object.entries(summaryStats.byUser)
                    .sort((a, b) => b[1].days - a[1].days)
                    .slice(0, 10)
                    .map(([userName, data], idx) => (
                      <div key={userName} className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <div 
                              className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-medium bg-primary/20 text-primary"
                            >
                              {userName.charAt(0)}
                            </div>
                            <span>{userName}</span>
                          </div>
                          <span className="text-muted-foreground">{data.days} days</span>
                        </div>
                        <div className="h-2 bg-secondary/50 rounded-full overflow-hidden">
                          <div 
                            className="h-full rounded-full bg-primary transition-all duration-500"
                            style={{ 
                              width: `${(data.days / Math.max(...Object.values(summaryStats.byUser).map(d => d.days))) * 100}%`,
                              opacity: 1 - (idx * 0.1)
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  {Object.keys(summaryStats.byUser).length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">No leave data for {viewYear}</p>
                  )}
                </div>
              </div>

              {/* Monthly Trend */}
              <div className="glass rounded-xl border border-border/60 p-4 lg:col-span-2">
                <h3 className="text-lg font-semibold mb-4">Monthly Leave Trend ({viewYear})</h3>
                <div className="flex items-end gap-2 h-40">
                  {summaryStats.byMonth.map((days, idx) => {
                    const maxDays = Math.max(...summaryStats.byMonth, 1);
                    const height = (days / maxDays) * 100;
                    const isCurrentMonth = idx === today.getMonth() && viewYear === today.getFullYear();
                    
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                        <span className="text-[10px] text-muted-foreground">{days || ''}</span>
                        <div 
                          className={`w-full rounded-t transition-all duration-500 ${
                            isCurrentMonth ? 'bg-primary' : 'bg-primary/50'
                          }`}
                          style={{ height: `${Math.max(height, 4)}%` }}
                        />
                        <span className="text-[10px] text-muted-foreground">{MONTHS[idx].slice(0, 3)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Add/Edit Leave Modal */}
      {showModal && (
        <>
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={() => { setShowModal(false); resetForm(); }}
          />
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div className="bg-card rounded-2xl border border-border w-full max-w-md shadow-2xl">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div>
                  <h3 className="font-semibold text-lg">{editingLeave ? 'Edit Leave' : 'Add Leave'}</h3>
                  <p className="text-sm text-muted-foreground">
                    {editingLeave ? 'Update leave details' : 'Record a new leave entry'}
                  </p>
                </div>
                <button
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-secondary transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
              
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                {/* Team Member */}
                <div>
                  <label className="block text-sm font-medium mb-2">Team Member</label>
                  <select
                    value={formData.user_id}
                    onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50"
                    data-testid="leave-user-select"
                    disabled={!!editingLeave}
                  >
                    <option value="">Select or leave blank for yourself</option>
                    {users.map(u => (
                      <option key={u.user_id || u.id} value={u.user_id || u.id}>
                        {u.name} ({u.email})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Leave Type */}
                <div>
                  <label className="block text-sm font-medium mb-2">Leave Type</label>
                  <input
                    type="text"
                    list="leave-types"
                    value={formData.leave_type}
                    onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })}
                    placeholder="e.g., Sick Leave, Vacation, WFH..."
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50"
                    required
                    data-testid="leave-type-input"
                  />
                  <datalist id="leave-types">
                    {leaveTypes.map(type => (
                      <option key={type} value={type} />
                    ))}
                  </datalist>
                </div>

                {/* Date Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Start Date</label>
                    <input
                      type="date"
                      value={formData.start_date}
                      onChange={(e) => setFormData({ ...formData, start_date: e.target.value, end_date: formData.end_date || e.target.value })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50"
                      required
                      data-testid="leave-start-date"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">End Date</label>
                    <input
                      type="date"
                      value={formData.end_date}
                      onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                      min={formData.start_date}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50"
                      required
                      data-testid="leave-end-date"
                    />
                  </div>
                </div>

                {/* Half Day Toggle */}
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="half-day"
                    checked={formData.is_half_day}
                    onChange={(e) => setFormData({ ...formData, is_half_day: e.target.checked })}
                    className="w-4 h-4 rounded border-border"
                  />
                  <label htmlFor="half-day" className="text-sm">Half day</label>
                  
                  {formData.is_half_day && (
                    <select
                      value={formData.half_day_type || ''}
                      onChange={(e) => setFormData({ ...formData, half_day_type: e.target.value })}
                      className="h-8 px-2 text-sm rounded-lg bg-background border border-border"
                    >
                      <option value="">Select half</option>
                      <option value="first_half">First Half</option>
                      <option value="second_half">Second Half</option>
                    </select>
                  )}
                </div>

                {/* Reason (Optional) */}
                <div>
                  <label className="block text-sm font-medium mb-2">Reason (optional)</label>
                  <textarea
                    value={formData.reason}
                    onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                    placeholder="Brief reason for leave..."
                    className="w-full h-20 px-3 py-2 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                    data-testid="leave-reason"
                  />
                </div>

                {/* Conflict Warning */}
                {conflicts && conflicts.people_on_leave.length > 0 && (
                  <div className={`flex items-start gap-3 p-3 rounded-lg ${
                    conflicts.conflict_level === 'high' ? 'bg-red-500/10 border border-red-500/30' :
                    conflicts.conflict_level === 'medium' ? 'bg-amber-500/10 border border-amber-500/30' :
                    'bg-emerald-500/10 border border-emerald-500/30'
                  }`}>
                    <AlertTriangle size={18} className={
                      conflicts.conflict_level === 'high' ? 'text-red-400' :
                      conflicts.conflict_level === 'medium' ? 'text-amber-400' : 'text-emerald-400'
                    } />
                    <div>
                      <p className="text-sm font-medium">{conflicts.message}</p>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {conflicts.people_on_leave.map((p, i) => (
                          <span key={i}>{p.user_name}{i < conflicts.people_on_leave.length - 1 ? ', ' : ''}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Submit */}
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => { setShowModal(false); resetForm(); }}
                    className="flex-1 h-10 px-4 rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 h-10 px-4 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
                    data-testid="submit-leave-btn"
                  >
                    {editingLeave ? 'Update Leave' : 'Add Leave'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default LeavePage;
