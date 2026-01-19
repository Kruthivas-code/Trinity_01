import React from 'react';
import { LogOut, Plus, Download, Upload } from 'lucide-react';

const Header = ({ user, analytics, onLogout, onCreateTicket, onExport, onImport }) => {
  const [showExportMenu, setShowExportMenu] = React.useState(false);

  return (
    <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
      <div className="mx-auto max-w-[1600px] px-4 h-16 flex items-center justify-between">
        {/* Left side - Brand and analytics */}
        <div className="flex items-center gap-4">
          <h1 className="text-xl md:text-2xl font-semibold tracking-tight" data-testid="app-brand">
            TickFlow
          </h1>
          
          {analytics && (
            <div className="hidden md:flex items-center gap-3 ml-4">
              <span className="text-xs px-2 py-1 rounded-md glass" data-testid="badge-total">
                Total: {analytics.total}
              </span>
              <span className="text-xs px-2 py-1 rounded-md glass" data-testid="badge-mine">
                Mine: {analytics.my_tickets}
              </span>
            </div>
          )}
        </div>

        {/* Right side - Actions and user menu */}
        <div className="flex items-center gap-2">
          <button
            onClick={onCreateTicket}
            className="h-9 px-3 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-cyan-400/90 transition-interactive"
            data-testid="create-ticket-button"
          >
            <Plus size={16} />
            <span className="hidden sm:inline">New Ticket</span>
          </button>

          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="h-9 px-3 flex items-center gap-2 rounded-lg bg-secondary/70 text-secondary-foreground text-sm border border-white/10 hover:bg-secondary/90 transition-interactive"
              data-testid="export-button"
            >
              <Download size={16} />
              <span className="hidden sm:inline">Export</span>
            </button>

            {showExportMenu && (
              <div className="absolute right-0 top-12 glass rounded-lg border border-border/60 p-2 min-w-[120px]">
                <button
                  onClick={() => {
                    onExport('json');
                    setShowExportMenu(false);
                  }}
                  className="w-full text-left px-3 py-2 text-sm rounded hover:bg-white/5 transition-interactive"
                  data-testid="export-json-button"
                >
                  Export JSON
                </button>
                <button
                  onClick={() => {
                    onExport('csv');
                    setShowExportMenu(false);
                  }}
                  className="w-full text-left px-3 py-2 text-sm rounded hover:bg-white/5 transition-interactive"
                  data-testid="export-csv-button"
                >
                  Export CSV
                </button>
              </div>
            )}
          </div>

          <button
            onClick={onImport}
            className="h-9 px-3 flex items-center gap-2 rounded-lg bg-secondary/70 text-secondary-foreground text-sm border border-white/10 hover:bg-secondary/90 transition-interactive"
            data-testid="import-button"
          >
            <Upload size={16} />
            <span className="hidden sm:inline">Import</span>
          </button>

          <div className="h-6 w-px bg-border mx-1" />

          <div className="flex items-center gap-2">
            <div className="hidden md:block text-right">
              <p className="text-sm font-medium" data-testid="user-name">{user.name}</p>
              <p className="text-xs text-muted-foreground">{user.email}</p>
            </div>
            
            <button
              onClick={onLogout}
              className="h-9 w-9 flex items-center justify-center rounded-lg bg-transparent hover:bg-white/5 border border-transparent transition-interactive"
              data-testid="logout-button"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
