/**
 * SocialLinksPanel — Manage social links displayed on docs pages
 */
import { useState, useEffect } from 'react';
import { X, Loader2, ExternalLink } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const PLATFORMS = [
  { key: 'twitter', label: 'Twitter / X', placeholder: 'https://x.com/yourhandle' },
  { key: 'linkedin', label: 'LinkedIn', placeholder: 'https://linkedin.com/company/yourcompany' },
  { key: 'discord', label: 'Discord', placeholder: 'https://discord.gg/invite-code' },
  { key: 'youtube', label: 'YouTube', placeholder: 'https://youtube.com/@yourchannel' },
  { key: 'reddit', label: 'Reddit', placeholder: 'https://reddit.com/r/yoursubreddit' },
];

export const SocialLinksPanel = ({ onClose, theme }) => {
  const [links, setLinks] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/kb/social-links`)
      .then(r => r.json())
      .then(d => { setLinks(d.links || {}); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/kb/admin/social-links`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ links }),
      });
      if (!res.ok) throw new Error('Save failed');
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error(e);
      alert('Failed to save social links');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="social-links-panel">
      <div className={`fixed inset-0 ${theme.modalOverlay} backdrop-blur-sm`} onClick={onClose} />
      <div className={`relative w-full max-w-md mx-4 ${theme.id === 'dark' ? 'bg-[#1a1a1a] border-white/10' : 'bg-white border-gray-200'} border rounded-2xl shadow-2xl`}>
        <div className={`flex items-center justify-between px-5 py-4 border-b ${theme.border}`}>
          <h3 className={`text-sm font-semibold ${theme.text}`}>Social Links</h3>
          <button onClick={onClose} className={`${theme.textMuted} ${theme.hoverText} transition-colors`} data-testid="social-links-close">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-[#00A1B2]" />
          </div>
        ) : (
          <div className="p-5 space-y-4">
            <p className={`text-xs ${theme.textSecondary} mb-3`}>
              Configure social links displayed at the bottom of every docs page. Leave blank to hide.
            </p>
            {PLATFORMS.map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>{label}</label>
                <div className="relative">
                  <input
                    value={links[key] || ''}
                    onChange={e => setLinks(prev => ({ ...prev, [key]: e.target.value }))}
                    placeholder={placeholder}
                    className={`w-full px-3 py-2 pr-8 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors`}
                    style={theme.inputBgStyle}
                    data-testid={`social-input-${key}`}
                  />
                  {links[key] && (
                    <a href={links[key]} target="_blank" rel="noopener noreferrer" className={`absolute right-2 top-1/2 -translate-y-1/2 ${theme.textSecondary} hover:text-[#00A1B2] transition-colors`}>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              </div>
            ))}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button onClick={onClose} className={`px-4 py-2 rounded-lg text-sm ${theme.textMuted} ${theme.hover} transition-colors`} data-testid="social-links-cancel">
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
                data-testid="social-links-save"
              >
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                {saved ? 'Saved!' : 'Save'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
