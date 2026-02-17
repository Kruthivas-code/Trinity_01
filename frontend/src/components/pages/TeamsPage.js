import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Users, Plus, Trash2, UserPlus, UserMinus, Loader2, X } from 'lucide-react';


const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const TeamsPage = ({ user }) => {
  const [searchParams] = useSearchParams();
  const [teams, setTeams] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(null);
  const [newTeam, setNewTeam] = useState({ name: '', type: '', description: '' });
  const [creating, setCreating] = useState(false);
  const [highlightedTeamId, setHighlightedTeamId] = useState(null);
  const teamRefs = useRef({});

  useEffect(() => {
    fetchTeams();
    fetchUsers();
    
    // Listen for create team events
    const handleCreateTeam = () => setShowCreateModal(true);
    window.addEventListener('trinity:create-team', handleCreateTeam);
    return () => window.removeEventListener('trinity:create-team', handleCreateTeam);
  }, []);

  // Handle team highlight from URL params
  useEffect(() => {
    const teamId = searchParams.get('team');
    if (teamId && teams.length > 0) {
      setHighlightedTeamId(teamId);
      // Scroll to the team card
      setTimeout(() => {
        if (teamRefs.current[teamId]) {
          teamRefs.current[teamId].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
      // Remove highlight after a few seconds
      setTimeout(() => setHighlightedTeamId(null), 3000);
    }
  }, [searchParams, teams]);

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
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        const userList = Array.isArray(data) ? data : (data.items || []);
        setUsers(userList.filter(u => u.user_id));
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const handleCreateTeam = async () => {
    if (!newTeam.name.trim()) {
      console.error('Operation failed');
      return;
    }
    
    setCreating(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/teams`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newTeam)
      });
      
      if (!response.ok) throw new Error('Failed to create team');
      
      // Success
      setShowCreateModal(false);
      setNewTeam({ name: '', type: '', description: '' });
      fetchTeams();
    } catch (error) {
      console.error('Operation failed');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteTeam = async (teamId) => {
    if (!confirm('Are you sure you want to delete this team?')) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/teams/${teamId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to delete');
      
      // Success
      fetchTeams();
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const handleAddMember = async (teamId, userId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/teams/${teamId}/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ user_id: userId })
      });
      
      if (!response.ok) throw new Error('Failed to add member');
      
      // Success
      setShowAddMemberModal(null);
      fetchTeams();
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const handleRemoveMember = async (teamId, userId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/teams/${teamId}/members/${userId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to remove member');
      
      // Success
      fetchTeams();
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const getAvailableUsers = (team) => {
    const memberIds = team.members || [];
    return Array.isArray(users) ? users.filter(u => !memberIds.includes(u.user_id)) : [];
  };

  if (!user) return null;

  return (
    <div className="h-full">
      {/* Header */}
      <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
        <div className="px-6 h-14 flex items-center justify-between">
          <h1 className="text-lg font-semibold">Teams</h1>
          
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-interactive"
            data-testid="create-team-button"
          >
            <Plus size={16} />
            <span>New Team</span>
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={32} className="animate-spin text-primary" />
          </div>
        ) : teams.length === 0 ? (
          <div className="text-center py-16 card-premium rounded-xl">
            <div className="w-14 h-14 mx-auto mb-4 rounded-xl empty-state-icon flex items-center justify-center">
              <Users size={28} className="text-muted-foreground/50" />
            </div>
            <h3 className="text-lg font-medium mb-2">No teams yet</h3>
            <p className="text-muted-foreground mb-5 text-sm">Create your first team to start organizing your agents.</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-interactive"
            >
              Create Team
            </button>
          </div>
        ) : (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {teams.map(team => (
              <div
                key={team.team_id}
                ref={el => teamRefs.current[team.team_id] = el}
                className={`card-premium rounded-xl overflow-hidden transition-all duration-500 ${
                  highlightedTeamId === team.team_id 
                    ? 'ring-2 ring-primary ring-offset-2 ring-offset-background scale-[1.02]' 
                    : ''
                }`}
                data-testid={`team-card-${team.team_id}`}
              >
                {/* Team Header */}
                <div className="p-5 border-b border-border/30 bg-gradient-subtle">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                        <Users size={20} className="text-primary" />
                      </div>
                      <div>
                        <h3 className="font-semibold">{team.name}</h3>
                        {team.type && (
                          <p className="text-xs text-muted-foreground mt-0.5">{team.type}</p>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteTeam(team.team_id)}
                      className="p-2 rounded-lg btn-destructive-subtle transition-interactive"
                      title="Delete team"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>

                  {team.description && (
                    <p className="text-sm text-muted-foreground mt-3">{team.description}</p>
                  )}
                </div>

                {/* Members */}
                <div className="p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Members ({team.member_count || 0})
                    </span>
                    <button
                      onClick={() => setShowAddMemberModal(team.team_id)}
                      className="text-xs text-primary hover:text-primary/80 flex items-center gap-1.5 font-medium transition-interactive"
                    >
                      <UserPlus size={12} />
                      Add
                    </button>
                  </div>
                  
                  {team.member_details && team.member_details.length > 0 ? (
                    <div className="space-y-2">
                      {team.member_details.map(member => (
                        <div key={member.user_id} className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/30 border border-border/30">
                          <div className="flex items-center gap-2.5">
                            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary/40 to-accent/40 flex items-center justify-center text-[11px] font-semibold text-primary">
                              {member.name?.charAt(0).toUpperCase()}
                            </div>
                            <span className="text-sm font-medium">{member.name}</span>
                          </div>
                          <button
                            onClick={() => handleRemoveMember(team.team_id, member.user_id)}
                            className="p-1.5 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-interactive"
                          >
                            <UserMinus size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 rounded-lg border border-dashed border-border/50">
                      <p className="text-sm text-muted-foreground">No members yet</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Team Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="glass rounded-xl p-6 w-full max-w-md border border-border/60 mx-4">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold">Create New Team</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 rounded-lg hover:bg-secondary/50 text-muted-foreground transition-interactive"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Team Name *</label>
                <input
                  type="text"
                  value={newTeam.name}
                  onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })}
                  className="w-full px-3 py-2.5 rounded-lg bg-secondary/30 border border-border/40 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                  placeholder="e.g., Engineering Team"
                  data-testid="team-name-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1.5">Team Type / Category</label>
                <input
                  type="text"
                  value={newTeam.type}
                  onChange={(e) => setNewTeam({ ...newTeam, type: e.target.value })}
                  className="w-full px-3 py-2.5 rounded-lg bg-secondary/30 border border-border/40 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                  placeholder="e.g., Technical, Sales, Operations"
                  data-testid="team-type-input"
                />
                <p className="text-xs text-muted-foreground mt-1">Optional - helps organize teams</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1.5">Description</label>
                <textarea
                  value={newTeam.description}
                  onChange={(e) => setNewTeam({ ...newTeam, description: e.target.value })}
                  className="w-full px-3 py-2.5 rounded-lg bg-secondary/30 border border-border/40 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm resize-none"
                  placeholder="Brief description of the team's responsibilities"
                  rows={3}
                />
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2.5 rounded-lg border border-border/40 hover:bg-secondary/30 transition-interactive text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateTeam}
                disabled={creating || !newTeam.name.trim()}
                className="flex-1 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-interactive disabled:opacity-50"
                data-testid="create-team-submit"
              >
                {creating ? <Loader2 size={16} className="animate-spin mx-auto" /> : 'Create Team'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      {showAddMemberModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="glass rounded-xl p-6 w-full max-w-md border border-border/60 mx-4">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold">Add Team Member</h2>
              <button
                onClick={() => setShowAddMemberModal(null)}
                className="p-2 rounded-lg hover:bg-secondary/50 text-muted-foreground transition-interactive"
              >
                <X size={18} />
              </button>
            </div>
            
            {(() => {
              const team = teams.find(t => t.team_id === showAddMemberModal);
              const available = team ? getAvailableUsers(team) : [];
              
              return available.length > 0 ? (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {available.map(u => (
                    <button
                      key={u.user_id}
                      onClick={() => handleAddMember(showAddMemberModal, u.user_id)}
                      className="w-full flex items-center gap-3 p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-interactive text-left"
                    >
                      <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs font-semibold">
                        {u.name?.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium">{u.name}</p>
                        <p className="text-xs text-muted-foreground">{u.email}</p>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p className="text-sm">No available users to add</p>
                  <p className="text-xs mt-1">All users are already members of this team</p>
                </div>
              );
            })()}
            
            <div className="mt-5">
              <button
                onClick={() => setShowAddMemberModal(null)}
                className="w-full px-4 py-2.5 rounded-lg border border-border/40 hover:bg-secondary/30 transition-interactive text-sm font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeamsPage;
