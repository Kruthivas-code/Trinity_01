/**
 * NavManager — Navigation structure manager modal
 */
import { useState } from 'react';
import {
  Plus, X, Trash2, FolderOpen, ArrowRight, Save, Loader2
} from 'lucide-react';

export const NavManager = ({ navGroups, onSave, onClose, onBulkMove }) => {
  const [groups, setGroups] = useState(JSON.parse(JSON.stringify(navGroups)));
  const [saving, setSaving] = useState(false);
  const [moveTarget, setMoveTarget] = useState(null);

  const addGroup = () => {
    const key = `group-${Date.now()}`;
    setGroups([...groups, { key, label: 'New Group', icon: 'file-text', sections: [{ key: 'default', label: 'Default' }] }]);
  };
  const removeGroup = (idx) => { if (window.confirm('Delete this nav group? Articles will remain but be unlinked.')) setGroups(groups.filter((_, i) => i !== idx)); };
  const updateGroup = (idx, field, val) => { const g = [...groups]; g[idx] = { ...g[idx], [field]: val }; setGroups(g); };
  const addSection = (gIdx) => { const g = [...groups]; g[gIdx].sections = [...(g[gIdx].sections || []), { key: `section-${Date.now()}`, label: 'New Section' }]; setGroups(g); };
  const removeSection = (gIdx, sIdx) => { const g = [...groups]; g[gIdx].sections = g[gIdx].sections.filter((_, i) => i !== sIdx); setGroups(g); };
  const updateSection = (gIdx, sIdx, field, val) => { const g = [...groups]; g[gIdx].sections[sIdx] = { ...g[gIdx].sections[sIdx], [field]: val }; setGroups(g); };
  const moveGroup = (idx, dir) => { const g = [...groups]; const t = g[idx]; g[idx] = g[idx + dir]; g[idx + dir] = t; setGroups(g); };
  const moveSection = (gIdx, sIdx, dir) => { const g = [...groups]; const secs = [...g[gIdx].sections]; const t = secs[sIdx]; secs[sIdx] = secs[sIdx + dir]; secs[sIdx + dir] = t; g[gIdx].sections = secs; setGroups(g); };

  const handleSave = async () => { setSaving(true); await onSave(groups); setSaving(false); };

  const getMoveTargets = (gIdx, sIdx) => {
    const targets = [];
    groups.forEach((g, gi) => {
      (g.sections || []).forEach((s, si) => {
        if (gi !== gIdx || si !== sIdx) targets.push({ gIdx: gi, sIdx: si, groupKey: g.key, groupLabel: g.label, sectionKey: s.key, sectionLabel: s.label });
      });
    });
    return targets;
  };

  const handleBulkMove = async (sourceGIdx, sourceSIdx, target) => {
    const srcGroup = navGroups[sourceGIdx] || groups[sourceGIdx];
    const srcSection = (srcGroup?.sections || [])[sourceSIdx] || groups[sourceGIdx]?.sections?.[sourceSIdx];
    if (!srcGroup || !srcSection) return;
    const count = await onBulkMove(srcGroup.key, srcSection.key, target.groupKey, target.groupLabel, target.sectionKey, target.sectionLabel);
    setMoveTarget(null);
    if (count > 0) alert(`Moved ${count} article(s) successfully.`);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" data-testid="nav-manager-modal">
      <div className="bg-[#0c0c0c] border border-slate-800/80 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800/80">
          <h2 className="text-base font-semibold text-white">Navigation Structure</h2>
          <div className="flex items-center gap-2">
            <button onClick={addGroup} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[#00A1B2] hover:opacity-90 text-white rounded-lg transition-opacity" data-testid="add-group-btn">
              <Plus className="w-3 h-3" /> Add Tab
            </button>
            <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"><X className="w-4 h-4" /></button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {groups.map((group, gIdx) => (
            <div key={group.key} className="border border-slate-800/80 rounded-xl bg-slate-900/30" data-testid={`nav-group-${gIdx}`}>
              <div className="flex items-center gap-2 p-3 border-b border-slate-800/50">
                <div className="flex flex-col gap-0.5">
                  <button disabled={gIdx === 0} onClick={() => moveGroup(gIdx, -1)} className="text-slate-600 hover:text-white disabled:opacity-20 text-[10px]">▲</button>
                  <button disabled={gIdx === groups.length - 1} onClick={() => moveGroup(gIdx, 1)} className="text-slate-600 hover:text-white disabled:opacity-20 text-[10px]">▼</button>
                </div>
                <input value={group.label} onChange={e => updateGroup(gIdx, 'label', e.target.value)} placeholder="Tab name"
                  className="flex-1 bg-transparent text-sm font-medium text-white placeholder:text-slate-600 outline-none border-b border-transparent focus:border-[#00A1B2] px-1 py-0.5" />
                <input value={group.key} onChange={e => updateGroup(gIdx, 'key', e.target.value)} placeholder="key"
                  className="w-36 bg-slate-800 text-xs font-mono text-slate-400 rounded px-2 py-1 border border-slate-700" />
                <button onClick={() => removeGroup(gIdx)} className="p-1 text-slate-600 hover:text-red-400 rounded"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
              <div className="p-3 space-y-2">
                {(group.sections || []).map((sec, sIdx) => (
                  <div key={sec.key} data-testid={`nav-section-${gIdx}-${sIdx}`}>
                    <div className="flex items-center gap-2 pl-4">
                      <div className="flex flex-col gap-0.5">
                        <button disabled={sIdx === 0} onClick={() => moveSection(gIdx, sIdx, -1)} className="text-slate-600 hover:text-white disabled:opacity-20 text-[10px]">▲</button>
                        <button disabled={sIdx === (group.sections || []).length - 1} onClick={() => moveSection(gIdx, sIdx, 1)} className="text-slate-600 hover:text-white disabled:opacity-20 text-[10px]">▼</button>
                      </div>
                      <FolderOpen className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />
                      <input value={sec.label} onChange={e => updateSection(gIdx, sIdx, 'label', e.target.value)} placeholder="Section name"
                        className="flex-1 bg-transparent text-sm text-slate-300 placeholder:text-slate-600 outline-none border-b border-transparent focus:border-[#00A1B2] px-1 py-0.5" />
                      <input value={sec.key} onChange={e => updateSection(gIdx, sIdx, 'key', e.target.value)} placeholder="key"
                        className="w-28 bg-slate-800 text-xs font-mono text-slate-400 rounded px-2 py-1 border border-slate-700" />
                      <button onClick={() => setMoveTarget(moveTarget?.gIdx === gIdx && moveTarget?.sIdx === sIdx ? null : { gIdx, sIdx })}
                        className={`p-1 rounded transition-colors ${moveTarget?.gIdx === gIdx && moveTarget?.sIdx === sIdx ? 'text-[#00A1B2] bg-[#00A1B2]/10' : 'text-slate-600 hover:text-[#00A1B2]'}`}
                        title="Move articles to another section" data-testid={`move-section-${gIdx}-${sIdx}`}>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => removeSection(gIdx, sIdx)} className="p-1 text-slate-600 hover:text-red-400 rounded"><Trash2 className="w-3 h-3" /></button>
                    </div>
                    {moveTarget?.gIdx === gIdx && moveTarget?.sIdx === sIdx && (
                      <div className="ml-10 mt-2 p-2.5 bg-slate-800/50 border border-slate-700 rounded-lg" data-testid="move-target-picker">
                        <p className="text-xs text-slate-400 mb-2">Move all articles in <strong className="text-white">{sec.label}</strong> to:</p>
                        <div className="space-y-1 max-h-32 overflow-y-auto">
                          {getMoveTargets(gIdx, sIdx).map((t, i) => (
                            <button key={i} onClick={() => handleBulkMove(gIdx, sIdx, t)}
                              className="w-full text-left px-2.5 py-1.5 text-xs rounded hover:bg-slate-700 text-slate-300 hover:text-white transition-colors flex items-center gap-2"
                              data-testid={`move-target-${i}`}>
                              <ArrowRight className="w-3 h-3 text-[#00A1B2]" />
                              <span className="text-slate-500">{t.groupLabel}</span>
                              <span className="text-slate-600">/</span>
                              <span>{t.sectionLabel}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                <button onClick={() => addSection(gIdx)} className="flex items-center gap-1.5 ml-4 px-2 py-1 text-xs text-slate-500 hover:text-[#00A1B2] rounded hover:bg-slate-800/50 transition-colors" data-testid={`add-section-${gIdx}`}>
                  <Plus className="w-3 h-3" /> Add Section
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-slate-800/80">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">Cancel</button>
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity" data-testid="save-nav-btn">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Save Navigation
          </button>
        </div>
      </div>
    </div>
  );
};
