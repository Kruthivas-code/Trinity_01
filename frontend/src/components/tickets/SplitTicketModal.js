import React, { useState } from 'react';
import { X, Scissors, AlertCircle } from 'lucide-react';

const SplitTicketModal = ({ ticket, notes, splitMessageIndex, onClose, onSplit }) => {
  const [selectedIndex, setSelectedIndex] = useState(splitMessageIndex);
  const [newTitle, setNewTitle] = useState('');

  const messages = [
    { type: 'original', content: ticket.description, index: 0 },
    ...notes.map((n, i) => ({ ...n, index: i + 1 }))
  ];

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl glass rounded-xl border border-border/60 shadow-2xl max-h-[80vh] flex flex-col">
        <div className="p-4 border-b border-border/40 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Scissors size={18} className="text-primary" />
              <h3 className="text-base font-semibold">Split Ticket</h3>
            </div>
            <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50">
              <X size={18} />
            </button>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Select where to split. Messages after this point will move to a new ticket.
          </p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {messages.map((msg, idx) => (
            <div key={idx} className="relative">
              {idx > 0 && (
                <button
                  onClick={() => setSelectedIndex(idx)}
                  className={`absolute -top-2 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium transition-colors ${
                    selectedIndex === idx 
                      ? 'bg-red-500 text-white' 
                      : 'bg-secondary/50 text-muted-foreground hover:bg-red-500/20 hover:text-red-400'
                  }`}
                >
                  <Scissors size={10} />
                  Split here
                </button>
              )}
              <div className={`p-3 rounded-lg border ${
                selectedIndex !== null && idx >= selectedIndex 
                  ? 'bg-amber-500/10 border-amber-500/30' 
                  : 'bg-secondary/30 border-border/30'
              }`}>
                <div className="text-[10px] text-muted-foreground mb-1">
                  {msg.type === 'original' ? 'Original Message' : msg.type === 'internal_note' ? 'Internal Note' : 'Reply'}
                </div>
                <p className="text-sm line-clamp-2">{msg.content || msg.text}</p>
              </div>
            </div>
          ))}
        </div>
        
        {selectedIndex !== null && (
          <div className="p-4 border-t border-border/40 space-y-3 shrink-0">
            <div className="flex items-center gap-2 text-sm text-amber-400">
              <AlertCircle size={14} />
              <span>{messages.length - selectedIndex} message(s) will move to the new ticket</span>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">New ticket title</label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder={`Split from ${ticket.ticket_id}`}
                className="w-full h-10 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
        )}
        
        <div className="p-4 border-t border-border/40 flex justify-end gap-2 shrink-0">
          <button
            onClick={onClose}
            className="h-9 px-4 text-sm rounded-lg border border-border/40 hover:bg-secondary/50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSplit(selectedIndex, newTitle || `Split from ${ticket.ticket_id}`)}
            disabled={selectedIndex === null}
            className="h-9 px-4 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Split Ticket
          </button>
        </div>
      </div>
    </div>
  );
};

export default SplitTicketModal;
