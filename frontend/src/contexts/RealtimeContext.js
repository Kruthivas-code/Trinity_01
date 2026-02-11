/**
 * Trinity Real-time Collaboration Context
 * Manages WebSocket connection and presence state
 */

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { io } from 'socket.io-client';


const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const RealtimeContext = createContext(null);

export const useRealtime = () => {
  const context = useContext(RealtimeContext);
  if (!context) {
    throw new Error('useRealtime must be used within a RealtimeProvider');
  }
  return context;
};

export const RealtimeProvider = ({ children, user }) => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [currentViewers, setCurrentViewers] = useState([]);
  const [typingUsers, setTypingUsers] = useState([]);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Initialize socket connection
  useEffect(() => {
    if (!user) return;

    // Connect to the backend Socket.IO endpoint via /api routing
    const socketUrl = BACKEND_URL || window.location.origin;
    
    const newSocket = io(socketUrl, {
      path: '/api/socket.io/',
      transports: ['polling', 'websocket'],
      upgrade: true,
      reconnection: true,
      reconnectionDelay: 2000,
      reconnectionDelayMax: 10000,
      reconnectionAttempts: maxReconnectAttempts,
      timeout: 20000,
    });

    // Connection events
    newSocket.on('connect', () => {
      console.log('🔌 Connected to real-time server');
      setIsConnected(true);
      reconnectAttempts.current = 0;
      
      // Authenticate
      newSocket.emit('authenticate', {
        user_id: user.user_id,
        name: user.name,
        email: user.email,
        picture: user.picture
      });
    });

    newSocket.on('disconnect', (reason) => {
      console.log('🔌 Disconnected:', reason);
      setIsConnected(false);
    });

    newSocket.on('connect_error', (error) => {
      console.error('Connection error:', error);
      reconnectAttempts.current++;
      if (reconnectAttempts.current >= maxReconnectAttempts) {
        console.log('Max reconnection attempts reached');
      }
    });

    // Authentication response
    newSocket.on('authenticated', async (data) => {
      console.log('✅ Authenticated:', data);
      
      // Trigger shift-start auto-assignment
      try {
        const response = await fetch(`${BACKEND_URL}/api/auth/shift-start`, {
          method: 'POST',
          credentials: 'include'
        });
        if (response.ok) {
          const result = await response.json();
          if (result.tickets_assigned > 0) {
            console.log(`📋 Shift start: ${result.tickets_assigned} tickets assigned`);
          }
        }
      } catch (error) {
        console.log('Shift-start trigger skipped:', error.message);
      }
    });

    // User presence events
    newSocket.on('user:online', (userData) => {
      setOnlineUsers(prev => {
        if (!prev.find(u => u.user_id === userData.user_id)) {
          return [...prev, userData];
        }
        return prev;
      });
    });

    newSocket.on('user:offline', (data) => {
      setOnlineUsers(prev => prev.filter(u => u.user_id !== data.user_id));
      setCurrentViewers(prev => prev.filter(u => u.user_id !== data.user_id));
    });

    // Location events
    newSocket.on('presence:sync', (data) => {
      setCurrentViewers(data.users || []);
    });

    newSocket.on('user:joined', (data) => {
      setCurrentViewers(prev => {
        if (!prev.find(u => u.user_id === data.user_id)) {
          return [...prev, data];
        }
        return prev;
      });
    });

    newSocket.on('user:left', (data) => {
      setCurrentViewers(prev => prev.filter(u => u.user_id !== data.user_id));
    });

    // Typing events
    newSocket.on('user:typing', (data) => {
      if (data.is_typing) {
        setTypingUsers(prev => {
          if (!prev.find(u => u.user_id === data.user_id)) {
            return [...prev, { user_id: data.user_id, name: data.name }];
          }
          return prev;
        });
      } else {
        setTypingUsers(prev => prev.filter(u => u.user_id !== data.user_id));
      }
    });

    setSocket(newSocket);

    // Heartbeat interval
    const heartbeatInterval = setInterval(() => {
      if (newSocket.connected) {
        newSocket.emit('heartbeat');
      }
    }, 30000);

    return () => {
      clearInterval(heartbeatInterval);
      newSocket.disconnect();
    };
  }, [user]);

  // Update socket reference for external use
  const socketRef = useRef(socket);

  // Join a location (ticket, dashboard, etc.)
  const joinLocation = useCallback((type, id = null) => {
    if (socket?.connected) {
      socket.emit('join_location', { type, id });
    }
  }, [socket]);

  // Leave a location
  const leaveLocation = useCallback((type, id = null) => {
    if (socket?.connected) {
      socket.emit('leave_location', { type, id });
      setCurrentViewers([]);
      setTypingUsers([]);
    }
  }, [socket]);

  // Send typing indicator
  const sendTyping = useCallback((type, id, isTyping) => {
    if (socket?.connected) {
      socket.emit('typing', { type, id, is_typing: isTyping });
    }
  }, [socket]);

  // Subscribe to ticket updates
  const onTicketUpdate = useCallback((callback) => {
    if (!socket) return () => {};
    
    const handler = (data) => callback(data);
    socket.on('ticket:update', handler);
    socket.on('ticket:created', handler);
    socket.on('ticket:deleted', handler);
    
    return () => {
      socket.off('ticket:update', handler);
      socket.off('ticket:created', handler);
      socket.off('ticket:deleted', handler);
    };
  }, [socket]);

  // Subscribe to leave updates
  const onLeaveUpdate = useCallback((callback) => {
    if (!socket) return () => {};
    
    const handler = (data) => callback(data);
    socket.on('leave:created', handler);
    socket.on('leave:updated', handler);
    socket.on('leave:deleted', handler);
    
    return () => {
      socket.off('leave:created', handler);
      socket.off('leave:updated', handler);
      socket.off('leave:deleted', handler);
    };
  }, [socket]);

  // Subscribe to notifications (general)
  const onNotification = useCallback((callback) => {
    if (!socket) return () => {};
    
    socket.on('notification:new', callback);
    return () => socket.off('notification:new', callback);
  }, [socket]);

  // Subscribe to mention notifications specifically
  const onMentionNotification = useCallback((callback) => {
    if (!socket) return () => {};
    
    socket.on('notification:mention', callback);
    return () => socket.off('notification:mention', callback);
  }, [socket]);

  const value = {
    socket,
    isConnected,
    onlineUsers,
    currentViewers,
    typingUsers,
    joinLocation,
    leaveLocation,
    sendTyping,
    onTicketUpdate,
    onLeaveUpdate,
    onNotification,
    onMentionNotification,
  };

  return (
    <RealtimeContext.Provider value={value}>
      {children}
    </RealtimeContext.Provider>
  );
};

export default RealtimeContext;
