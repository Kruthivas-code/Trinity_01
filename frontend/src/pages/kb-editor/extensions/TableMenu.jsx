/**
 * TableMenu — Floating context menu for table row operations in TipTap editor.
 * Shows a grip handle on row hover with Insert/Move/Copy/Delete actions.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  GripVertical, Plus, ArrowUp, ArrowDown, Copy, Trash2
} from 'lucide-react';

const MENU_ITEMS = [
  { key: 'insertBefore', label: 'Insert before', icon: Plus, action: 'addRowBefore' },
  { key: 'insertAfter', label: 'Insert after', icon: Plus, action: 'addRowAfter' },
  { key: 'moveUp', label: 'Move up', icon: ArrowUp, action: 'moveRowUp' },
  { key: 'moveDown', label: 'Move down', icon: ArrowDown, action: 'moveRowDown' },
  { key: 'copyRow', label: 'Copy row', icon: Copy, action: 'copyRow' },
  { key: 'deleteRow', label: 'Delete row', icon: Trash2, action: 'deleteRow' },
];

const moveRow = (editor, direction) => {
  const { state } = editor;
  const { selection } = state;
  const { $from } = selection;

  // Walk up from cursor to find the tableRow node
  let rowDepth = null;
  for (let d = $from.depth; d > 0; d--) {
    if ($from.node(d).type.name === 'tableRow') { rowDepth = d; break; }
  }
  if (rowDepth === null) return;

  const tableDepth = rowDepth - 1;
  const table = $from.node(tableDepth);
  const rowIndex = $from.index(tableDepth);
  const targetIndex = direction === 'up' ? rowIndex - 1 : rowIndex + 1;

  // Can't move header row or go out of bounds
  if (targetIndex < 1 || targetIndex >= table.childCount) return; // skip header row (index 0)

  const { tr } = state;
  const tableStart = $from.start(tableDepth);

  // Calculate positions of both rows
  let pos = tableStart;
  const rowPositions = [];
  for (let i = 0; i < table.childCount; i++) {
    rowPositions.push({ start: pos, size: table.child(i).nodeSize });
    pos += table.child(i).nodeSize;
  }

  const from = rowPositions[rowIndex];
  const to = rowPositions[targetIndex];
  const rowNode = table.child(rowIndex);
  const targetNode = table.child(targetIndex);

  // Swap the two rows
  if (direction === 'up') {
    tr.replaceWith(to.start, to.start + to.size, rowNode);
    tr.replaceWith(from.start, from.start + from.size, targetNode);
  } else {
    tr.replaceWith(from.start, from.start + from.size, targetNode);
    tr.replaceWith(to.start, to.start + to.size, rowNode);
  }

  editor.view.dispatch(tr);
};

const copyRow = (editor) => {
  const { state } = editor;
  const { selection } = state;
  const { $from } = selection;

  let rowDepth = null;
  for (let d = $from.depth; d > 0; d--) {
    if ($from.node(d).type.name === 'tableRow') { rowDepth = d; break; }
  }
  if (rowDepth === null) return;

  const tableDepth = rowDepth - 1;
  const table = $from.node(tableDepth);
  const rowIndex = $from.index(tableDepth);
  const rowNode = table.child(rowIndex);

  // Create a copy of the row (replacing th with td for copied rows)
  const { tr } = state;
  const tableStart = $from.start(tableDepth);
  let insertPos = tableStart;
  for (let i = 0; i <= rowIndex; i++) {
    insertPos += table.child(i).nodeSize;
  }

  // Build cells as td
  const cells = [];
  rowNode.forEach(cell => {
    const cellType = editor.schema.nodes.tableCell;
    cells.push(cellType.create(cell.attrs, cell.content));
  });
  const newRow = editor.schema.nodes.tableRow.create(null, cells);

  tr.insert(insertPos, newRow);
  editor.view.dispatch(tr);
};

export const TableRowMenu = ({ editor }) => {
  const [menuPos, setMenuPos] = useState(null);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);

  const handleAction = useCallback((action) => {
    if (!editor) return;
    switch (action) {
      case 'addRowBefore': editor.chain().focus().addRowBefore().run(); break;
      case 'addRowAfter': editor.chain().focus().addRowAfter().run(); break;
      case 'moveRowUp': moveRow(editor, 'up'); break;
      case 'moveRowDown': moveRow(editor, 'down'); break;
      case 'copyRow': copyRow(editor); break;
      case 'deleteRow': editor.chain().focus().deleteRow().run(); break;
      default: break;
    }
    setShowMenu(false);
  }, [editor]);

  // Track which row the cursor is in and position the grip handle
  useEffect(() => {
    if (!editor) return;
    const update = () => {
      const { state } = editor;
      const { selection } = state;
      const { $from } = selection;

      let inTable = false;
      for (let d = $from.depth; d > 0; d--) {
        if ($from.node(d).type.name === 'tableRow') {
          inTable = true;
          break;
        }
      }
      if (!inTable) {
        setMenuPos(null);
        setShowMenu(false);
        return;
      }

      // Find the DOM node for the table row
      const domAtPos = editor.view.domAtPos($from.pos);
      let rowEl = domAtPos.node;
      while (rowEl && rowEl.tagName !== 'TR') {
        rowEl = rowEl.parentElement;
      }
      if (!rowEl) { setMenuPos(null); return; }

      const tableEl = rowEl.closest('table');
      if (!tableEl) { setMenuPos(null); return; }

      const tableRect = tableEl.getBoundingClientRect();
      const rowRect = rowEl.getBoundingClientRect();

      setMenuPos({
        top: rowRect.top - tableRect.top + rowRect.height / 2,
        left: -28,
        isHeader: rowEl.querySelector('th') !== null,
      });
    };

    editor.on('selectionUpdate', update);
    editor.on('transaction', update);
    return () => {
      editor.off('selectionUpdate', update);
      editor.off('transaction', update);
    };
  }, [editor]);

  // Close menu on outside click
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (!menuPos || menuPos.isHeader) return null;

  return (
    <>
      {/* Grip handle */}
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="absolute z-20 p-0.5 rounded hover:bg-white/10 transition-colors cursor-grab"
        style={{ top: menuPos.top - 10, left: menuPos.left }}
        title="Row actions"
        data-testid="table-row-grip"
      >
        <GripVertical className="w-4 h-4 text-emerald-400" />
      </button>

      {/* Context menu */}
      {showMenu && (
        <div
          ref={menuRef}
          className="absolute z-30 bg-[#1a1a2e] border border-slate-700 rounded-lg shadow-xl py-1 min-w-[160px]"
          style={{ top: menuPos.top - 10, left: menuPos.left - 170 }}
          data-testid="table-row-context-menu"
        >
          {MENU_ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => handleAction(item.action)}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
              data-testid={`table-row-${item.key}`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          ))}
        </div>
      )}
    </>
  );
};
