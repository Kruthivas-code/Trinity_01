/**
 * GlobalSettingsModal — Global Docs site settings (meta, favicon, OG, etc.)
 */
import { useState, useEffect } from 'react';
import { X, Loader2, Globe, FileText, Image as ImageIcon } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const FIELDS = [
  { key: 'meta_title', label: 'Meta Title', placeholder: 'Emergent Docs', icon: <FileText className="w-4 h-4" />, type: 'text' },
  { key: 'meta_description', label: 'Meta Description', placeholder: 'Documentation and guides for building with Emergent', icon: <FileText className="w-4 h-4" />, type: 'textarea' },
  { key: 'favicon_url', label: 'Favicon URL', placeholder: '/favicon.ico', icon: <Globe className="w-4 h-4" />, type: 'text' },
  { key: 'og_image_url', label: 'OG Image / Thumbnail URL', placeholder: 'https://example.com/og-image.png', icon: <ImageIcon className="w-4 h-4" />, type: 'text' },
  { key: 'logo_url', label: 'Logo URL', placeholder: 'https://example.com/logo.svg', icon: <ImageIcon className="w-4 h-4" />, type: 'text' },
  { key: 'footer_text', label: 'Footer Text', placeholder: 'Built with Emergent', icon: <FileText className="w-4 h-4" />, type: 'text' },
  { key: 'custom_domain', label: 'Custom Domain', placeholder: 'docs.yourcompany.com', icon: <Globe className="w-4 h-4" />, type: 'text' },
];

export const GlobalSettingsModal = ({ onClose, theme }) => {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/kb/admin/docs-settings`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => { setSettings(d || {}); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/kb/admin/docs-settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(settings),
      });
      if (!res.ok) throw new Error('Save failed');
      const data = await res.json();
      setSettings(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error(e);
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="global-settings-modal">
      <div className={`fixed inset-0 ${theme.modalOverlay} backdrop-blur-sm`} onClick={onClose} />
      <div className={`relative w-full max-w-lg mx-4 ${theme.id === 'dark' ? 'bg-[#1a1a1a] border-white/10' : 'bg-white border-gray-200'} border rounded-2xl shadow-2xl max-h-[85vh] flex flex-col`}>
        <div className={`flex items-center justify-between px-5 py-4 border-b ${theme.border} flex-shrink-0`}>
          <div>
            <h3 className={`text-sm font-semibold ${theme.text}`}>Global Docs Settings</h3>
            <p className={`text-xs ${theme.textSecondary} mt-0.5`}>Configure site-wide settings for your documentation</p>
          </div>
          <button onClick={onClose} className={`${theme.textMuted} ${theme.hoverText} transition-colors`} data-testid="global-settings-close">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-[#00A1B2]" />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {FIELDS.map(({ key, label, placeholder, icon, type }) => (
              <div key={key}>
                <label className={`flex items-center gap-2 text-xs font-medium ${theme.textMuted} mb-1.5`}>
                  <span className={theme.textSecondary}>{icon}</span>
                  {label}
                </label>
                {type === 'textarea' ? (
                  <textarea
                    value={settings[key] || ''}
                    onChange={e => setSettings(prev => ({ ...prev, [key]: e.target.value }))}
                    placeholder={placeholder}
                    rows={3}
                    className={`w-full px-3 py-2 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors resize-none`}
                    style={theme.inputBgStyle}
                    data-testid={`settings-${key}`}
                  />
                ) : (
                  <input
                    value={settings[key] || ''}
                    onChange={e => setSettings(prev => ({ ...prev, [key]: e.target.value }))}
                    placeholder={placeholder}
                    className={`w-full px-3 py-2 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors`}
                    style={theme.inputBgStyle}
                    data-testid={`settings-${key}`}
                  />
                )}
              </div>
            ))}
          </div>
        )}

        <div className={`flex items-center justify-end gap-3 px-5 py-4 border-t ${theme.border} flex-shrink-0`}>
          <button onClick={onClose} className={`px-4 py-2 rounded-lg text-sm ${theme.textMuted} ${theme.hover} transition-colors`} data-testid="global-settings-cancel">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
            data-testid="global-settings-save"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
            {saved ? 'Saved!' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};
