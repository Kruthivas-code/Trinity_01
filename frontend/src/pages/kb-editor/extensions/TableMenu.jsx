/**
 * TableMenu — Floating grip handles + drag-and-drop reorder + context menu
 * for table row operations in the TipTap editor.
 *
 * Grip handles appear on ALL data rows when the cursor is inside a table.
 * - Click a grip  → context menu (insert / move / copy / delete)
 * - Drag a grip   → reorder the row with visual drop-indicator feedback
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  GripVertical, Plus, ArrowUp, ArrowDown, Copy, Trash2
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Context-menu items                                                 */
/* ------------------------------------------------------------------ */
const MENU_ITEMS = [
  { key: 'insertBefore', label: 'Insert before', icon: Plus, action: 'addRowBefore' },
  { key: 'insertAfter', label: 'Insert after', icon: Plus, action: 'addRowAfter' },
  { key: 'moveUp', label: 'Move up', icon: ArrowUp, action: 'moveRowUp' },
  { key: 'moveDown', label: 'Move down', icon: ArrowDown, action: 'moveRowDown' },
  { key: 'copyRow', label: 'Copy row', icon: Copy, action: 'copyRow' },
  { key: 'deleteRow', label: 'Delete row', icon: Trash2, action: 'deleteRow', danger: true },
];

/* ------------------------------------------------------------------ */
/*  ProseMirror helpers                                                */
/* ------------------------------------------------------------------ */

/** Reorder a table row from `fromIndex` to `toIndex` (final position). */
const reorderRow = (editor, tableEl, fromIndex, toIndex) => {
  if (fromIndex === toIndex || fromIndex < 1 || toIndex < 1) return;
  if (!tableEl || !editor) return;

  try {
    const pos = editor.view.posAtDOM(tableEl, 0);
    const $pos = editor.state.doc.resolve(pos);

    let tableNode = null;
    let tablePos = null;
    for (let d = $pos.depth; d >= 0; d--) {
      if ($pos.node(d).type.name === 'table') {
        tableNode = $pos.node(d);
        tablePos = $pos.before(d);
        break;
      }
    }
    if (!tableNode) return;
    if (fromIndex >= tableNode.childCount || toIndex >= tableNode.childCount) return;

    const rows = [];
    for (let i = 0; i < tableNode.childCount; i++) rows.push(tableNode.child(i));

    const [moved] = rows.splice(fromIndex, 1);
    rows.splice(toIndex, 0, moved);

    const newTable = tableNode.type.create(tableNode.attrs, rows);
    const { tr } = editor.state;
    tr.replaceWith(tablePos, tablePos + tableNode.nodeSize, newTable);
    editor.view.dispatch(tr);
  } catch (e) {
    console.error('Failed to reorder row:', e);
  }
};

/** Move a single row up or down by 1 (menu action, uses current selection). */
const moveRow = (editor, direction) => {
  const { $from } = editor.state.selection;
  let rowDepth = null;
  for (let d = $from.depth; d > 0; d--) {
    if ($from.node(d).type.name === 'tableRow') { rowDepth = d; break; }
  }
  if (rowDepth === null) return;

  const tableDepth = rowDepth - 1;
  const table = $from.node(tableDepth);
  const rowIndex = $from.index(tableDepth);
  const target = direction === 'up' ? rowIndex - 1 : rowIndex + 1;
  if (target < 1 || target >= table.childCount) return;

  const { tr } = editor.state;
  const tableStart = $from.start(tableDepth);
  let pos = tableStart;
  const rp = [];
  for (let i = 0; i < table.childCount; i++) {
    rp.push({ start: pos, size: table.child(i).nodeSize });
    pos += table.child(i).nodeSize;
  }

  const rowNode = table.child(rowIndex);
  const tgtNode = table.child(target);
  if (direction === 'up') {
    tr.replaceWith(rp[target].start, rp[target].start + rp[target].size, rowNode);
    tr.replaceWith(rp[rowIndex].start, rp[rowIndex].start + rp[rowIndex].size, tgtNode);
  } else {
    tr.replaceWith(rp[rowIndex].start, rp[rowIndex].start + rp[rowIndex].size, tgtNode);
    tr.replaceWith(rp[target].start, rp[target].start + rp[target].size, rowNode);
  }
  editor.view.dispatch(tr);
};

