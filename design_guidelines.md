{
  "brand": {
    "product_name": "Trinity",
    "design_direction": "Intercom-style inbox UI (modern, collaborative, conversation-centric)",
    "brand_attributes": [
      "calm under pressure",
      "high-clarity / high-readability",
      "operational and trustworthy",
      "fast scanning for 8+ hour daily use",
      "escalation-first (L1/L2/L3 always visible)"
    ]
  },
  "layout_system": {
    "app_shell": {
      "pattern": "3-zone app shell (Sidebar nav + Inbox/List + Main/Drawer panels)",
      "rules": [
        "Never center the whole app container.",
        "Prefer left-aligned text and controls.",
        "Keep the ticket drawer layout (customer history | conversation | details) intact; only refine spacing/typography/affordances."
      ],
      "grid": {
        "container": "w-full",
        "page_padding": "px-4 sm:px-6 lg:px-8",
        "gutters": "gap-3 sm:gap-4",
        "max_reading_width": "conversation content max-w-[78ch] (keep email/plain text comfortable)"
      },
      "recommended_widths": {
        "sidebar": "w-[272px] (collapsible to w-[72px])",
        "inbox_list": "w-[360px] md:w-[420px]",
        "drawer_customer_history": "w-[320px]",
        "drawer_conversation": "flex-1 min-w-[520px]",
        "drawer_details": "w-[360px]"
      },
      "resizable": {
        "use": "Use shadcn Resizable to allow power users to adjust list vs conversation widths.",
        "component": "/app/frontend/src/components/ui/resizable.jsx",
        "note": "Persist sizes in localStorage per user."
      }
    },
    "information_hierarchy": {
      "primary_focus": "Conversation reply + ticket status",
      "secondary": "Customer context + history",
      "tertiary": "Automation, tags, SLA, internal notes"
    }
  },
  "typography": {
    "font_loading": {
      "google_fonts": [
        "Inter (already present)",
        "Plus Jakarta Sans (already present)"
      ],
      "pairing": {
        "ui": "Inter",
        "brand_wordmark": "Plus Jakarta Sans",
        "mono_optional": "IBM Plex Mono (optional for IDs/log snippets in details panel)"
      }
    },
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl (use only on marketing-like pages; rarely in SaaS)",
      "h2": "text-base md:text-lg (page subheading style per constraints)",
      "app_title": "text-lg sm:text-xl font-semibold tracking-tight",
      "section_title": "text-sm font-semibold text-foreground",
      "table_header": "text-xs font-medium text-muted-foreground uppercase tracking-wide",
      "body": "text-base (mobile: text-sm) leading-6",
      "list_primary": "text-sm sm:text-base font-medium leading-5",
      "list_secondary": "text-xs sm:text-sm text-muted-foreground leading-5",
      "meta": "text-xs text-muted-foreground",
      "conversation": "text-sm sm:text-base leading-7 (increase line-height for plain-text emails)",
      "input": "text-sm sm:text-base",
      "button": "text-sm sm:text-base font-medium"
    },
    "readability_rules": [
      "Default body text must be at least text-sm on mobile and text-base on desktop.",
      "Conversation pane: line-height must feel airy (leading-7) with generous paragraph spacing.",
      "Never use low-contrast muted text for primary info (subject, sender, status).",
      "Use tabular-nums for timestamps and SLA metrics (Tailwind: tabular-nums)."
    ]
  },
  "color_system": {
    "mode": "Light theme as primary (white/black) with subtle neutral surfaces; dark mode remains but redesign targets light-first clarity.",
    "semantic_tokens": {
      "background": "hsl(var(--background))",
      "foreground": "hsl(var(--foreground))",
      "surface": "hsl(var(--card))",
      "surface_2": "hsl(var(--secondary))",
      "border": "hsl(var(--border))",
      "muted_text": "hsl(var(--muted-foreground))",
      "focus_ring": "hsl(var(--ring))"
    },
    "accent_strategy": {
      "goal": "Intercom-like: mostly monochrome UI, accent used sparingly for selection, focus, and key states.",
      "accent_color": "Use the existing dark charcoal primary in light mode. Add ONE additional calm accent for status highlights only: ocean-teal 187/48-ish but at low saturation in light mode.",
      "do_not": [
        "Do not introduce purple.",
        "Do not use saturated gradients on content areas."
      ]
    },
    "l1_l2_l3_palette": {
      "rule": "Escalation levels must be instantly recognizable in sidebar + list badges + kanban tags.",
      "tokens": {
        "l1": {
          "label": "L1",
          "bg": "bg-emerald-50",
          "text": "text-emerald-800",
          "border": "border-emerald-200",
          "dot": "bg-emerald-500"
        },
        "l2": {
          "label": "L2",
          "bg": "bg-amber-50",
          "text": "text-amber-900",
          "border": "border-amber-200",
          "dot": "bg-amber-500"
        },
        "l3": {
          "label": "L3",
          "bg": "bg-rose-50",
          "text": "text-rose-800",
          "border": "border-rose-200",
          "dot": "bg-rose-500"
        }
      },
      "accessibility": "Ensure badge text meets AA; if on tinted bg, use darker text (800/900)."
    },
    "status_palette": {
      "todo": "slate",
      "in_progress": "blue",
      "waiting": "amber",
      "review": "violet (solid only, NOT gradient; keep very muted)",
      "resolved": "emerald",
      "note": "Avoid heavy color fills; prefer left border + small chip + subtle column header tint."
    },
    "gradients_texture": {
      "policy": "Gradients are decorative only and must cover <20% viewport.",
      "allowed_usage": [
        "Top-of-app subtle radial wash behind header only",
        "Kanban empty state backdrop only"
      ],
      "allowed_examples": {
        "hero_wash": "background: radial-gradient(900px circle at 12% 0%, rgba(13,101,118,0.08), transparent 55%), radial-gradient(700px circle at 88% 10%, rgba(15,23,42,0.04), transparent 45%);"
      },
      "texture": "Add a subtle noise overlay via CSS on large backgrounds only (opacity 0.03–0.05)."
    }
  },
  "design_tokens_css": {
    "instruction": "Main agent should implement/adjust tokens in /app/frontend/src/index.css under .light primarily (keep existing structure).",
    "additions": {
      "spacing": {
        "--space-1": "0.25rem",
        "--space-2": "0.5rem",
        "--space-3": "0.75rem",
        "--space-4": "1rem",
        "--space-5": "1.25rem",
        "--space-6": "1.5rem",
        "--space-8": "2rem"
      },
      "radius": {
        "--radius-sm": "10px",
        "--radius-md": "14px",
        "--radius-lg": "18px"
      },
      "shadow": {
        "--shadow-1": "0 1px 2px rgba(0,0,0,0.06)",
        "--shadow-2": "0 6px 18px rgba(0,0,0,0.08)",
        "--shadow-focus": "0 0 0 4px hsl(var(--ring) / 0.18)"
      }
    }
  },
  "components": {
    "primary_component_sources": {
      "shadcn_ui": "/app/frontend/src/components/ui",
      "toasts": "/app/frontend/src/components/ui/sonner.jsx"
    },
    "component_path": {
      "app_sidebar": [
        "/app/frontend/src/components/ui/scroll-area.jsx",
        "/app/frontend/src/components/ui/collapsible.jsx",
        "/app/frontend/src/components/ui/separator.jsx",
        "/app/frontend/src/components/ui/badge.jsx",
        "/app/frontend/src/components/ui/tooltip.jsx"
      ],
      "command_palette": [
        "/app/frontend/src/components/ui/command.jsx",
        "/app/frontend/src/components/ui/dialog.jsx"
      ],
      "ticket_list": [
        "/app/frontend/src/components/ui/input.jsx",
        "/app/frontend/src/components/ui/tabs.jsx",
        "/app/frontend/src/components/ui/scroll-area.jsx",
        "/app/frontend/src/components/ui/avatar.jsx",
        "/app/frontend/src/components/ui/badge.jsx",
        "/app/frontend/src/components/ui/skeleton.jsx"
      ],
      "ticket_drawer": [
        "/app/frontend/src/components/ui/drawer.jsx",
        "/app/frontend/src/components/ui/resizable.jsx",
        "/app/frontend/src/components/ui/tabs.jsx",
        "/app/frontend/src/components/ui/textarea.jsx",
        "/app/frontend/src/components/ui/hover-card.jsx"
      ],
      "kanban": [
        "/app/frontend/src/components/ui/card.jsx",
        "/app/frontend/src/components/ui/badge.jsx",
        "/app/frontend/src/components/ui/dropdown-menu.jsx",
        "/app/frontend/src/components/ui/tooltip.jsx"
      ],
      "analytics": [
        "/app/frontend/src/components/ui/card.jsx",
        "/app/frontend/src/components/ui/tabs.jsx",
        "/app/frontend/src/components/ui/select.jsx",
        "/app/frontend/src/components/ui/table.jsx"
      ],
      "forms": [
        "/app/frontend/src/components/ui/form.jsx",
        "/app/frontend/src/components/ui/label.jsx",
        "/app/frontend/src/components/ui/input.jsx",
        "/app/frontend/src/components/ui/textarea.jsx",
        "/app/frontend/src/components/ui/switch.jsx",
        "/app/frontend/src/components/ui/checkbox.jsx"
      ],
      "dialogs_sheets": [
        "/app/frontend/src/components/ui/dialog.jsx",
        "/app/frontend/src/components/ui/sheet.jsx",
        "/app/frontend/src/components/ui/alert-dialog.jsx"
      ],
      "calendar_leave": [
        "/app/frontend/src/components/ui/calendar.jsx",
        "/app/frontend/src/components/ui/popover.jsx"
      ]
    },
    "button_rules_intercom_style": {
      "source": "https://developers.intercom.com/docs/canvas-kit/canvas-kit-inbox-best-practices",
      "rules": [
        "Avoid primary buttons in surfaces that load by default (e.g., right details panel cards). Use secondary/link by default.",
        "Use primary only inside an active flow (e.g., when composing a reply, submitting escalation, saving canned response).",
        "Use link-style buttons for navigation actions like Back/Cancel/Done.",
        "Separate navigation actions from content with a divider/spacer; place at bottom of card/panel."
      ]
    }
  },
  "page_blueprints": {
    "login": {
      "layout": "Split screen: left brand + reassurance, right auth card (no heavy gradients)",
      "components": ["Card", "Form", "Input", "Button"],
      "details": [
        "Increase input height: h-11 sm:h-12, text-base",
        "Use subtle security microcopy in muted text"
      ]
    },
    "all_tickets_inbox": {
      "layout": "3-column: sidebar folders | conversation list | conversation/drawer",
      "conversation_list": {
        "row_height": "min-h-[76px] (larger target)",
        "row_structure": [
          "Top line: subject (font-medium)",
          "Second line: last message preview (muted)",
          "Right meta: absolute timestamp + SLA chip"
        ],
        "states": [
          "Unread: left 2px border + slightly stronger subject weight",
          "Selected: bg-secondary + ring-1 ring-border",
          "Hover: bg-muted/60"
        ]
      },
      "filters": "Tabs: All/Open/Waiting/Closed/Starred; add search input with Command-K hint",
      "empty_state": "Left-aligned muted paragraph, with an action link (per Intercom empty state guidance)"
    },
    "ticket_drawer": {
      "layout": "Resizable 3-panel drawer",
      "conversation": {
        "plain_text_rendering": [
          "Use <pre> styled for wrapping: whitespace-pre-wrap break-words font-sans",
          "Apply leading-7 and paragraph spacing (space-y-4)"
        ],
        "composer": [
          "Pinned at bottom with subtle top border",
          "Primary action: Send",
          "Secondary: Add note, Attach, Canned responses"
        ]
      },
      "details_panel": {
        "pattern": "Stacked cards with progressive disclosure (Collapsible sections)",
        "first_canvas_rule": "Default view shows only most relevant blocks (SLA, priority, owner); advanced blocks behind collapsibles"
      }
    },
    "kanban_dashboard": {
      "layout": "Horizontal scroll board on mobile; full columns on desktop",
      "column_style": "Header sticky with subtle tint; cards white with hairline border",
      "drag": "Use existing DnD; add drop indicator (2px outline + subtle scale)"
    },
    "analytics": {
      "layout": "Card grid + table drilldown",
      "charts": "Use Recharts for time series and stacked bars",
      "key_metrics": [
        "First response time",
        "Time to resolve",
        "Escalation rate L1→L2→L3",
        "Backlog by folder",
        "Agent load"
      ]
    }
  },
  "interaction_design": {
    "micro_interactions": {
      "hover": [
        "List rows: background-color transition 160ms",
        "Buttons: shadow + background-color 160ms",
        "Badges: border-color 160ms"
      ],
      "press": "Buttons scale- [0.98] with transition-transform 120ms (only on press state)",
      "focus": "Use .focus-ring utility (already present) + visible ring on inputs and list rows",
      "scroll": "Use ScrollArea; keep custom scrollbar subtle",
      "loading": "Use Skeleton rows in list and conversation blocks"
    },
    "motion_principles": {
      "entrance": "Use existing .animate-fade-in-up for column and drawer content; stagger list load",
      "reduce_motion": "Respect prefers-reduced-motion (already in index.css)",
      "never": [
        "Never use transition: all",
        "Avoid large parallax in productivity views"
      ]
    }
  },
  "testing_attributes": {
    "rule": "All interactive and key informational elements MUST include data-testid (kebab-case).",
    "examples": [
      "data-testid=sidebar-l1-folder-button",
      "data-testid=ticket-list-search-input",
      "data-testid=ticket-row-<id>",
      "data-testid=ticket-drawer-send-reply-button",
      "data-testid=kanban-column-in-progress",
      "data-testid=analytics-first-response-time-card",
      "data-testid=command-palette-trigger"
    ]
  },
  "l1_l2_l3_sidebar_rules": {
    "structure": [
      "Folders section: L1, L2, L3 (Collapsible groups)",
      "Within each: Open, Waiting, Needs review, Resolved",
      "Each folder shows count badge (monochrome) + level chip (colored)"
    ],
    "interaction": [
      "Drag ticket to a level folder to escalate (show drop target highlight)",
      "Right-click context menu: Escalate → L2/L3, Assign, Mark waiting",
      "Keyboard: use Command palette to jump to any folder (type 'L2 waiting')"
    ],
    "visual": [
      "Level chips always visible in sidebar labels",
      "Use small colored dot + text (avoid big color blocks)"
    ]
  },
  "libraries": {
    "recharts": {
      "why": "Analytics dashboard charts",
      "install": "npm i recharts",
      "usage_notes": [
        "Prefer subtle gridlines: stroke=\"hsl(var(--border))\"",
        "Use tooltip with Card-like surface",
        "Keep axes labels text-xs text-muted-foreground"
      ]
    },
    "framer_motion": {
      "why": "Drawer transitions, list item subtle entrance, drag affordances",
      "install": "npm i framer-motion",
      "usage_notes": [
        "Keep durations 0.16–0.24s",
        "Use opacity + y 8px for entrance",
        "Avoid overly springy motion in enterprise contexts"
      ]
    }
  },
  "image_urls": {
    "policy": "This is a SaaS app; avoid decorative stock photos inside operational screens. Use illustrations only in empty states.",
    "empty_state_illustrations": [
      {
        "category": "empty-state",
        "description": "Subtle monochrome inbox illustration (used in marketing/login only; in-app empty states should be text-first)",
        "url": "https://images.unsplash.com/photo-1557682250-33bd709cbe85?auto=format&fit=crop&w=1200&q=60"
      }
    ],
    "login_background": [
      {
        "category": "login",
        "description": "Light texture background (very subtle; apply opacity 0.08)",
        "url": "https://images.unsplash.com/photo-1528459801416-a9e53bbf4e17?auto=format&fit=crop&w=1600&q=60"
      }
    ]
  },
  "instructions_to_main_agent": [
    "Prioritize light theme: enforce larger font sizes in ticket list, conversation, and sidebars.",
    "Implement L1/L2/L3 as first-class folder groups in the sidebar with chips + counts; never hide them under a menu.",
    "Adopt Intercom button hierarchy: avoid primary CTAs in default-loaded context panels; primary reserved for active flows (reply, save, submit).",
    "Use progressive disclosure in details panel (Collapsible) to avoid overwhelming the agent; default to essential blocks only.",
    "Ensure every interactive element and critical info has data-testid in kebab-case.",
    "Keep gradients extremely subtle and decorative only; do not place gradients behind dense text.",
    "Prefer ScrollArea for all long panes (sidebar, list, conversation, details)."
  ],
  "appendix_general_ui_ux_design_guidelines": "<General UI UX Design Guidelines>  \n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
