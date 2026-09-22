/**
 * NavManager — recursive, drag-and-drop navigation tree editor.
 *
 * Edits the kb_navigation tree: arbitrarily-nested groups, each holding a
 * mix of pages (existing articles, referenced by slug) and further nested
 * groups, in true display order (one `children` array per group).
 *
 * Capabilities:
 *   - Add / rename / delete a group at any depth.
 *   - Drag-and-drop reorder of a group's direct children (dnd-kit) — pages
 *     and subgroups both, within that one group. Reordering across two
 *     different groups is not drag-and-drop (nested cross-container drop
 *     targets get unreliable fast); instead every node has an explicit
 *     "Move to…" action that reparents it anywhere else in the tree,
 *     which is exactly as capable and much easier to get right.
 *   - Unlink a page from the tree (does not delete the article — it can be
 *     re-added from the sidebar's "+" on any group).
 *   - "Move to…" also drives the old bulk-move affordance: moving a GROUP
 *     relocates its own direct pages in one action (its subgroups move with
 *     it structurally since it's reparented whole).
 *   - Toggle a group's visibility (published) — hides it and everything
 *     under it from the public docs site without deleting anything.
 *
 * Nothing here talks to the network directly — `onSave(tree)` persists the
 * whole edited tree in one PUT (mirrors the single-document navigation
 * write the backend already does), and the caller re-fetches.
 */
import { useMemo, useState } from 'react';
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core';
import {
  SortableContext, useSortable, arrayMove, verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Plus, Trash2, FolderOpen, FileText, GripVertical, ArrowRightLeft,
  Save, Loader2, ChevronDown, ChevronRight, Eye, EyeOff,
} from 'lucide-react';

const nodeId = (parentId, idx, node) =>
  `${parentId}::${idx}::${node.type}::${node.type === 'page' ? node.slug : node.key}`;

// Every group in the tree, as a flat list of { key, label, depth, node },
// used to populate "Move to…" targets. `excludeKeys` removes a node and its
// own descendants so you can't move something into itself.
function flattenGroups(nodes, depth, excludeKeys, out) {
  for (const node of nodes || []) {
    if (node.type !== 'group' || excludeKeys.has(node.key)) continue;
    out.push({ key: node.key, label: node.label || node.key, depth });
    flattenGroups(node.children || [], depth + 1, excludeKeys, out);
  }
  return out;
}

// Collect a group's own key plus every descendant group's key (used to keep
// "Move to…" from offering a destination inside the thing being moved).
function collectKeys(node, into) {
  if (node.type !== 'group') return into;
  into.add(node.key);
  for (const child of node.children || []) collectKeys(child, into);
  return into;
}

// Remove a node (by identity) from anywhere in the tree, returning the new
// tree and the removed node (or null if not found).
function removeNode(nodes, target) {
  let removed = null;
  const next = [];
  for (const node of nodes) {
    if (node === target) { removed = node; continue; }
    if (node.type === 'group') {
      const [newChildren, r] = removeNode(node.children || [], target);
      if (r) removed = r;
      next.push({ ...node, children: newChildren });
    } else {
      next.push(node);
    }
  }
  return [next, removed];
}

function appendToGroup(nodes, targetKey, item) {
  return nodes.map((node) => {
    if (node.type !== 'group') return node;
    if (node.key === targetKey) {
      return { ...node, children: [...(node.children || []), item] };
    }
    return { ...node, children: appendToGroup(node.children || [], targetKey, item) };
  });
}

