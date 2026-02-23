import React, { useState, useEffect } from 'react';
import { ArrowLeft, Mail, Calendar, Clock, Users, Plus, X, Check, Loader2, User as UserIcon } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const DAYS_OF_WEEK = [
  { value: 1, label: 'Mon' },
  { value: 2, label: 'Tue' },
  { value: 3, label: 'Wed' },
  { value: 4, label: 'Thu' },
  { value: 5, label: 'Fri' },
  { value: 6, label: 'Sat' },
  { value: 7, label: 'Sun' }
];

const ProfilePage = ({ user: currentUser }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [viewedUser, setViewedUser] = useState(null);
  const [isViewingOther, setIsViewingOther] = useState(false);
  const [myShifts, setMyShifts] = useState([]);
  const [availableShifts, setAvailableShifts] = useState([]);
  const [teams, setTeams] = useState([]);
  const [userTeams, setUserTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddShift, setShowAddShift] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState('');
  const [joiningShift, setJoiningShift] = useState(null);
  const [leavingShift, setLeavingShift] = useState(null);

  // Determine which user to display
  useEffect(() => {
    const userIdFromUrl = searchParams.get('user');
    if (userIdFromUrl && userIdFromUrl !== currentUser?.user_id) {
      // Viewing another user's profile
      setIsViewingOther(true);
      fetchUserProfile(userIdFromUrl);
    } else {
      // Viewing own profile
      setIsViewingOther(false);
      setViewedUser(currentUser);
    }
  }, [searchParams, currentUser]);

  // Fetch another user's profile
  const fetchUserProfile = async (userId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        const userList = Array.isArray(data) ? data : (data.items || []);
        const foundUser = userList.find(u => u.user_id === userId);
        if (foundUser) {
          setViewedUser(foundUser);
          // Fetch their teams
          fetchUserTeams(userId);
        } else {
          setViewedUser(null);
        }
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch teams a user belongs to
  const fetchUserTeams = async (userId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/teams`, {
        credentials: 'include'
      });
      if (response.ok) {
        const allTeams = await response.json();
        const teamsWithUser = allTeams.filter(t => t.members?.includes(userId));
        setUserTeams(teamsWithUser);
      }
    } catch (error) {
      console.error('Failed to fetch user teams:', error);
    }
  };

  // Use viewedUser for display, fall back to currentUser
  const user = viewedUser || currentUser;

  useEffect(() => {
    if (user && !isViewingOther) {
      fetchMyShifts();
      fetchTeams();
      fetchAllShifts();
    } else if (user && isViewingOther) {
      setLoading(false);
    }
  }, [user, isViewingOther]);

  const fetchMyShifts = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users/${user.user_id}/shifts`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setMyShifts(data);
      }
    } catch (error) {
      console.error('Failed to fetch my shifts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTeams = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/teams`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setTeams(data);
      }
    } catch (error) {
      console.error('Failed to fetch teams:', error);
    }
  };

  const fetchAllShifts = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/shifts`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setAvailableShifts(data);
      }
    } catch (error) {
      console.error('Failed to fetch shifts:', error);
    }
  };

  const handleJoinShift = async (shiftId) => {
    setJoiningShift(shiftId);
    try {
      const response = await fetch(`${BACKEND_URL}/api/users/${user.user_id}/shifts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ shift_id: shiftId, is_primary: true })
      });
      
      if (response.ok) {
        await fetchMyShifts();
        await fetchAllShifts();
        setShowAddShift(false);
      }
    } catch (error) {
      console.error('Failed to join shift:', error);
    } finally {
      setJoiningShift(null);
    }
  };

  const handleLeaveShift = async (shiftId) => {
    setLeavingShift(shiftId);
    try {
      const response = await fetch(`${BACKEND_URL}/api/users/${user.user_id}/shifts/${shiftId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        await fetchMyShifts();
        await fetchAllShifts();
      }
    } catch (error) {
      console.error('Failed to leave shift:', error);
    } finally {
      setLeavingShift(null);
    }
  };

  const getAvailableShiftsForTeam = () => {
    if (!selectedTeam) return [];
    const myShiftIds = myShifts.map(s => s.shift_id);
    return availableShifts.filter(s => 
      s.team_id === selectedTeam && !myShiftIds.includes(s.shift_id)
    );
  };

  if (!user) {
    return null;
  }

  return (
    <div className="h-full">
      {/* Header */}
      <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
        <div className="px-6 h-14 flex items-center gap-3">
          {isViewingOther && (
            <button
              onClick={() => navigate('/profile')}
              className="p-2 rounded-lg hover:bg-secondary/50 transition-colors"
            >
              <ArrowLeft size={18} />
            </button>
          )}
          <h1 className="text-lg font-semibold">
            {isViewingOther ? `${user?.name || 'User'}'s Profile` : 'My Profile'}
          </h1>
        </div>
      </header>

      {/* Content */}
      <div className="p-6 space-y-6 max-w-4xl">
          {/* Profile Card */}
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            {/* Profile Header */}
            <div className="flex items-center gap-6 mb-8 pb-8 border-b border-border/40">
              {user.picture ? (
                <img
                  src={user.picture}
                  alt={user.name}
                  className="w-24 h-24 rounded-full"
                />
              ) : (
                <div className="w-24 h-24 rounded-full bg-primary/20 flex items-center justify-center text-primary text-3xl font-medium">
                  {user.name?.charAt(0).toUpperCase()}
                </div>
              )}
              <div>
                <h2 className="text-2xl font-semibold mb-1">{user.name}</h2>
                <p className="text-muted-foreground">{user.email}</p>
                {user.role && (
                  <span className="inline-block mt-2 px-2 py-0.5 text-xs font-medium bg-primary/20 text-primary rounded">
                    {user.role}
                  </span>
                )}
              </div>
            </div>

            {/* Profile Details */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-4">Account Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex items-center gap-3 p-4 rounded-lg bg-secondary/30">
                    <Mail className="text-muted-foreground" size={20} />
                    <div>
                      <p className="text-sm text-muted-foreground">Email</p>
                      <p className="font-medium">{user.email}</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3 p-4 rounded-lg bg-secondary/30">
                    <Calendar className="text-muted-foreground" size={20} />
                    <div>
                      <p className="text-sm text-muted-foreground">Member Since</p>
                      <p className="font-medium">
                        {user.created_at 
                          ? new Date(user.created_at?.endsWith?.('Z') ? user.created_at : user.created_at + 'Z').toLocaleDateString('en-US', { 
                              timeZone: 'Asia/Kolkata',
                              year: 'numeric', 
                              month: 'long', 
                              day: 'numeric' 
                            })
                          : 'N/A'
                        }
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Show teams for viewed user */}
              {isViewingOther && userTeams.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium mb-4">Teams</h3>
                  <div className="flex flex-wrap gap-2">
                    {userTeams.map(team => (
                      <button
                        key={team.team_id}
                        onClick={() => navigate(`/teams?team=${team.team_id}`)}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors"
                      >
                        <Users size={14} className="text-primary" />
                        <span className="text-sm font-medium">{team.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* My Shifts Card - Only show for own profile */}
          {!isViewingOther && (
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Clock className="text-primary" size={24} />
                <div>
                  <h3 className="text-lg font-medium">My Shifts</h3>
                  <p className="text-sm text-muted-foreground">Manage your work schedule</p>
                </div>
              </div>
              <button
                onClick={() => setShowAddShift(true)}
                className="h-9 px-4 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                data-testid="add-shift-button"
              >
                <Plus size={16} />
                Join Shift
              </button>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 size={24} className="animate-spin text-primary" />
              </div>
            ) : myShifts.length === 0 ? (
              <div className="text-center py-12 bg-secondary/20 rounded-xl">
                <Clock size={40} className="mx-auto text-muted-foreground/30 mb-3" />
                <p className="text-muted-foreground">You haven't joined any shifts yet</p>
                <p className="text-sm text-muted-foreground/70 mt-1">Click "Join Shift" to get started</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {myShifts.map(userShift => (
                  <div key={userShift.user_shift_id} className="p-4 rounded-xl bg-secondary/30 border border-border/30">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-medium">{userShift.shift_details?.name || 'Unknown Shift'}</h4>
                        <p className="text-sm text-muted-foreground flex items-center gap-1.5 mt-0.5">
                          <Users size={12} />
                          {userShift.team_name || 'Unknown Team'}
                        </p>
                      </div>
                      <button
                        onClick={() => handleLeaveShift(userShift.shift_id)}
                        disabled={leavingShift === userShift.shift_id}
                        className="p-1.5 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors disabled:opacity-50"
                        title="Leave this shift"
                      >
                        {leavingShift === userShift.shift_id ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <X size={14} />
                        )}
                      </button>
                    </div>
                    
                    <div className="flex items-center gap-3 text-sm">
                      <div className="flex items-center gap-1.5 text-muted-foreground">
                        <Clock size={12} />
                        <span>
                          {userShift.shift_details?.start_time || '??:??'} - {userShift.shift_details?.end_time || '??:??'} IST
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex gap-1 mt-3">
                      {DAYS_OF_WEEK.map(day => (
                        <span
                          key={day.value}
                          className={`w-7 h-7 flex items-center justify-center text-[10px] rounded ${
                            userShift.shift_details?.days_of_week?.includes(day.value)
                              ? 'bg-primary/20 text-primary font-medium'
                              : 'bg-secondary/50 text-muted-foreground/30'
                          }`}
                        >
                          {day.label[0]}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          )}
        </div>

      {/* Add Shift Modal */}
      {showAddShift && (
        <>
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={() => setShowAddShift(false)}
          />
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div className="bg-card rounded-2xl border border-border w-full max-w-md shadow-2xl">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div>
                  <h3 className="font-semibold text-lg">Join a Shift</h3>
                  <p className="text-sm text-muted-foreground">Select a team and available shift</p>
                </div>
                <button
                  onClick={() => setShowAddShift(false)}
                  className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-secondary transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
              
              <div className="p-6 space-y-5">
                {/* Team Selection */}
                <div>
                  <label className="block text-sm font-medium mb-2">Select Team</label>
                  <select
                    value={selectedTeam}
                    onChange={(e) => setSelectedTeam(e.target.value)}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                  >
                    <option value="">Choose a team...</option>
                    {teams.map(team => (
                      <option key={team.team_id} value={team.team_id}>
                        {team.name} ({team.escalation_level || 'N/A'})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Available Shifts */}
                {selectedTeam && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Available Shifts</label>
                    {getAvailableShiftsForTeam().length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4 bg-secondary/30 rounded-lg">
                        No available shifts for this team, or you're already enrolled in all shifts
                      </p>
                    ) : (
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {getAvailableShiftsForTeam().map(shift => (
                          <button
                            key={shift.shift_id}
                            onClick={() => handleJoinShift(shift.shift_id)}
                            disabled={joiningShift === shift.shift_id}
                            className="w-full p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors text-left disabled:opacity-50"
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="font-medium">{shift.name}</div>
                                <div className="text-sm text-muted-foreground">
                                  {shift.start_time} - {shift.end_time} IST
                                </div>
                              </div>
                              {joiningShift === shift.shift_id ? (
                                <Loader2 size={16} className="animate-spin text-primary" />
                              ) : (
                                <Check size={16} className="text-primary" />
                              )}
                            </div>
                            <div className="flex gap-1 mt-2">
                              {DAYS_OF_WEEK.map(day => (
                                <span
                                  key={day.value}
                                  className={`w-5 h-5 flex items-center justify-center text-[9px] rounded ${
                                    shift.days_of_week?.includes(day.value)
                                      ? 'bg-primary/20 text-primary'
                                      : 'bg-secondary/50 text-muted-foreground/30'
                                  }`}
                                >
                                  {day.label[0]}
                                </span>
                              ))}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ProfilePage;
