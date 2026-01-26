/**
 * PresenceIndicator - Shows users currently viewing a ticket
 */

import React from 'react';
import { useRealtime } from '../contexts/RealtimeContext';

const PresenceIndicator = ({ ticketId, maxAvatars = 3 }) => {
  const { currentViewers, typingUsers } = useRealtime();
  
  // Filter out current user (they know they're viewing)
  const otherViewers = currentViewers.filter(v => v.user_id !== window.__CURRENT_USER_ID__);
  
  if (otherViewers.length === 0 && typingUsers.length === 0) {
    return null;
  }

  const displayedViewers = otherViewers.slice(0, maxAvatars);
  const remainingCount = otherViewers.length - maxAvatars;
  
  // Get typing user names
  const typingNames = typingUsers.map(u => u.name.split(' ')[0]);

  return (
    <div className="flex items-center gap-2">
      {/* Avatar stack */}
      {displayedViewers.length > 0 && (
        <div className="flex items-center -space-x-2">
          {displayedViewers.map((viewer, idx) => (
            <div
              key={viewer.user_id}
              className="relative"
              style={{ zIndex: maxAvatars - idx }}
              title={`${viewer.name} is viewing`}
            >
              {viewer.picture ? (
                <img
                  src={viewer.picture}
                  alt={viewer.name}
                  className="w-7 h-7 rounded-full border-2 border-background"
                />
              ) : (
                <div className="w-7 h-7 rounded-full border-2 border-background bg-primary/20 flex items-center justify-center text-[10px] font-semibold text-primary">
                  {viewer.name?.charAt(0).toUpperCase()}
                </div>
              )}
              {/* Online indicator */}
              <span className="absolute bottom-0 right-0 w-2 h-2 bg-green-500 rounded-full border border-background" />
            </div>
          ))}
          
          {remainingCount > 0 && (
            <div className="w-7 h-7 rounded-full border-2 border-background bg-secondary flex items-center justify-center text-[10px] font-medium text-muted-foreground">
              +{remainingCount}
            </div>
          )}
        </div>
      )}
      
      {/* Typing indicator */}
      {typingNames.length > 0 && (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground animate-pulse">
          <span className="flex gap-0.5">
            <span className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
          <span>
            {typingNames.length === 1 
              ? `${typingNames[0]} is typing`
              : `${typingNames.slice(0, 2).join(', ')} are typing`
            }
          </span>
        </div>
      )}
      
      {/* Viewing indicator (if not typing) */}
      {typingNames.length === 0 && otherViewers.length > 0 && (
        <span className="text-xs text-muted-foreground">
          {otherViewers.length === 1 
            ? `${otherViewers[0].name.split(' ')[0]} is viewing`
            : `${otherViewers.length} people viewing`
          }
        </span>
      )}
    </div>
  );
};

export default PresenceIndicator;
