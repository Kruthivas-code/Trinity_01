{
  "meta": {
    "product": "TickFlow",
    "app_type": "Ticket management Kanban web app",
    "brand_attributes": ["sleek", "modern", "precise", "calm confidence", "performance-first"],
    "style": "Dark theme with glassmorphism accents (blurred, frosted panels on matte dark backdrop). High-contrast, compact density, space-efficient." 
  },

  "typography": {
    "font_import": "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap",
    "font_stack": {
      "display": "\"Space Grotesk\", ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Inter, \"Helvetica Neue\", Arial, \"Noto Sans\", \"Apple Color Emoji\", \"Segoe UI Emoji\"",
      "body": "Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, \"Helvetica Neue\", Arial, \"Noto Sans\""
    },
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight",
      "h2": "text-base md:text-lg font-medium",
      "body": "text-sm md:text-base",
      "small": "text-xs md:text-sm text-muted-foreground"
    }
  },

  "color_system": {
    "semantic_tokens_hsl": {
      "--background": "222 28% 6%", 
      "--foreground": "210 25% 96%",
      "--card": "222 28% 8%",
      "--card-foreground": "210 25% 96%",
      "--popover": "222 28% 8%",
      "--popover-foreground": "210 25% 96%",
      "--primary": "194 85% 56%", 
      "--primary-foreground": "210 40% 8%",
      "--secondary": "210 14% 18%",
      "--secondary-foreground": "210 25% 96%",
      "--muted": "215 16% 14%",
      "--muted-foreground": "215 12% 65%",
      "--accent": "188 72% 40%", 
      "--accent-foreground": "210 40% 10%",
      "--destructive": "3 83% 55%",
      "--destructive-foreground": "0 0% 98%",
      "--border": "215 16% 22%",
      "--input": "215 16% 22%",
      "--ring": "190 90% 55%",
      "--radius": "0.7rem"
    },
    "glass_tokens": {
      "--glass-bg": "hsla(210, 18%, 12%, 0.55)",
      "--glass-elevated-bg": "hsla(210, 18%, 16%, 0.55)",
      "--glass-border": "hsla(195, 25%, 85%, 0.18)",
      "--glass-ring": "hsla(194, 85%, 56%, 0.45)",
      "--glass-shadow": "0 8px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.06)"
    },
    "gradient_palette": {
      "ocean_mist": "linear-gradient(135deg, rgba(17,24,39,0) 0%, rgba(13,101,118,0.22) 35%, rgba(65,148,196,0.22) 70%, rgba(17,24,39,0) 100%)",
      "slate_to_teal": "linear-gradient(120deg, rgba(24,32,45,0.0) 0%, rgba(26,71,84,0.22) 50%, rgba(24,32,45,0.0) 100%)",
      "enforcement": "Use gradients only on section backgrounds or large decorative layers. Never exceed 20% viewport coverage; never on text-heavy blocks; never on small UI elements (<100px)."
    }
  },

  "tokens_css": {
    "snippet": """
@layer base { 
  :root { 
    --background: 222 28% 6%;
    --foreground: 210 25% 96%;
    --card: 222 28% 8%;
    --card-foreground: 210 25% 96%;
    --popover: 222 28% 8%;
    --popover-foreground: 210 25% 96%;
    --primary: 194 85% 56%;
    --primary-foreground: 210 40% 8%;
    --secondary: 210 14% 18%;
    --secondary-foreground: 210 25% 96%;
    --muted: 215 16% 14%;
    --muted-foreground: 215 12% 65%;
    --accent: 188 72% 40%;
    --accent-foreground: 210 40% 10%;
    --destructive: 3 83% 55%;
    --destructive-foreground: 0 0% 98%;
    --border: 215 16% 22%;
    --input: 215 16% 22%;
    --ring: 190 90% 55%;
    --radius: 0.7rem;

    --glass-bg: hsla(210, 18%, 12%, 0.55);
    --glass-elevated-bg: hsla(210, 18%, 16%, 0.55);
    --glass-border: hsla(195, 25%, 85%, 0.18);
    --glass-ring: hsla(194, 85%, 56%, 0.45);
    --glass-shadow: 0 8px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.06);
  }
}

/* Glass utilities */
.glass { 
  background: var(--glass-bg);
  backdrop-filter: saturate(140%) blur(14px);
  -webkit-backdrop-filter: saturate(140%) blur(14px);
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
}
.glass-elevated { background: var(--glass-elevated-bg); }

/* Avoid center-aligning app container per guideline */
/* Do not add .App { text-align:center } */
"""
  },

  "layout": {
    "header": {
      "structure": "Top sticky glass header with app name, analytics badges, search/command, import/export, user menu",
      "classes": "sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150",
      "children": [
        "Brand at left (Space Grotesk) with subtle ocean_mist gradient underline",
        "Search/Command palette trigger (Command from shadcn)",
        "Analytics badges (Badge) for total tickets, my tickets",
        "Export/Import (Button variants)",
        "User avatar menu (DropdownMenu + Avatar)"
      ]
    },
    "kanban": {
      "columns": ["Backlog", "To Do", "In Progress", "Review", "Done"],
      "behavior": "5 side-by-side glass columns. Horizontal scroll on small screens with snap; resizable widths on desktop; virtualized lists inside each column; smooth dnd-kit between columns.",
      "wrapper_classes": "relative h-[calc(100vh-72px)] overflow-x-auto overflow-y-hidden snap-x snap-mandatory",
      "track_classes": "flex h-full gap-4 px-4 pb-6",
      "column_classes": "glass min-w-[320px] md:min-w-[360px] lg:min-w-[380px] snap-start rounded-xl border border-border/60 flex flex-col",
      "column_header_classes": "px-4 py-3 flex items-center justify-between sticky top-0 z-10 bg-transparent backdrop-blur",
      "list_container_classes": "flex-1 overflow-y-auto pr-1",
      "dnd": {
        "virtualization": "react-window FixedSizeList per column with overscanCount=6; use DragOverlay for smooth drag ghost",
        "collision": "closestCorners for inter-column moves; pointerWithin for dense lists",
        "sensors": "Pointer + Keyboard sensors from dnd-kit"
      }
    },
    "auth": {
      "layout": "Split background with subtle gradient accent and centered glass card",
      "card_classes": "glass max-w-md w-full mx-auto rounded-2xl p-6 md:p-8 border border-border/60",
      "form_controls": "space-y-4"
    }
  },

  "buttons": {
    "style_family": "Glass / Neomorphic",
    "tokens": {
      "--btn-radius": "0.75rem",
      "--btn-shadow": "0 4px 16px rgba(0,0,0,0.25)",
      "--btn-motion": "cubic-bezier(0.2, 0.8, 0.2, 1)"
    },
    "variants": {
      "primary": "bg-primary text-primary-foreground hover:bg-cyan-400/90 active:scale-[0.985] focus-visible:ring-2 focus-visible:ring-cyan-300",
      "secondary": "bg-secondary/70 text-secondary-foreground hover:bg-secondary/90 border border-white/10",
      "ghost": "bg-transparent hover:bg-white/5 border border-transparent"
    },
    "sizes": {
      "sm": "h-9 px-3 rounded-[var(--btn-radius)]",
      "md": "h-10 px-4 rounded-[var(--btn-radius)]",
      "lg": "h-12 px-5 rounded-[var(--btn-radius)]"
    }
  },

  "components": {
    "paths": {
      "button": "./components/ui/button.jsx",
      "badge": "./components/ui/badge.jsx",
      "drawer": "./components/ui/drawer.jsx",
      "sheet": "./components/ui/sheet.jsx",
      "dialog": "./components/ui/dialog.jsx",
      "skeleton": "./components/ui/skeleton.jsx",
      "card": "./components/ui/card.jsx",
      "avatar": "./components/ui/avatar.jsx",
      "dropdown_menu": "./components/ui/dropdown-menu.jsx",
      "command": "./components/ui/command.jsx",
      "input": "./components/ui/input.jsx",
      "textarea": "./components/ui/textarea.jsx",
      "select": "./components/ui/select.jsx",
      "switch": "./components/ui/switch.jsx",
      "tooltip": "./components/ui/tooltip.jsx",
      "sonner": "./components/ui/sonner.jsx",
      "resizable": "./components/ui/resizable.jsx",
      "scroll_area": "./components/ui/scroll-area.jsx",
      "sheet_component": "./components/ui/sheet.jsx"
    },
    "recipes": {
      "header": {
        "structure": ["Brand", "Search/Command", "Badges", "Import/Export", "UserMenu"],
        "example": """
<header class=\"glass border-b border-border/60\">
  <div class=\"mx-auto max-w-[1600px] px-4 h-16 flex items-center justify-between\">
    <div class=\"flex items-center gap-3\">
      <span class=\"text-lg font-semibold tracking-tight\" data-testid=\"app-brand\">TickFlow</span>
      <div class=\"hidden md:flex gap-2\">
        <span class=\"text-xs text-muted-foreground\" data-testid=\"badge-total\">Total: 1,204</span>
        <span class=\"text-xs text-muted-foreground\" data-testid=\"badge-mine\">Mine: 238</span>
      </div>
    </div>
    <div class=\"flex items-center gap-2\">
      <!-- Command palette trigger -->
      <button class=\"h-9 px-3 rounded-lg glass border border-white/10 text-sm\" data-testid=\"command-trigger\">⌘K</button>
      <button class=\"h-9 px-3 rounded-lg bg-primary text-primary-foreground\" data-testid=\"export-button\">Export</button>
      <button class=\"h-9 px-3 rounded-lg bg-secondary/70\" data-testid=\"import-button\">Import</button>
      <!-- User menu via DropdownMenu + Avatar -->
    </div>
  </div>
</header>
"""
      },
      "ticket_card": {
        "layout": "Compact glass card: title, assignee avatar+name, priority dot, small badges.",
        "classes": "glass rounded-xl p-3 border hover:border-white/20 transition-colors duration-200",
        "example": """
function TicketCard({ item, onOpen }) {
  return (
    <button
      className=\"w-full text-left glass rounded-xl p-3 border hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--glass-ring)]\"
      onClick={() => onOpen(item)}
      data-testid=\"ticket-card\"
    >
      <div className=\"flex items-center justify-between gap-2\">
        <h4 className=\"text-sm font-medium line-clamp-2\" data-testid=\"ticket-title\">{item.title}</h4>
        <span className=\"shrink-0 w-2.5 h-2.5 rounded-full\" style={{background:item.priorityColor}} data-testid=\"ticket-priority-dot\" />
      </div>
      <div className=\"mt-2 flex items-center gap-2 text-xs text-muted-foreground\">
        <img src={item.assigneeAvatar} alt=\"\" className=\"w-5 h-5 rounded-full\" />
        <span data-testid=\"ticket-assignee\">{item.assignee}</span>
      </div>
    </button>
  )
}
"""
      },
      "drawer_detail": {
        "description": "Right-side drawer with full ticket details and actions.",
        "example": """
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerFooter } from \"./components/ui/drawer\";
import { Button } from \"./components/ui/button\";

function TicketDrawer({ open, onOpenChange, ticket }) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className=\"glass-elevated border-l border-border/60\" side=\"right\" data-testid=\"ticket-drawer\"> 
        <DrawerHeader>
          <DrawerTitle className=\"font-semibold text-base\" data-testid=\"drawer-title\">{ticket?.title}</DrawerTitle>
        </DrawerHeader>
        <div className=\"px-6 pb-6 space-y-6\">
          {/* details... */}
        </div>
        <DrawerFooter className=\"px-6 pb-6\">
          <Button data-testid=\"drawer-save-button\">Save</Button>
          <Button variant=\"ghost\" data-testid=\"drawer-close-button\" onClick={() => onOpenChange(false)}>Close</Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  )
}
"""
      },
      "virtualized_kanban_js": {
        "notes": "Use dnd-kit + react-window; DragOverlay for glossy ghost; FixedSizeList itemSize ~84 for compact cards.",
        "example": """
import React from \"react\";
import { DndContext, DragOverlay, closestCorners, PointerSensor, useSensor, useSensors } from \"@dnd-kit/core\";
import { SortableContext, verticalListSortingStrategy, arrayMove } from \"@dnd-kit/sortable\";
import { FixedSizeList as List } from \"react-window\";
import { useDroppable } from \"@dnd-kit/core\";

function SortableItem({ id, item, style }) {
  return (
    <div style={style} className=\"px-2\" data-testid=\"sortable-item\">
      <div className=\"\">
        <TicketCard item={item} onOpen={() => {}} />
      </div>
    </div>
  );
}

function VirtualizedColumn({ columnId, itemIds, items, height }) {
  const { setNodeRef } = useDroppable({ id: columnId });

  const Row = ({ index, style }) => {
    const id = itemIds[index];
    return <SortableItem id={id} item={items[id]} style={style} />
  };

  return (
    <div ref={setNodeRef} className=\"glass rounded-xl border border-border/60 flex flex-col min-w-[360px]\" data-testid={\`kanban-column-\${columnId}\`}> 
      <div className=\"px-4 py-3 sticky top-0 z-10 bg-transparent backdrop-blur flex items-center justify-between\">
        <h3 className=\"text-sm font-medium\">{columnId}</h3>
        <span className=\"text-xs text-muted-foreground\" data-testid=\"column-count\">{itemIds.length}</span>
      </div>
      <div className=\"flex-1 overflow-y-auto pr-1\">
        <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
          <List height={height} itemCount={itemIds.length} itemSize={84} width={\"100%\"} overscanCount={6}>
            {Row}
          </List>
        </SortableContext>
      </div>
    </div>
  );
}

export default function KanbanBoard({ columns, items }) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const [activeId, setActiveId] = React.useState(null);

  function findContainer(id) {
    for (const [key, ids] of Object.entries(columns)) if (ids.includes(id)) return key;
    return id;
  }

  function onDragStart({ active }) { setActiveId(active.id); }

  function onDragEnd({ active, over }) {
    setActiveId(null);
    if (!over) return;
    const from = findContainer(active.id);
    const to = findContainer(over.id);
    if (from && to) {
      if (from === to) {
        const oldIndex = columns[from].indexOf(active.id);
        const newIndex = columns[to].indexOf(over.id);
        columns[from] = arrayMove(columns[from], oldIndex, newIndex);
      } else {
        const fromItems = [...columns[from]];
        const toItems = [...columns[to]];
        fromItems.splice(fromItems.indexOf(active.id), 1);
        const overIndex = Math.max(0, toItems.indexOf(over.id));
        toItems.splice(overIndex, 0, active.id);
        columns = { ...columns, [from]: fromItems, [to]: toItems };
      }
    }
  }

  const listHeight = typeof window !== 'undefined' ? window.innerHeight - 160 : 600;

  return (
    <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={onDragStart} onDragEnd={onDragEnd}>
      <div className=\"relative h-[calc(100vh-72px)] overflow-x-auto overflow-y-hidden\">
        <div className=\"flex h-full gap-4 px-4 pb-6\" data-testid=\"kanban-track\"> 
          {Object.entries(columns).map(([col, ids]) => (
            <VirtualizedColumn key={col} columnId={col} itemIds={ids} items={items} height={listHeight} />
          ))}
        </div>
      </div>
      <DragOverlay>{activeId ? <div className=\"glass rounded-xl p-3\"><span className=\"text-xs\">Dragging...</span></div> : null}</DragOverlay>
    </DndContext>
  );
}
"""
      },
      "empty_state": {
        "example": """
<div className=\"flex flex-col items-center justify-center text-center p-6 text-muted-foreground\" data-testid=\"empty-state\">
  <div className=\"w-16 h-16 rounded-xl glass flex items-center justify-center mb-3\">💼</div>
  <p className=\"text-sm\">No tickets yet</p>
  <button className=\"mt-3 h-9 px-3 rounded-lg bg-primary text-primary-foreground\" data-testid=\"empty-add-ticket\">Create ticket</button>
</div>
"""
      },
      "skeleton_card": {
        "example": """
import { Skeleton } from \"./components/ui/skeleton\";

function TicketSkeleton() {
  return (
    <div className=\"glass rounded-xl p-3 border\" data-testid=\"ticket-skeleton\"> 
      <Skeleton className=\"h-4 w-3/4\" />
      <div className=\"mt-3 flex items-center gap-2\">
        <Skeleton className=\"h-5 w-5 rounded-full\" />
        <Skeleton className=\"h-3 w-20\" />
      </div>
    </div>
  );
}
"""
      }
    }
  },

  "micro_interactions": {
    "hover": "Cards: border-white/20 on hover; Buttons: subtle shade shift; No universal transition, only color/background/box-shadow transitions.",
    "drag": "Elevate dragged item via DragOverlay with slight scale(1.02) and glow ring var(--glass-ring).",
    "entrance": "Framer Motion: columns fade+rise 12px; cards stagger 18ms per card.",
    "scroll": "Header reduces blur intensity on scroll; columns support subtle inertial snap on mobile."
  },

  "accessibility": {
    "contrast": "All text meets AA on dark glass. Primary cyan on dark background must have >=4.5:1 for body-size text.",
    "focus": "Always render focus-visible rings (ring-2 ring-cyan-300).",
    "motion": "Respect prefers-reduced-motion: disable entrance animations and parallax.",
    "screenreader": "Announce column counts, drag start/destination via aria-live polite.",
    "testing_attributes": "All interactive and key informational elements MUST include data-testid attributes using kebab-case describing role."
  },

  "libraries": {
    "install": [
      "npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities react-window",
      "npm install framer-motion",
      "npm install lucide-react"
    ],
    "usage_notes": [
      "Use FixedSizeList for stable virtualization; if variable heights become necessary, switch to @tanstack/react-virtual.",
      "Use shadcn Drawer/Sheet for edit/create flows; never raw HTML modals.",
      "Use sonner for toasts (see ./components/ui/sonner.jsx)."
    ]
  },

  "grid_system": {
    "container": "mx-auto max-w-[1600px] px-4",
    "spacing": "Use 2–3x whitespace vs typical dashboards. Column gap 1rem–1.25rem; inside card padding 0.75rem–1rem.",
    "radius": "Use --radius = 0.7rem as base; columns rounded-xl; buttons 0.75rem."
  },

  "image_urls": [
    {
      "url": "https://images.pexels.com/photos/28428587/pexels-photo-28428587.jpeg",
      "category": "accent-background",
      "description": "Dark abstract with soft spheres; use as subtle hero/header decorative background overlay under 20% viewport coverage"
    },
    {
      "url": "https://images.pexels.com/photos/5829761/pexels-photo-5829761.jpeg",
      "category": "glass-texture",
      "description": "Frosted / fog gradient texture; use as noise overlay masked inside columns at low opacity (6–10%)."
    }
  ],

  "testing_data_testids": [
    "app-brand",
    "command-trigger",
    "export-button",
    "import-button",
    "kanban-track",
    "kanban-column-backlog",
    "kanban-column-to-do",
    "kanban-column-in-progress",
    "kanban-column-review",
    "kanban-column-done",
    "ticket-card",
    "ticket-title",
    "ticket-assignee",
    "ticket-priority-dot",
    "ticket-skeleton",
    "empty-state",
    "empty-add-ticket",
    "drawer-title",
    "drawer-save-button",
    "drawer-close-button"
  ],

  "empty_and_loading": {
    "empty_column": "Centered glass icon tile + copy + primary button. Ensure space for quick-add.",
    "skeletons": "Use Skeleton components in lists at mount and during pagination."
  },

  "forms": {
    "create_edit": {
      "pattern": "Prefer Drawer (right) on desktop; Sheet on mobile; Dialog for destructive confirms only.",
      "fields": ["title", "description", "status", "assignee", "priority", "labels", "attachments"],
      "components": ["input", "textarea", "select", "avatar", "badge", "button"]
    },
    "auth": {
      "layout": "Glass card with Input, Password, Button; visible focus state; remember me Switch",
      "data_testids": ["login-email-input", "login-password-input", "login-submit-button", "register-submit-button"]
    }
  },

  "motion": {
    "durations": { "fast": 120, "base": 220, "slow": 340 },
    "easing": "cubic-bezier(0.2,0.8,0.2,1)",
    "rules": [
      "Never apply transition: all; restrict to color/background/box-shadow/opacity.",
      "Drag overlay scale 1.02 with subtle glow; drop snaps to position over 140ms."
    ]
  },

  "instructions_to_main_agent": [
    "1) Update src/index.css tokens to the semantic dark palette + glass tokens from tokens_css.snippet.",
    "2) Build Header using shadcn Button, DropdownMenu, Avatar, Command; apply data-testid attributes.",
    "3) Implement KanbanBoard.js using dnd-kit + react-window per the virtualized_kanban_js example; ensure columns list matches Backlog → To Do → In Progress → Review → Done.",
    "4) Implement TicketCard.js using the glass classes and ensure compact height (~72–84px).",
    "5) Add TicketDrawer.js using shadcn Drawer with Save/Close actions and testids.",
    "6) Add Empty and Skeleton states to each column.",
    "7) Ensure mobile: columns become horizontally scrollable with snap; keep min-w 320–380px.",
    "8) Add analytics badges in header; hook to real counts later.",
    "9) Integrate Sonner toasts for success/error.",
    "10) Enforce gradient restriction rule; only use gradient overlays like ocean_mist at low opacity on header background.",
    "11) All interactive elements must include data-testid in kebab-case."
  ],

  "component_path": [
    "./components/ui/button.jsx",
    "./components/ui/badge.jsx",
    "./components/ui/drawer.jsx",
    "./components/ui/sheet.jsx",
    "./components/ui/dialog.jsx",
    "./components/ui/skeleton.jsx",
    "./components/ui/card.jsx",
    "./components/ui/avatar.jsx",
    "./components/ui/dropdown-menu.jsx",
    "./components/ui/command.jsx",
    "./components/ui/input.jsx",
    "./components/ui/textarea.jsx",
    "./components/ui/select.jsx",
    "./components/ui/switch.jsx",
    "./components/ui/tooltip.jsx",
    "./components/ui/sonner.jsx",
    "./components/ui/resizable.jsx",
    "./components/ui/scroll-area.jsx"
  ]
}


