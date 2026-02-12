import React from 'react';
import { X, Keyboard } from 'lucide-react';

const KeyboardShortcutsHelp = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const shortcuts = {
    'Global': [
      { keys: ['⌘', 'K'], description: 'Open command palette' },
      { keys: ['/'], description: 'Search' },
      { keys: ['N'], description: 'Create new ticket' },
      { keys: ['⌘', 'N'], description: 'Create new ticket (anywhere)' },
      { keys: ['Esc'], description: 'Close modal/drawer' },
      { keys: ['?'], description: 'Show keyboard shortcuts' },
    ],
    'Navigation': [
      { keys: ['1'], description: 'Go to Dashboard' },
      { keys: ['2'], description: 'Go to All Tickets' },
      { keys: ['3'], description: 'Go to Starred' },
      { keys: ['4'], description: 'Go to Open Tickets' },
      { keys: ['5'], description: 'Go to Closed Tickets' },
    ],
    'Ticket Drawer': [
      { keys: ['Esc'], description: 'Close drawer' },
      { keys: ['R'], description: 'Switch to Reply mode' },
      { keys: ['N'], description: 'Switch to Note mode' },
      { keys: ['S'], description: 'Star/Unstar ticket' },
      { keys: ['A'], description: 'Assign to me' },
      { keys: ['M'], description: 'Merge with ticket' },
      { keys: ['L'], description: 'Link to ticket' },
      { keys: ['C'], description: 'Copy ticket link' },
      { keys: ['D'], description: 'Delete ticket' },
      { keys: ['1-4'], description: 'Set priority (1=Low, 4=Urgent)' },
      { keys: ['⌘', 'Enter'], description: 'Send reply/note' },
      { keys: ['⌘', 'S'], description: 'Save changes' },
    ],
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl max-h-[80vh] overflow-y-auto glass rounded-xl border border-border/60 shadow-2xl">
        <div className="sticky top-0 p-4 border-b border-border/40 bg-background/95 backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Keyboard size={20} className="text-primary" />
            <h2 className="text-lg font-semibold">Keyboard Shortcuts</h2>
          </div>
          <button 
            onClick={onClose}
            className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50 transition-colors"
          >
            <X size={18} />
          </button>
        </div>
        
        <div className="p-4 space-y-6">
          {Object.entries(shortcuts).map(([category, items]) => (
            <div key={category}>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider">
                {category}
              </h3>
              <div className="space-y-2">
                {items.map((shortcut, idx) => (
                  <div 
                    key={idx}
                    className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-secondary/30 transition-colors"
                  >
                    <span className="text-sm text-foreground">{shortcut.description}</span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, keyIdx) => (
                        <React.Fragment key={keyIdx}>
                          <kbd className="min-w-[24px] h-6 px-1.5 flex items-center justify-center rounded bg-secondary border border-border/60 text-xs font-mono font-medium shadow-sm">
                            {key}
                          </kbd>
                          {keyIdx < shortcut.keys.length - 1 && (
                            <span className="text-muted-foreground text-xs">+</span>
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        
        <div className="sticky bottom-0 p-3 border-t border-border/40 bg-background/95 backdrop-blur-sm">
          <p className="text-xs text-muted-foreground text-center">
            Press <kbd className="px-1.5 py-0.5 rounded bg-secondary border border-border/60 text-[10px] font-mono">?</kbd> anytime to show this help
          </p>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcutsHelp;
