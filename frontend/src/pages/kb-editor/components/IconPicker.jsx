/**
 * IconPicker — Reusable icon selection dropdown for the KB Editor.
 * Shows a searchable grid of Lucide icons with theme support.
 */
import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { icons } from 'lucide-react';
import { Search, X } from 'lucide-react';

// All icon entries: [PascalName, Component]
const ALL_ICONS = Object.entries(icons);

// Convert PascalCase → kebab-case for storage
const toKebab = (name) => name.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();

// Popular icons shown first (before search)
const POPULAR = [
  'Rocket', 'Code', 'Zap', 'Star', 'Globe', 'Shield', 'Database', 'Terminal',
  'FileText', 'BookOpen', 'Layers', 'CreditCard', 'Sparkles', 'Lightbulb',
  'Puzzle', 'Wrench', 'Users', 'Heart', 'Settings', 'Lock', 'Key', 'Mail',
  'Bell', 'Camera', 'Cloud', 'Download', 'Upload', 'Eye', 'Gift', 'Home',
  'Image', 'Link', 'Map', 'Monitor', 'Music', 'Package', 'Phone', 'Printer',
  'Search', 'Send', 'Server', 'Share2', 'ShoppingCart', 'Smartphone', 'Speaker',
  'Tag', 'Trash2', 'Truck', 'Tv', 'Video', 'Wifi', 'Award', 'BarChart',
  'Battery', 'Bluetooth', 'Bookmark', 'Box', 'Briefcase', 'Calendar', 'Check',
  'Clock', 'Compass', 'Cpu', 'Disc', 'DollarSign', 'Edit', 'ExternalLink',
  'File', 'Filter', 'Flag', 'Folder', 'Grid', 'Hash', 'Headphones',
  'HelpCircle', 'Inbox', 'Info', 'Layout', 'LifeBuoy', 'List', 'Loader',
  'MapPin', 'Maximize', 'Mic', 'Moon', 'Navigation', 'Paperclip', 'Pen',
  'Percent', 'Play', 'Plus', 'Power', 'Radio', 'RefreshCw', 'Save',
  'Scissors', 'Shield', 'Shuffle', 'Sidebar', 'Sliders', 'Sun', 'Table',
  'Target', 'Thermometer', 'ThumbsUp', 'ToggleLeft', 'Tool', 'Umbrella',
  'Unlock', 'User', 'Volume2', 'Watch', 'Wind', 'XCircle', 'Aperture',
  'AtSign', 'Binary', 'Bot', 'Brain', 'Bug', 'Building', 'ChartBar',
  'CircleCheck', 'Cog', 'Command', 'Crown', 'Diamond', 'Flame', 'Gamepad2',
  'Gauge', 'Gem', 'GitBranch', 'Glasses', 'GraduationCap', 'Hammer',
  'Handshake', 'HardDrive', 'Hexagon', 'Infinity', 'Joystick', 'Keyboard',
  'Lamp', 'Laptop', 'Leaf', 'Library', 'Magnet', 'Medal', 'Megaphone',
  'MessageCircle', 'Milestone', 'Mountain', 'MousePointer', 'Network',
  'Newspaper', 'Palette', 'PanelLeft', 'PartyPopper', 'PenTool', 'Pill',
  'Pizza', 'Plug', 'Receipt', 'Repeat', 'Rocket', 'Rss', 'Ruler',
  'Scale', 'ScanLine', 'School', 'ScrollText', 'Ship', 'Shirt', 'Signal',
  'Siren', 'Skull', 'Snowflake', 'Sofa', 'Stamp', 'Store', 'Swords',
  'Telescope', 'Timer', 'Trophy', 'Wand2', 'Warehouse', 'Webhook', 'Workflow',
];

const PAGE_SIZE = 120;