// ---------- Move-to picker ----------
const MoveToPicker = ({ tree, excludeKeys, onPick, onCancel, theme }) => {
  const targets = useMemo(() => flattenGroups(tree, 0, excludeKeys, []), [tree, excludeKeys]);
  return (
    <div className={`ml-6 mt-1.5 mb-1 p-2.5 ${theme.cardBg} border ${theme.borderSubtle} rounded-lg`} data-testid="move-to-picker">
      <div className="flex items-center justify-between mb-1.5">
        <p className={`text-xs ${theme.textMuted}`}>Move to:</p>
        <button onClick={onCancel} className={`text-xs ${theme.textTertiary} ${theme.hoverText}`} data-testid="move-to-cancel">Cancel</button>
      </div>
      <div className="space-y-0.5 max-h-40 overflow-y-auto">
        {targets.length === 0 && <p className={`text-xs ${theme.textTertiary} px-1 py-1`}>No other group to move into.</p>}
        {targets.map((t) => (
          <button
            key={t.key}
            onClick={() => onPick(t.key)}
            className={`w-full text-left px-2 py-1 text-xs rounded ${theme.hover} ${theme.textMuted} ${theme.hoverText} transition-colors flex items-center gap-1.5`}
            style={{ paddingLeft: `${0.5 + t.depth * 0.75}rem` }}
            data-testid={`move-to-target-${t.key}`}
          >
            <FolderOpen className="w-3 h-3 flex-shrink-0 opacity-60" />
            <span className="truncate">{t.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

// ---------- One page (leaf) row ----------
const PageRow = ({ page, id, articlesBySlug, depth, onUnlink, onMoveClick, showMovePicker, tree, excludeKeys, onMove, onCancelMove, theme }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 };
  const article = articlesBySlug.get(page.slug);
  const title = article?.sidebar_title || article?.title || page.slug;
  const isMissing = !article;

  return (
    <div ref={setNodeRef} style={{ ...style, paddingLeft: `${depth * 1.25}rem` }}>
      <div className={`group flex items-center gap-1.5 py-1 rounded-lg ${theme.hover}`} data-testid={`nav-page-${page.slug}`}>
        <button {...attributes} {...listeners} className={`p-0.5 cursor-grab active:cursor-grabbing ${theme.textTertiary} ${theme.hoverText}`} aria-label="Drag to reorder" data-testid="page-drag-handle">
          <GripVertical className="w-3.5 h-3.5" />
        </button>
        <FileText className={`w-3.5 h-3.5 flex-shrink-0 ${isMissing ? 'text-rose-400' : theme.textTertiary}`} />
        <span className={`flex-1 text-sm truncate ${isMissing ? `italic ${theme.textTertiary}` : theme.textMuted}`}>
          {title}{isMissing && ' (missing)'}
        </span>
        <button onClick={onMoveClick} className={`p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${theme.textTertiary} hover:text-[#00A1B2]`} title="Move to another group" data-testid={`move-page-${page.slug}`}>
          <ArrowRightLeft className="w-3.5 h-3.5" />
        </button>
        <button onClick={onUnlink} className={`p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${theme.textTertiary} hover:text-red-400`} title="Remove from this group (article itself is kept)" data-testid={`unlink-page-${page.slug}`}>
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
      {showMovePicker && (
        <MoveToPicker tree={tree} excludeKeys={excludeKeys} onPick={onMove} onCancel={onCancelMove} theme={theme} />
      )}
    </div>
  );
};

// ---------- One group node (recursive) ----------
const GroupNode = ({
  group, id, depth, articlesBySlug, tree, onChangeChildren, onUpdateGroup, onDeleteGroup,
  onAddSubgroup, onMoveNode, movePickerFor, setMovePickerFor, theme,
}) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 };
  const [expanded, setExpanded] = useState(true);
  const children = group.children || [];
  const excludeKeys = useMemo(() => collectKeys(group, new Set()), [group]);
  // Cheap enough to recompute on every render — no need to memoize (and
  // memoizing on `children` risks a stale count since `[] ` fallbacks are a
  // fresh array reference whenever a group has no children).
  let totalCount = 0;
  (function countPages(nodes) {
    nodes.forEach((c) => { if (c.type === 'page') totalCount += 1; else countPages(c.children || []); });
  })(children);

  const childIds = children.map((c, i) => nodeId(id, i, c));
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));
  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = childIds.indexOf(active.id);
    const newIndex = childIds.indexOf(over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    onChangeChildren(arrayMove(children, oldIndex, newIndex));
  };

  return (
    <div ref={setNodeRef} style={{ ...style, paddingLeft: `${depth * 1.25}rem` }} data-testid={`nav-group-${group.key}`}>
      <div className={`group flex items-center gap-1.5 py-1.5 rounded-lg ${theme.hover}`}>
        <button {...attributes} {...listeners} className={`p-0.5 cursor-grab active:cursor-grabbing ${theme.textTertiary} ${theme.hoverText}`} aria-label="Drag group" data-testid="group-drag-handle">
          <GripVertical className="w-3.5 h-3.5" />
        </button>
        <button onClick={() => setExpanded((e) => !e)} className={`p-0.5 ${theme.textTertiary} ${theme.hoverText}`} data-testid={`toggle-group-${group.key}`}>
          {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>
        <FolderOpen className={`w-3.5 h-3.5 flex-shrink-0 ${theme.textTertiary}`} />
        <input
          value={group.label}
          onChange={(e) => onUpdateGroup({ ...group, label: e.target.value })}
          placeholder="Group name"
          className={`flex-1 min-w-0 bg-transparent text-sm font-medium ${group.published === false ? 'opacity-50' : ''} ${theme.text} ${theme.placeholder} outline-none border-b border-transparent focus:border-[#00A1B2] px-1 py-0.5`}
          data-testid={`group-label-input-${group.key}`}
        />
        {group.published === false && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400 flex-shrink-0">hidden</span>
        )}
        {depth === 0 && (
          <input
            value={group.icon || ''}
            onChange={(e) => onUpdateGroup({ ...group, icon: e.target.value })}
            placeholder="icon"
            title="lucide-react icon name (top-level groups only)"
            className={`w-20 ${theme.inputBg} text-xs font-mono ${theme.textMuted} rounded px-1.5 py-1 border ${theme.inputBorder}`}
            style={theme.inputBgStyle}
            data-testid={`group-icon-input-${group.key}`}
          />
        )}
        <input
          value={group.key}
          onChange={(e) => onUpdateGroup({ ...group, key: e.target.value })}
          placeholder="key"
          className={`w-28 ${theme.inputBg} text-xs font-mono ${theme.textMuted} rounded px-1.5 py-1 border ${theme.inputBorder}`}
          style={theme.inputBgStyle}
          data-testid={`group-key-input-${group.key}`}
        />
        <span className={`text-[10px] ${theme.textTertiary} flex-shrink-0 px-1`}>{totalCount}</span>
        <button onClick={onAddSubgroup} className={`p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${theme.textTertiary} hover:text-[#00A1B2]`} title="Add nested group" data-testid={`add-subgroup-${group.key}`}>
          <Plus className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => onUpdateGroup({ ...group, published: group.published === false ? true : false })}
          className={`p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${theme.textTertiary} hover:text-[#00A1B2]`}
          title={group.published === false ? 'Show on public docs' : 'Hide from public docs'}
          data-testid={`toggle-published-${group.key}`}
        >
          {group.published === false ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
        </button>
        <button onClick={() => setMovePickerFor(movePickerFor === group.key ? null : group.key)} className={`p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${movePickerFor === group.key ? 'text-[#00A1B2]' : `${theme.textTertiary} hover:text-[#00A1B2]`}`} title="Move this group (and its pages) elsewhere" data-testid={`move-group-${group.key}`}>
          <ArrowRightLeft className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => {
            if (window.confirm(`Delete "${group.label}"? ${totalCount > 0 ? `${totalCount} page(s) inside will be unlinked (not deleted) ` : ''}and any nested groups go with it.`)) {
              onDeleteGroup(group.key);
            }
          }}
          className={`p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${theme.textTertiary} hover:text-red-400`}
          title="Delete group"
          data-testid={`delete-group-${group.key}`}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {movePickerFor === group.key && (
        <MoveToPicker
          tree={tree}
          excludeKeys={excludeKeys}
          onPick={(targetKey) => { onMoveNode(group, targetKey); setMovePickerFor(null); }}
          onCancel={() => setMovePickerFor(null)}
          theme={theme}
        />
      )}

      {expanded && children.length > 0 && (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={childIds} strategy={verticalListSortingStrategy}>
            {children.map((child, i) => {
              const childId = childIds[i];
              if (child.type === 'page') {
                return (
                  <PageRow
                    key={childId}
                    id={childId}
                    page={child}
                    depth={depth + 1}
                    articlesBySlug={articlesBySlug}
                    tree={tree}
                    excludeKeys={excludeKeys}
                    showMovePicker={movePickerFor === `page::${child.slug}`}
                    onMoveClick={() => setMovePickerFor(movePickerFor === `page::${child.slug}` ? null : `page::${child.slug}`)}
                    onMove={(targetKey) => { onMoveNode(child, targetKey); setMovePickerFor(null); }}
                    onCancelMove={() => setMovePickerFor(null)}
                    onUnlink={() => onChangeChildren(children.filter((c) => c !== child))}
                    theme={theme}
                  />
                );
              }
              return (
                <GroupNode
                  key={childId}
                  id={childId}
                  group={child}
                  depth={depth + 1}
                  articlesBySlug={articlesBySlug}
                  tree={tree}
                  onChangeChildren={(newChildren) => onUpdateGroup({ ...child, children: newChildren })}
                  onUpdateGroup={(updated) => onChangeChildren(children.map((c) => (c === child ? updated : c)))}
                  onDeleteGroup={() => onChangeChildren(children.filter((c) => c !== child))}
                  onAddSubgroup={() => {
                    const newSub = { type: 'group', key: `group-${Date.now()}`, label: 'New Group', icon: '', published: true, children: [] };
                    onUpdateGroup({ ...child, children: [...(child.children || []), newSub] });
                  }}
                  onMoveNode={onMoveNode}
                  movePickerFor={movePickerFor}
                  setMovePickerFor={setMovePickerFor}
                  theme={theme}
                />
              );
            })}
          </SortableContext>
        </DndContext>
      )}
    </div>
  );
};

export const NavManager = ({ groups, articles, onSave, theme }) => {
  const [tree, setTree] = useState(() => JSON.parse(JSON.stringify(groups || [])));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [rootMovePickerFor, setRootMovePickerFor] = useState(null);

  const articlesBySlug = useMemo(() => new Map((articles || []).map((a) => [a.slug, a])), [articles]);
  const rootIds = tree.map((g, i) => nodeId('root', i, g));
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const handleRootDragEnd = (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = rootIds.indexOf(active.id);
    const newIndex = rootIds.indexOf(over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    setTree(arrayMove(tree, oldIndex, newIndex));
  };

  const updateRootGroup = (updated, original) => {
    setTree((t) => t.map((g) => (g === original ? updated : g)));
  };

  const addTopLevelGroup = () => {
    setTree((t) => [...t, { type: 'group', key: `group-${Date.now()}`, label: 'New Group', icon: 'file-text', published: true, children: [] }]);
  };

  // Reparent any node (group or page) elsewhere in the tree, wherever it
  // currently lives, dropping it at the end of the target group's children.
  const moveNode = (target, targetKey) => {
    setTree((t) => {
      const [withoutNode, removed] = removeNode(t, target);
      if (!removed) return t;
      return appendToGroup(withoutNode, targetKey, removed);
    });
  };

  const handleSave = async () => {
    setSaving(true);
    await onSave(tree);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-3" data-testid="nav-manager">
      <div className="flex items-center justify-between">
        <p className={`text-xs ${theme.textSecondary}`}>
          Drag to reorder within a group; use the move icon to relocate a page or group anywhere else in the tree.
        </p>
        <button onClick={addTopLevelGroup} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[#00A1B2] hover:opacity-90 text-white rounded-lg transition-opacity flex-shrink-0" data-testid="add-group-btn">
          <Plus className="w-3 h-3" /> Add Group
        </button>
      </div>

      {tree.length === 0 ? (
        <div className={`px-4 py-8 text-center text-xs ${theme.textTertiary} border ${theme.border} rounded-xl`}>
          No navigation groups yet. Click <strong className={theme.textMuted}>Add Group</strong> to start.
        </div>
      ) : (
        <div className={`border ${theme.border} rounded-xl p-2`}>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleRootDragEnd}>
            <SortableContext items={rootIds} strategy={verticalListSortingStrategy}>
              {tree.map((group, i) => (
                <GroupNode
                  key={rootIds[i]}
                  id={rootIds[i]}
                  group={group}
                  depth={0}
                  articlesBySlug={articlesBySlug}
                  tree={tree}
                  onChangeChildren={(newChildren) => updateRootGroup({ ...group, children: newChildren }, group)}
                  onUpdateGroup={(updated) => updateRootGroup(updated, group)}
                  onDeleteGroup={() => setTree((t) => t.filter((g) => g !== group))}
                  onAddSubgroup={() => {
                    const newSub = { type: 'group', key: `group-${Date.now()}`, label: 'New Group', icon: '', published: true, children: [] };
                    updateRootGroup({ ...group, children: [...(group.children || []), newSub] }, group);
                  }}
                  onMoveNode={moveNode}
                  movePickerFor={rootMovePickerFor}
                  setMovePickerFor={setRootMovePickerFor}
                  theme={theme}
                />
              ))}
            </SortableContext>
          </DndContext>
        </div>
      )}

      <div className="flex justify-end pt-1">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
          data-testid="save-nav-btn">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saved ? 'Saved!' : 'Save Navigation'}
        </button>
      </div>
    </div>
  );
};

export default NavManager;
