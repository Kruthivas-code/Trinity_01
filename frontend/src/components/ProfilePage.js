import React from 'react';
import { ArrowLeft, Mail, Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const ProfilePage = ({ user }) => {
  const navigate = useNavigate();

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="gradient-overlay" />
      <div className="content-wrapper relative z-10">
        {/* Header */}
        <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
          <div className="mx-auto max-w-[1200px] px-4 h-16 flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="h-9 w-9 flex items-center justify-center rounded-lg hover:bg-white/5 transition-interactive"
              data-testid="back-button"
            >
              <ArrowLeft size={20} />
            </button>
            <h1 className="text-xl font-semibold">Profile</h1>
          </div>
        </header>

        {/* Content */}
        <div className="mx-auto max-w-[1200px] px-4 py-8">
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
              </div>
            </div>

            {/* Profile Details */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-4">Account Information</h3>
                <div className="space-y-4">
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
                          ? new Date(user.created_at).toLocaleDateString('en-US', { 
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
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