/** Duplicate the current row (uses current selection). */
const copyRow = (editor) => {
  const { $from } = editor.state.selection;
  let rowDepth = null;
  for (let d = $from.depth; d > 0; d--) {
    if ($from.node(d).type.name === 'tableRow') { rowDepth = d; break; }
  }
  if (rowDepth === null) return;

  const tableDepth = rowDepth - 1;
  const table = $from.node(tableDepth);
  const rowIndex = $from.index(tableDepth);
  const rowNode = table.child(rowIndex);
  const tableStart = $from.start(tableDepth);

  let insertPos = tableStart;
  for (let i = 0; i <= rowIndex; i++) insertPos += table.child(i).nodeSize;

  const cells = [];
  rowNode.forEach(cell => {
    cells.push(editor.schema.nodes.tableCell.create(cell.attrs, cell.content));
  });
  const newRow = editor.schema.nodes.tableRow.create(null, cells);
  const { tr } = editor.state;
  tr.insert(insertPos, newRow);
  editor.view.dispatch(tr);
};

/** Move editor cursor into the first cell of a given <tr> DOM element. */
const focusInRow = (editor, rowEl) => {
  if (!rowEl) return;
  const cell = rowEl.querySelector('td, th');
  if (!cell) return;
  try {
    const pos = editor.view.posAtDOM(cell, 0);
    editor.commands.setTextSelection(pos + 1);
    editor.commands.focus();
  } catch {}
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export const TableRowMenu = ({ editor, theme }) => {
  const [rowInfos, setRowInfos] = useState([]);
  const [activeRowIdx, setActiveRowIdx] = useState(null);
  const [showMenu, setShowMenu] = useState(false);

  const [isDragging, setIsDragging] = useState(false);
  const [dragFrom, setDragFrom] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);

  const menuRef = useRef(null);
  const tableElRef = useRef(null);
  const rowInfosRef = useRef([]);
  const dragFromRef = useRef(null);
  const dropTargetRef = useRef(null);

  useEffect(() => { rowInfosRef.current = rowInfos; }, [rowInfos]);
  useEffect(() => { dragFromRef.current = dragFrom; }, [dragFrom]);
  useEffect(() => { dropTargetRef.current = dropTarget; }, [dropTarget]);

  /* ---- Track table rows when cursor moves ---- */
  useEffect(() => {
    if (!editor) return;
    const update = () => {
      if (dragFromRef.current !== null) return; // skip while dragging

      const { $from } = editor.state.selection;
      let inTable = false;
      for (let d = $from.depth; d > 0; d--) {
        if ($from.node(d).type.name === 'tableRow') { inTable = true; break; }
      }
      if (!inTable) {
        tableElRef.current = null;
        setRowInfos([]);
        setActiveRowIdx(null);
        setShowMenu(false);
        return;
      }

      const domAtPos = editor.view.domAtPos($from.pos);
      let rowEl = domAtPos.node;
      while (rowEl && rowEl.tagName !== 'TR') rowEl = rowEl.parentElement;
      if (!rowEl) return;

      const tableEl = rowEl.closest('table');
      if (!tableEl) return;
      tableElRef.current = tableEl;

      const tableRect = tableEl.getBoundingClientRect();
      const allTrs = tableEl.querySelectorAll('tr');
      const infos = [];
      let curIdx = null;

      allTrs.forEach((tr, i) => {
        const rect = tr.getBoundingClientRect();
        infos.push({
          el: tr,
          top: rect.top - tableRect.top,
          height: rect.height,
          absTop: rect.top,
          absBottom: rect.bottom,
          isHeader: tr.querySelector('th') !== null,
          index: i,
        });
        if (tr === rowEl) curIdx = i;
      });

      setRowInfos(infos);
      setActiveRowIdx(curIdx);
    };

    editor.on('selectionUpdate', update);
    editor.on('transaction', update);
    return () => {
      editor.off('selectionUpdate', update);
      editor.off('transaction', update);
    };
  }, [editor]);

  /* ---- Close menu on outside click ---- */
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  /* ---- Context-menu action handler ---- */
  const handleAction = useCallback((action) => {
    if (!editor) return;
    switch (action) {
      case 'addRowBefore': editor.chain().focus().addRowBefore().run(); break;
      case 'addRowAfter':  editor.chain().focus().addRowAfter().run(); break;
      case 'moveRowUp':    moveRow(editor, 'up'); break;
      case 'moveRowDown':  moveRow(editor, 'down'); break;
      case 'copyRow':      copyRow(editor); break;
      case 'deleteRow':    editor.chain().focus().deleteRow().run(); break;
      default: break;
    }
    setShowMenu(false);
  }, [editor]);

  /* ---- Grip mousedown: distinguish click vs. drag ---- */
  const handleGripMouseDown = useCallback((rowIndex, rowEl, e) => {
    e.preventDefault();
    e.stopPropagation();
    const startY = e.clientY;
    let dragging = false;

    const onMove = (me) => {
      if (!dragging && Math.abs(me.clientY - startY) > 5) {
        dragging = true;
        setIsDragging(true);
        setDragFrom(rowIndex);
        setDropTarget(rowIndex);
        dropTargetRef.current = rowIndex;
        document.body.style.cursor = 'grabbing';
        document.body.style.userSelect = 'none';
      }
      if (dragging) {
        const infos = rowInfosRef.current;
        const mouseY = me.clientY;
        const dataRows = infos.filter(r => !r.isHeader);
        if (dataRows.length === 0) return;

        let target = rowIndex;
        // Find which row the mouse is currently over
        for (const row of dataRows) {
          if (mouseY >= row.absTop && mouseY < row.absBottom) {
            target = row.index;
            break;
          }
        }
        // Edge: above first data row
        if (mouseY < dataRows[0].absTop) target = dataRows[0].index;
        // Edge: below last data row
        if (mouseY >= dataRows[dataRows.length - 1].absBottom) target = dataRows[dataRows.length - 1].index;

        setDropTarget(target);
        dropTargetRef.current = target;
      }
    };

    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';

      if (dragging) {
        const from = dragFromRef.current;
        const to = dropTargetRef.current;
        setIsDragging(false);
        setDragFrom(null);
        setDropTarget(null);
        if (from !== null && to !== null && from !== to) {
          reorderRow(editor, tableElRef.current, from, to);
          // Focus the moved row after DOM updates
          setTimeout(() => {
            try {
              const tEl = tableElRef.current;
              if (tEl) {
                const trs = tEl.querySelectorAll('tr');
                if (trs[to]) focusInRow(editor, trs[to]);
              }
            } catch {}
          }, 20);
        }
      } else {
        // Click → focus row + show context menu
        if (editor && rowEl) {
          focusInRow(editor, rowEl);
          setTimeout(() => setShowMenu(true), 50);
        }
      }
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [editor]);

  /* ---- Derived theme values ---- */
  const isDark = theme?.id === 'dark';

  /* ---- Render nothing if no table ---- */
  if (rowInfos.length === 0) return null;

  /* ---- Drop-indicator position ---- */
  let dropLineTop = null;
  if (isDragging && dropTarget !== null && dragFrom !== null && dropTarget !== dragFrom) {
    const tgtRow = rowInfos[dropTarget];
    if (tgtRow) {
      dropLineTop = dropTarget < dragFrom
        ? tgtRow.top - 1
        : tgtRow.top + tgtRow.height - 1;
    }
  }

  /* ---- Compute context menu position: left on wide screens, right on narrow ---- */
  const getMenuPos = () => {
    if (!showMenu || activeRowIdx === null || !rowInfos[activeRowIdx]) return {};
    const row = rowInfos[activeRowIdx];
    const top = row.top + row.height / 2 - 10;
    const tableLeft = tableElRef.current?.getBoundingClientRect()?.left ?? 300;
    return tableLeft < 220
      ? { top, left: 8 }
      : { top, left: -198 };
  };

  return (
    <>
      {/* ---- Grip handles (all data rows) ---- */}
      {rowInfos.filter(r => !r.isHeader).map(row => (
        <div
          key={row.index}
          onMouseDown={(e) => handleGripMouseDown(row.index, row.el, e)}
          className={[
            'absolute z-20 p-0.5 rounded transition-opacity duration-150',
            isDragging && dragFrom === row.index
              ? 'cursor-grabbing opacity-100'
              : 'cursor-grab',
            !isDragging && activeRowIdx === row.index
              ? 'opacity-100'
              : !isDragging ? 'opacity-30 hover:opacity-100' : 'opacity-50',
          ].join(' ')}
          style={{ top: row.top + row.height / 2 - 10, left: -28 }}
          title="Drag to reorder or click for options"
          data-testid={`table-row-grip-${row.index}`}
        >
          <GripVertical className={`w-4 h-4 ${isDark ? 'text-emerald-400' : 'text-[#00A1B2]'}`} />
        </div>
      ))}

      {/* ---- Drag source highlight ---- */}
      {isDragging && dragFrom !== null && rowInfos[dragFrom] && (
        <div
          className="absolute z-10 rounded pointer-events-none"
          style={{
            left: 0,
            right: 0,
            top: rowInfos[dragFrom].top,
            height: rowInfos[dragFrom].height,
            background: isDark ? 'rgba(16,185,129,0.08)' : 'rgba(0,161,178,0.08)',
            border: isDark ? '1px solid rgba(16,185,129,0.25)' : '1px solid rgba(0,161,178,0.25)',
          }}
          data-testid="drag-source-highlight"
        />
      )}

      {/* ---- Drop indicator line ---- */}
      {isDragging && dropLineTop !== null && (
        <div
          className="absolute z-30 pointer-events-none"
          style={{ left: 0, right: 0, top: dropLineTop }}
          data-testid="drop-indicator"
        >
          <div className={`h-0.5 rounded-full ${isDark ? 'bg-emerald-400' : 'bg-[#00A1B2]'}`} />
          <div className={`absolute -left-1.5 -top-[3px] w-2 h-2 rounded-full ${isDark ? 'bg-emerald-400' : 'bg-[#00A1B2]'}`} />
          <div className={`absolute -right-1.5 -top-[3px] w-2 h-2 rounded-full ${isDark ? 'bg-emerald-400' : 'bg-[#00A1B2]'}`} />
        </div>
      )}

      {/* ---- Context menu ---- */}
      {showMenu && !isDragging && activeRowIdx !== null && rowInfos[activeRowIdx] && !rowInfos[activeRowIdx].isHeader && (
        <div
          ref={menuRef}
          className={`absolute z-30 rounded-lg shadow-xl py-1 min-w-[160px] border ${isDark ? 'bg-[#1a1a2e] border-slate-700' : 'bg-white border-gray-200'}`}
          style={getMenuPos()}
          data-testid="table-row-context-menu"
        >
          {MENU_ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => handleAction(item.action)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm transition-colors ${
                item.danger
                  ? 'text-red-400 hover:bg-red-500/10 hover:text-red-300'
                  : isDark
                    ? 'text-slate-300 hover:bg-white/10 hover:text-white'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
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
