import React from 'react';
import { 
  Plus, User, Activity, AlertTriangle, Users, Tag, GitMerge, 
  GitBranch, Scissors, Star, FileText, Edit, Clock
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// Icon mapping for activity types
const getActivityIcon = (iconName, className = "w-3.5 h-3.5") => {
  const icons = {
    'plus': Plus,
    'user': User,
    'activity': Activity,
    'alert-triangle': AlertTriangle,
    'users': Users,
    'tag': Tag,
    'git-merge': GitMerge,
    'git-branch': GitBranch,
    'scissors': Scissors,
    'star': Star,
    'file-text': FileText,
    'edit': Edit,
  };
  const Icon = icons[iconName] || Edit;
  return <Icon className={className} />;
};

// Color coding for different activity types
const getActivityColor = (field) => {
  const colors = {
    'ticket': 'bg-green-500/20 text-green-400 border-green-500/30',
    'status': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    'assignee_id': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    'priority': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    'merge': 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    'unmerge': 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    'split': 'bg-pink-500/20 text-pink-400 border-pink-500/30',
    'is_starred': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    'team_id': 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
    'tags': 'bg-teal-500/20 text-teal-400 border-teal-500/30',
  };
  return colors[field] || 'bg-slate-500/20 text-slate-400 border-slate-500/30';
};

// Format timestamp for display
const formatRelativeTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
};

// Format full date for tooltip
const formatFullDate = (timestamp) => {
  if (!timestamp) return '';
  return new Date(timestamp).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
};

// Group activities by date
const groupActivitiesByDate = (activities) => {
  const groups = {};
  const today = new Date().toDateString();
  const yesterday = new Date(Date.now() - 86400000).toDateString();

  activities.forEach(activity => {
    if (!activity.timestamp) return;
    const date = new Date(activity.timestamp);
    const dateStr = date.toDateString();
    
    let label;
    if (dateStr === today) {
      label = 'Today';
    } else if (dateStr === yesterday) {
      label = 'Yesterday';
    } else {
      label = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    if (!groups[label]) {
      groups[label] = [];
    }
    groups[label].push(activity);
  });

  return groups;
};

const ActivityItem = ({ activity }) => {
  const colorClass = getActivityColor(activity.field);
  
  return (
    <div className="flex items-start gap-3 group" data-testid="activity-item">
      {/* Icon */}
      <div className={`p-1.5 rounded-full ${colorClass} border shrink-0`}>
        {getActivityIcon(activity.icon)}
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0 pt-0.5">
        <p className="text-sm text-foreground">
          {activity.description}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-muted-foreground">
            {activity.user_name || activity.user_id || 'System'}
          </span>
          <span className="text-xs text-muted-foreground/50">•</span>
          <span 
            className="text-xs text-muted-foreground cursor-help"
            title={formatFullDate(activity.timestamp)}
          >
            {formatRelativeTime(activity.timestamp)}
          </span>
          {activity.source_ticket_id && (
            <>
              <span className="text-xs text-muted-foreground/50">•</span>
              <span className="text-xs text-cyan-400 font-mono">
                {activity.source_ticket_id}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const ActivityTimeline = ({ activities = [], loading = false }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-2">
          <Clock className="w-5 h-5 text-muted-foreground animate-pulse" />
          <span className="text-sm text-muted-foreground">Loading activity...</span>
        </div>
      </div>
    );
  }

  if (!activities || activities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Activity className="w-8 h-8 text-muted-foreground/50 mb-2" />
        <p className="text-sm text-muted-foreground">No activity recorded yet</p>
      </div>
    );
  }

  // Group activities by date (reverse order - newest first)
  const reversedActivities = [...activities].reverse();
  const groupedActivities = groupActivitiesByDate(reversedActivities);
  const dateLabels = Object.keys(groupedActivities);

  return (
    <div className="space-y-4 py-2" data-testid="activity-timeline">
      {dateLabels.map(dateLabel => (
        <div key={dateLabel}>
          {/* Date header */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              {dateLabel}
            </span>
            <div className="flex-1 h-px bg-border/30" />
          </div>
          
          {/* Activities for this date */}
          <div className="space-y-3 pl-1">
            {groupedActivities[dateLabel].map((activity, idx) => (
              <ActivityItem key={`${activity.timestamp}-${idx}`} activity={activity} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default ActivityTimeline;
