import React, { useState, useEffect } from 'react';
import { ArrowLeft, Users, Plus, Trash2, UserPlus, UserMinus, Loader2, Shield, Wrench } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const TeamsPage = ({ user }) => {
  const navigate = useNavigate();
  const [teams, setTeams] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(null);
  const [newTeam, setNewTeam] = useState({ name: '', type: 'l1', description: '' });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchTeams();
    fetchUsers();
  }, []);

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
        // Filter users with user_id
        setUsers(data.filter(u => u.user_id));
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const handleCreateTeam = async () => {
    if (!newTeam.name.trim()) {
      // Error
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
      setNewTeam({ name: '', type: 'l1', description: '' });
      fetchTeams();
    } catch (error) {
      // Error
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
      // Error
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
      // Error
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
      // Error
    }
  };

  const getTeamIcon = (type) => {
    switch (type) {
      case 'l1': return <Shield size={20} className="text-blue-400" />;
      case 'l2': return <Wrench size={20} className="text-purple-400" />;
      default: return <Users size={20} className="text-gray-400" />;
    }
  };

  const getTeamTypeLabel = (type) => {
    switch (type) {
      case 'l1': return 'L1 Support';
      case 'l2': return 'L2 Technical';
      case 'specialist': return 'Specialist';
      default: return type;
    }
  };

  const getAvailableUsers = (team) => {
    const memberIds = team.members || [];
    return users.filter(u => !memberIds.includes(u.user_id));
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-background">
      <div className="gradient-overlay" />
      <div className="content-wrapper relative z-10">
        {/* Header */}
        <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
          <div className="mx-auto max-w-[1200px] px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="h-9 w-9 flex items-center justify-center rounded-lg hover:bg-white/10 transition-interactive"
                data-testid="back-button"
              >
                <ArrowLeft size={20} />
              </button>
              <h1 className="text-xl font-semibold">Teams</h1>
            </div>
            
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-primary text-white hover:opacity-90 transition-interactive"
              data-testid="create-team-button"
            >
              <Plus size={16} />
              <span>New Team</span>
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="mx-auto max-w-[1200px] px-4 py-8">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={32} className="animate-spin text-primary" />
            </div>
          ) : teams.length === 0 ? (
            <div className="text-center py-12">
              <Users size={48} className="mx-auto mb-4 text-muted-foreground opacity-50" />
              <h3 className="text-lg font-medium mb-2">No teams yet</h3>
              <p className="text-muted-foreground mb-4">Create your first team to start organizing your support agents.</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 rounded-lg bg-gradient-primary text-white hover:opacity-90 transition-interactive"
              >
                Create Team
              </button>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2">
              {teams.map(team => (
                <div
                  key={team.team_id}
                  className="glass rounded-2xl p-6 border border-border/60"
                  data-testid={`team-card-${team.team_id}`}
                >
                  {/* Team Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-secondary/50 flex items-center justify-center">
                        {getTeamIcon(team.type)}
                      </div>
                      <div>
                        <h3 className="font-semibold">{team.name}</h3>
                        <p className="text-sm text-muted-foreground">{getTeamTypeLabel(team.type)}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteTeam(team.team_id)}
                      className="p-2 rounded hover:bg-destructive/10 text-destructive"
                      title="Delete team"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  {team.description && (
                    <p className="text-sm text-muted-foreground mb-4">{team.description}</p>
                  )}

                  {/* Members */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Members ({team.member_count || 0})</span>
                      <button
                        onClick={() => setShowAddMemberModal(team.team_id)}
                        className="flex items-center gap-1 text-xs text-primary hover:text-primary/80"
                      >
                        <UserPlus size={14} />
                        Add
                      </button>
                    </div>
                    
                    {team.member_details && team.member_details.length > 0 ? (
                      <div className="space-y-2">
                        {team.member_details.map(member => (
                          <div
                            key={member.user_id}
                            className="flex items-center justify-between p-2 rounded-lg bg-secondary/30"
                          >
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-full bg-gradient-primary flex items-center justify-center text-white text-xs font-medium">
                                {member.name?.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <p className="text-sm font-medium">{member.name}</p>
                                <p className="text-xs text-muted-foreground">{member.email}</p>
                              </div>
                            </div>
                            <button
                              onClick={() => handleRemoveMember(team.team_id, member.user_id)}
                              className="p-1 rounded hover:bg-destructive/10 text-destructive"
                              title="Remove member"
                            >
                              <UserMinus size={14} />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No members yet</p>
                    )}
                  </div>

                  {/* Team Stats */}
                  <div className="flex gap-4 pt-4 border-t border-border/40">
                    <div className="text-center">
                      <p className="text-lg font-semibold">{team.member_count || 0}</p>
                      <p className="text-xs text-muted-foreground">Agents</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Create Team Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="glass rounded-2xl p-6 w-full max-w-md border border-border/60 mx-4">
              <h2 className="text-lg font-semibold mb-4">Create New Team</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Team Name</label>
                  <input
                    type="text"
                    value={newTeam.name}
                    onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-secondary/30 border border-border/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="e.g., L1 Support"
                    data-testid="team-name-input"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Team Type</label>
                  <select
                    value={newTeam.type}
                    onChange={(e) => setNewTeam({ ...newTeam, type: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-secondary/30 border border-border/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
                    data-testid="team-type-select"
                  >
                    <option value="l1">L1 Support</option>
                    <option value="l2">L2 Technical</option>
                    <option value="specialist">Specialist</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Description</label>
                  <textarea
                    value={newTeam.description}
                    onChange={(e) => setNewTeam({ ...newTeam, description: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-secondary/30 border border-border/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="Brief description of the team's purpose"
                    rows={2}
                  />
                </div>
              </div>
              
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg border border-border/40 hover:bg-secondary/30 transition-interactive"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateTeam}
                  disabled={creating || !newTeam.name.trim()}
                  className="flex-1 px-4 py-2 rounded-lg bg-gradient-primary text-white hover:opacity-90 transition-interactive disabled:opacity-50"
                  data-testid="create-team-submit"
                >
                  {creating ? <Loader2 size={16} className="animate-spin mx-auto" /> : 'Create'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Add Member Modal */}
        {showAddMemberModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="glass rounded-2xl p-6 w-full max-w-md border border-border/60 mx-4">
              <h2 className="text-lg font-semibold mb-4">Add Team Member</h2>
              
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
                        <div className="w-8 h-8 rounded-full bg-gradient-primary flex items-center justify-center text-white text-xs font-medium">
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
                  <p className="text-sm text-muted-foreground">No available users to add</p>
                );
              })()}
              
              <button
                onClick={() => setShowAddMemberModal(null)}
                className="w-full mt-4 px-4 py-2 rounded-lg border border-border/40 hover:bg-secondary/30 transition-interactive"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TeamsPage;
