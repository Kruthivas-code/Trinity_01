import React from 'react';
import Sidebar from './Sidebar';

/**
 * PageLayout - Wrapper that adds Sidebar to standalone pages
 * Used for pages that don't use MainLayout (Profile, Settings, Teams, Admin)
 */
const PageLayout = ({ user, children }) => {
  return (
    <div className="min-h-screen flex bg-background">
      <div className="gradient-overlay" />
      
      <Sidebar user={user} />
      
      <main className="flex-1 relative z-10">
        {children}
      </main>
    </div>
  );
};

export default PageLayout;
