import React, { useState } from 'react';
import { X, Upload } from 'lucide-react';
import { toast } from 'sonner';

const ImportModal = ({ isOpen, onClose, onImport }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      validateAndSetFile(file);
    }
  };

  const validateAndSetFile = (file) => {
    const validTypes = ['application/json', 'text/csv', 'text/plain'];
    const validExtensions = ['.json', '.csv'];
    
    const hasValidType = validTypes.includes(file.type);
    const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    
    if (hasValidType || hasValidExtension) {
      setSelectedFile(file);
    } else {
      toast.error('Please select a JSON or CSV file');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      validateAndSetFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (selectedFile) {
      onImport(selectedFile);
      setSelectedFile(null);
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={handleClose}
        data-testid="import-modal-backdrop"
      >
        {/* Modal */}
        <div
          className="glass-elevated max-w-lg w-full rounded-2xl p-6 border border-border/60 relative"
          onClick={(e) => e.stopPropagation()}
          data-testid="import-modal"
        >
          <form onSubmit={handleSubmit}>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold" data-testid="import-modal-title">
                Import Tickets
              </h2>
              <button
                type="button"
                onClick={handleClose}
                className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-white/5 transition-interactive"
                data-testid="import-modal-close-button"
              >
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Upload a JSON or CSV file containing ticket data. The file should include fields like title, description, status, and assignee_id.
              </p>

              {/* Drop Zone */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-interactive ${
                  isDragging
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-border/60'
                }`}
                data-testid="import-dropzone"
              >
                <Upload className="mx-auto mb-3 text-muted-foreground" size={32} />
                
                {selectedFile ? (
                  <div>
                    <p className="text-sm font-medium mb-1">{selectedFile.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(selectedFile.size / 1024).toFixed(2)} KB
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium mb-1">Drop your file here</p>
                    <p className="text-xs text-muted-foreground mb-3">or click to browse</p>
                  </div>
                )}

                <input
                  type="file"
                  accept=".json,.csv"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-input"
                  data-testid="import-file-input"
                />
                <label
                  htmlFor="file-input"
                  className="inline-block px-4 py-2 rounded-lg bg-secondary/70 text-sm border border-white/10 hover:bg-secondary/90 cursor-pointer transition-interactive"
                >
                  Select File
                </label>
              </div>
            </div>

            {/* Footer */}
            <div className="mt-6 flex items-center gap-3">
              <button
                type="button"
                onClick={handleClose}
                className="flex-1 h-10 px-4 rounded-lg bg-secondary/70 text-secondary-foreground border border-white/10 hover:bg-secondary/90 transition-interactive"
                data-testid="import-modal-cancel-button"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!selectedFile}
                className="flex-1 h-10 px-4 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-cyan-400/90 transition-interactive disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="import-modal-submit-button"
              >
                Import
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
};

export default ImportModal;