const IconPicker = ({ value, onChange, isLight }) => {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const containerRef = useRef(null);
  const pickerRef = useRef(null);

  // Resolve current icon
  const currentPascal = value
    ? value.split('-').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join('')
    : null;
  const CurrentIcon = currentPascal ? icons[currentPascal] : null;

  // Filtered icon list
  const filteredIcons = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) {
      // Show popular icons first, then the rest
      const popularSet = new Set(POPULAR);
      const popular = POPULAR.map(name => [name, icons[name]]).filter(([, c]) => c);
      const rest = ALL_ICONS.filter(([name]) => !popularSet.has(name));
      return [...popular, ...rest];
    }
    return ALL_ICONS.filter(([name]) => name.toLowerCase().includes(q));
  }, [search]);

  const displayedIcons = filteredIcons.slice(0, visibleCount);

  const handleSelect = useCallback((pascalName) => {
    onChange(toKebab(pascalName));
    setOpen(false);
    setSearch('');
    setVisibleCount(PAGE_SIZE);
  }, [onChange]);

  const handleRemove = useCallback(() => {
    onChange('');
    setOpen(false);
    setSearch('');
  }, [onChange]);

  // Infinite scroll
  const handleScroll = useCallback((e) => {
    const el = e.target;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 100) {
      setVisibleCount(prev => Math.min(prev + PAGE_SIZE, filteredIcons.length));
    }
  }, [filteredIcons.length]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setOpen(false);
        setSearch('');
        setVisibleCount(PAGE_SIZE);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className="relative" ref={pickerRef} data-testid="icon-picker">
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center gap-2 px-2.5 py-1.5 border rounded-lg text-xs transition-colors ${
          isLight
            ? 'bg-gray-50 border-gray-200 text-gray-900 hover:border-gray-300'
            : 'bg-slate-800 border-slate-700 text-white hover:border-slate-600'
        }`}
        data-testid="icon-picker-trigger"
      >
        {CurrentIcon ? (
          <>
            <CurrentIcon className="w-4 h-4 text-[#00A1B2] flex-shrink-0" />
            <span className="truncate">{value}</span>
          </>
        ) : (
          <span className={isLight ? 'text-gray-400' : 'text-slate-500'}>Select icon...</span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className={`absolute z-[100] mt-1 left-0 right-0 border rounded-xl shadow-2xl overflow-hidden ${
            isLight ? 'bg-white border-gray-200' : 'bg-[#1a1a1a] border-white/10'
          }`}
          style={{ width: '280px' }}
          data-testid="icon-picker-dropdown"
        >
          {/* Header */}
          <div className={`flex items-center justify-between px-3 pt-3 pb-2 ${isLight ? 'text-gray-900' : 'text-white'}`}>
            <span className="text-xs font-semibold">Icons</span>
            <button
              onClick={handleRemove}
              className="text-[10px] font-medium text-red-400 hover:text-red-300 transition-colors"
              data-testid="icon-picker-remove"
            >
              Remove
            </button>
          </div>

          {/* Search */}
          <div className="px-3 pb-2">
            <div className={`flex items-center gap-2 px-2.5 py-1.5 border rounded-lg ${
              isLight ? 'bg-gray-50 border-gray-200' : 'bg-slate-800 border-slate-700'
            }`}>
              <Search className={`w-3.5 h-3.5 flex-shrink-0 ${isLight ? 'text-gray-400' : 'text-slate-500'}`} />
              <input
                value={search}
                onChange={(e) => { setSearch(e.target.value); setVisibleCount(PAGE_SIZE); }}
                placeholder="Search icons..."
                className={`bg-transparent outline-none text-xs w-full ${isLight ? 'text-gray-900 placeholder:text-gray-400' : 'text-white placeholder:text-slate-500'}`}
                autoFocus
                data-testid="icon-picker-search"
              />
              {search && (
                <button onClick={() => setSearch('')} className={isLight ? 'text-gray-400' : 'text-slate-500'}>
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {/* Icon grid */}
          <div
            className="px-3 pb-3 overflow-y-auto"
            style={{ maxHeight: '240px' }}
            onScroll={handleScroll}
            ref={containerRef}
            data-testid="icon-picker-grid"
          >
            {displayedIcons.length === 0 ? (
              <p className={`text-xs text-center py-4 ${isLight ? 'text-gray-400' : 'text-slate-500'}`}>No icons found</p>
            ) : (
              <div className="grid grid-cols-8 gap-0.5">
                {displayedIcons.map(([name, IconComp]) => {
                  const kebab = toKebab(name);
                  const isSelected = kebab === value;
                  return (
                    <button
                      key={name}
                      type="button"
                      onClick={() => handleSelect(name)}
                      title={name}
                      className={`p-1.5 rounded-md flex items-center justify-center transition-colors ${
                        isSelected
                          ? 'bg-[#00A1B2]/20 text-[#00A1B2] ring-1 ring-[#00A1B2]/40'
                          : isLight
                            ? 'text-gray-500 hover:bg-gray-100 hover:text-gray-900'
                            : 'text-slate-400 hover:bg-white/10 hover:text-white'
                      }`}
                      data-testid={`icon-option-${kebab}`}
                    >
                      <IconComp size={16} strokeWidth={1.5} />
                    </button>
                  );
                })}
              </div>
            )}
            {visibleCount < filteredIcons.length && (
              <p className={`text-[10px] text-center py-2 ${isLight ? 'text-gray-400' : 'text-slate-500'}`}>
                Showing {visibleCount} of {filteredIcons.length} — scroll for more
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default IconPicker;