<General UI UX Design Guidelines>  
    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms
    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text
   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json

 **GRADIENT RESTRICTION RULE**
NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc
NEVER use dark gradients for logo, testimonial, footer etc
NEVER let gradients cover more than 20% of the viewport.
NEVER apply gradients to text-heavy content or reading areas.
NEVER use gradients on small UI elements (<100px width).
NEVER stack multiple gradient layers in the same viewport.

**ENFORCEMENT RULE:**
    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors

**How and where to use:**
   • Section backgrounds (not content backgrounds)
   • Hero section header content. Eg: dark to light to dark color
   • Decorative overlays and accent elements only
   • Hero section with 2-3 mild color
   • Gradients creation can be done for any angle say horizontal, vertical or diagonal

- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**

</Font Guidelines>

- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. 
   
- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.

- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.
   
- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly
    Eg: - if it implies playful/energetic, choose a colorful scheme
           - if it implies monochrome/minimal, choose a black–white/neutral scheme

**Component Reuse:**
	- Prioritize using pre-existing components from src/components/ui when applicable
	- Create new components that match the style and conventions of existing components when needed
	- Examine existing components to understand the project's component patterns before creating new ones

**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component

**Best Practices:**
	- Use Shadcn/UI as the primary component library for consistency and accessibility
	- Import path: ./components/[component-name]

**Export Conventions:**
	- Components MUST use named exports (export const ComponentName = ...)
	- Pages MUST use default exports (export default function PageName() {...})

**Toasts:**
  - Use `sonner` for toasts"  
  - Sonner component are located in `/app/src/components/ui/sonner.tsx`

Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.
</General UI UX Design Guidelines>