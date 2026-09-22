"""
AI Writing Assistant (Phase 3 of the help-doc-v3 feature port).

Ported from help-doc-v3's three assistant surfaces:
  - POST /api/generator/markdown  -> here: POST /api/assistant/generate
  - POST /api/assistant/tweak    -> here: POST /api/assistant/tweak (unchanged path)
  - the Writing Assistant's "Chat" mode, which in help-doc-v3 has NO endpoint
    of its own — WritingAssistant.jsx's ChatMode just calls
    POST /api/assistant/tweak with a hand-crafted "respond as a writing
    coach" instruction and displays whatever comes back in the `markdown`
    field (confirmed by reading help-doc-v3's WritingAssistant.jsx in full;
    there is no /api/assistant/chat or similar in help-doc-v3/backend/server.py).
    Trinity gets a real, dedicated `POST /api/assistant/chat` endpoint
    instead of reusing /tweak with a stringified persona — a small
    deliberate improvement, not a straight port: it keeps the wire shape
    honest (a chat reply is not "rewritten markdown") and gives Chat mode
    its own system prompt without having to fight tweak's markdown-only
    framing.

Path choice: help-doc-v3 keeps `/api/generator/markdown` outside its
`/api/assistant/*` family (a leftover of that codebase's flat, one-big-
server.py routing). Trinity's convention is one router-file per feature with
every route sharing that file's prefix (see routes/kb.py -> /api/kb/...,
routes/review.py -> /api/review/...). Renaming it to
POST /api/assistant/generate keeps all three AI-assistant endpoints under
one router/prefix/tag, which is more consistent with that convention than
preserving help-doc-v3's exact path would be.

Auth / gating (Phase 1 philosophy carried forward):
  - Tweak and Chat are content-level AI help — same tier as
    PUT /api/kb/admin/articles/{slug}, which Phase 1 deliberately left open
    to any signed-in user, not just owners. They only touch text the caller
    hands in; they never write to kb_articles or kb_navigation. Gated by
    get_current_user only.
  - Generate (raw notes -> Markdown draft) is the same tier: it returns a
    draft string and touches no collection. Keeping it open to any
    signed-in user lets a non-owner use it for its other real purpose —
    drafting content to paste into an EXISTING article they're allowed to
    edit (Phase 1: content edits are open to everyone), not just for
    drafting brand-new pages.
  - "New Page" mode (turning a generate() draft into an actual new,
    navigable article) is NOT a new endpoint here at all. There is
    deliberately no POST /api/assistant/new-page or similar: the frontend's
    "Use this draft" action in New Page mode does exactly what the manual
    "+" (new page) flow in KBEditor.jsx already does — it pre-fills the
    editor's new-page form (title/content_markdown/target group) with the
    generated draft and routes to the existing /dashboard/kb-editor/new
    flow, whose Save button already calls
    POST /api/kb/admin/articles (routes/kb.py's create_article), which is
    owner-gated via _owner_only() (Phase 1) and already contains the one
    nav-tree-insertion code path (kb.py's create_article body, using
    _find_group()) that places a new page into the tree correctly. This
    router never touches kb_articles/kb_navigation and never duplicates
    that insertion logic — it only ever talks to the LLM. A non-owner who
    drafts a new page via the assistant hits the exact same 403 from
    _owner_only() that a non-owner hitting the manual "+" flow always has,
    the moment they try to Save — there is no assistant-shaped backdoor
    around Phase 1's owner gate.

emergentintegrations: imported lazily INSIDE each handler (not at module
top-level), same as help-doc-v3's server.py does for its /generate,
/mintlify/convert, /generator/markdown and /assistant/tweak handlers (all
four do `from emergentintegrations.llm.chat import LlmChat, UserMessage`
inside the function body, not at import time). Mirroring that here means
this router — and therefore server.py, which imports it unconditionally at
startup — stays importable in any environment that doesn't have the
`emergentintegrations` package installed or EMERGENT_LLM_KEY configured;
only calling one of these three endpoints without both would fail, not
booting the app.
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import EMERGENT_LLM_KEY
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["ai_assistant"])

LLM_MODEL_PROVIDER = "anthropic"
LLM_MODEL_NAME = "claude-sonnet-4-5-20250929"

# ── Trinity's real MDX/markdown component vocabulary ──────────────────────
#
# Confirmed against what actually renders, not help-doc-v3's component list:
#   - frontend/src/components/docs/DocContent.jsx (public-site renderer:
#     Callout + shorthand tags, Steps/Step, CardGroup/Card, Columns,
#     ColumnLayout/Col, Tabs/Tab, Accordion/AccordionItem, YouTube/Loom/
#     Video/Figure, raw <iframe>)
#   - frontend/src/lib/mdx/parser.js (the regex-based extractor that
#     actually decides what is/isn't recognized — this is the ground truth
#     for exact tag/attribute syntax, since a plausible-looking variant the
#     regexes don't match falls through as unrendered literal text)
#   - frontend/src/pages/kb-editor/RichTextEditor.jsx's own markdown-import
#     regexes (what the WYSIWYG editor recognizes when loading content) and
#     its slash-command snippets (e.g. the Tabs snippet is literally
#     `<Tab label="Tab 1">`, confirming `label`, not help-doc-v3's `title`)
#
# Two important divergences from help-doc-v3's component API that would
# silently break rendering if copied verbatim:
#   1. Trinity's <CardGroup> takes NO attributes (no `cols={2}`) — the
#      parser's container regex only matches a bare `<CardGroup>`. Column
#      count for card grids isn't author-controlled.
#   2. Trinity's <Tab> uses `label="..."`, not help-doc-v3's `title="..."`.
#
# Also: Cards nested directly inside <CardGroup> must appear with attributes
# in the exact order title -> icon -> href (all but title optional) because
# extractInnerComponents()'s CardGroup regex is order-sensitive; the
# standalone-<Card> and <Columns>-nested-<Card> regexes are order-agnostic,
# but there's no reason to teach the model two dialects, so the prompt below
# asks for the strict order everywhere.
COMPONENT_GUIDE = """PLATFORM-COMPATIBLE MARKDOWN COMPONENTS (use ONLY these — they render natively; anything else falls through as literal text):
  - Callouts: <Callout type="note|tip|warning|error|info|success|caution|danger" title="Optional">body</Callout>
    Shorthand tags (equivalent to Callout with that type): <Note>, <Info>, <Tip>, <Warning>, <Caution>, <Error>, <Danger>, <Success>.
  - Step-by-step flows (the outer <Steps> tag takes NO attributes):
      <Steps>
      <Step title="Install dependencies" icon="terminal">body</Step>
      <Step title="Run the migration">body</Step>
      </Steps>
    `icon` is optional (a lucide-react icon name, e.g. rocket, terminal, settings, zap, code, book, link).
  - Card grids — <CardGroup> takes NO attributes (never `cols={n}` on CardGroup itself). Every <Card> inside it MUST have its attributes in this exact order — title, then icon, then href, all but title optional:
      <CardGroup>
      <Card title="Heading" icon="rocket" href="/some-page">Short description.</Card>
      </CardGroup>
    Never use emoji for icons — only lucide-react icon names.
  - Side-by-side columns of cards (attribute order on Card is flexible here): <Columns cols={2}>...<Card title="..." icon="..." href="...">...</Card>...</Columns>. `cols` is 1-4.
  - Two or three free-form panes side by side: <ColumnLayout cols={2}><Col>markdown here</Col><Col>markdown here</Col></ColumnLayout>.
  - Tabs — each child is <Tab label="...">, using `label` (NEVER `title`):
      <Tabs>
      <Tab label="JavaScript">
      ```js
      // code
      ```
      </Tab>
      <Tab label="Python">
      ```py
      # code
      ```
      </Tab>
      </Tabs>
  - Accordions — outer <Accordion> takes NO attributes; children are <AccordionItem title="...">body</AccordionItem>:
      <Accordion>
      <AccordionItem title="What if it fails?">body</AccordionItem>
      </Accordion>
  - Media (self-closing tags): <YouTube id="VIDEO_ID" />, <Loom id="ID" />, <Video src="https://..." />, <Figure src="https://..." alt="..." caption="..." />.
  - Raw embeds also render as-is: <iframe src="https://..." title="..." allowfullscreen />.

STRICT RULES:
  1. Do not use Mintlify-style props this platform doesn't parse — no `<CardGroup cols={2}>`, no `<Tab title="...">`. Those exact variants render as broken literal text here.
  2. Do not invent components outside the list above (no <Table>, no custom <Warning type="...">, etc.) — use plain Markdown tables/lists/blockquotes for everything else.
  3. Preserve the author's facts and intent — clarify and restructure, never invent new claims.
  4. Use fenced code blocks with language tags (```bash, ```python, ```javascript, ```json, ```tsx, etc.) and `inline code` for identifiers/commands/flags.
"""


def _strip_code_fence(text: str) -> str:
    """Undo an LLM's habit of wrapping the whole answer in a single
    ```markdown ... ``` fence even when told not to (same defensive cleanup
    help-doc-v3's three markdown-producing handlers all do)."""
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _require_llm_key():
    if not EMERGENT_LLM_KEY:
        # 503, not help-doc-v3's 500 -- this is a configuration gap
        # ("assistant not set up here"), not a server error.
        raise HTTPException(status_code=503, detail="AI assistant is not configured (EMERGENT_LLM_KEY is not set).")


async def _send(system_message: str, user_prompt: str, session_prefix: str) -> str:
    """Shared LlmChat call path for all three endpoints below."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # lazy import — see module docstring

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"{session_prefix}_{uuid.uuid4().hex[:8]}",
        system_message=system_message,
    ).with_model(LLM_MODEL_PROVIDER, LLM_MODEL_NAME)
    response = await chat.send_message(UserMessage(text=user_prompt))
    return _strip_code_fence(response or "")


# ── Tweak ───────────────────────────────────────────────────────────────

class AssistantTweakRequest(BaseModel):
    instruction: str
    markdown: str
    selection: Optional[str] = None  # if set, only this slice is rewritten


@router.post("/tweak")
async def assistant_tweak(body: AssistantTweakRequest, current_user: dict = Depends(get_current_user)):
    """Apply an instruction to an existing piece of markdown. Content-level
    AI help (Phase 1 philosophy): open to any signed-in user, same tier as
    PUT /api/kb/admin/articles/{slug} -- this endpoint never touches
    kb_articles/kb_navigation itself, it only rewrites text handed to it.

    If `selection` is set, only that slice is rewritten (the frontend is
    responsible for substituting the response back into the source at the
    recorded offsets); otherwise the whole `markdown` is the target."""
    _require_llm_key()
    instruction = (body.instruction or "").strip()
    source = (body.selection or body.markdown or "").strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="instruction is required")
    if not source:
        raise HTTPException(status_code=400, detail="markdown is required")
    if len(source) > 40000:
        raise HTTPException(status_code=400, detail="markdown too large (max 40k chars)")

    system_message = (
        "You are a writing assistant inside a documentation editor. The user is editing a Markdown "
        "documentation page and has asked you to apply an instruction to a piece of their content.\n\n"
        "STRICT OUTPUT RULES:\n"
        "1. Output ONLY the rewritten Markdown -- no preface, no explanation, no surrounding code fence.\n"
        "2. Preserve the original structure (heading levels, lists, callouts) unless the instruction asks to change it.\n"
        "3. Keep all factual content the user provided. Do not invent new facts.\n"
        "4. Match the existing voice and tone unless the instruction asks otherwise.\n\n"
        f"{COMPONENT_GUIDE}\n"
        "Keep existing platform components intact; add new ones only where the instruction calls for it. "
        "Do NOT wrap the output in a code fence."
    )
    user_prompt = (
        f"INSTRUCTION:\n{instruction}\n\n"
        f"CONTENT TO REWRITE:\n\"\"\"\n{source}\n\"\"\"\n\n"
        "Now output the rewritten Markdown."
    )

    try:
        out = await _send(system_message, user_prompt, "assist_tweak")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assistant tweak error: {e}")
        raise HTTPException(status_code=500, detail=f"Assistant failed: {e}")

    return {"markdown": out, "applied_to_selection": bool(body.selection)}


# ── Generate (raw notes -> Markdown draft) ────────────────────────────────

class AssistantGenerateRequest(BaseModel):
    raw_input: str
    title: Optional[str] = None
    style: Optional[str] = "documentation"  # "documentation" | "tutorial" | "reference" | "blog"


STYLE_HINTS = {
    "documentation": "Write technical product documentation. Use clear hierarchical headings, short paragraphs, bullet lists where appropriate, and `inline code` for variable names/commands.",
    "tutorial": "Write a step-by-step tutorial. Use numbered headings and a <Steps><Step title=\"...\">...</Step></Steps> block for the main procedure, with fenced code samples in the relevant language.",
    "reference": "Write an API/feature reference. Use H2 sections per endpoint/setting, with Markdown tables for parameters and fenced code examples.",
    "blog": "Write a clear, engaging post. Single implicit H1 (the platform renders the title separately), narrative paragraphs, and supporting subheadings.",
}


@router.post("/generate")
async def assistant_generate(body: AssistantGenerateRequest, current_user: dict = Depends(get_current_user)):
    """Convert raw notes/an outline into polished Markdown. Content-level AI
    help (Phase 1 philosophy): open to any signed-in user -- it returns a
    plain string and never creates or touches an article. This is
    deliberately the SAME endpoint whether the caller intends to paste the
    result into an existing article they're editing (always allowed, Phase
    1) or is drafting a brand-new page (the actual page-creation step is a
    separate, existing, owner-gated call the frontend makes on its own --
    see this module's docstring)."""
    _require_llm_key()
    raw = (body.raw_input or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="raw_input is required")
    if len(raw) > 30000:
        raise HTTPException(status_code=400, detail="raw_input too large (max 30k chars)")

    style_hint = STYLE_HINTS.get(body.style, STYLE_HINTS["documentation"])
    title_hint = f"\nDocument title: {body.title}" if body.title else ""

    system_message = (
        "You are an expert technical writer creating documentation pages for the Emergent platform. "
        "Your task: take the user's raw notes/draft and rewrite them as a polished, well-formatted Markdown document.\n\n"
        "STRICT OUTPUT RULES:\n"
        "1. Output ONLY the Markdown document -- no preface, no explanation, no surrounding code fence.\n"
        "2. Do NOT include a top-level `# Title` heading (the platform renders the title separately). Start at H2.\n\n"
        f"{COMPONENT_GUIDE}\n"
        "RULES OF THUMB:\n"
        "  - Reach for a component only when it meaningfully improves scannability (Steps for a sequence, "
        "CardGroup for parallel options, Callout for an important aside).\n"
        "  - Do NOT wrap the whole document in a code fence."
    )
    user_prompt = (
        f"Style: {style_hint}{title_hint}\n\n"
        f"Raw input from the author:\n\"\"\"\n{raw}\n\"\"\"\n\n"
        "Now produce the polished Markdown document."
    )

    try:
        markdown = await _send(system_message, user_prompt, "gen_md")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assistant generate error: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    return {"markdown": markdown, "title": body.title}


# ── Chat (free-form Q&A about the current doc) ────────────────────────────

class AssistantChatRequest(BaseModel):
    message: str
    markdown: Optional[str] = None  # the doc currently open in the editor, for context


@router.post("/chat")
async def assistant_chat(body: AssistantChatRequest, current_user: dict = Depends(get_current_user)):
    """Free-form writing-coach chat about the article currently open in the
    editor. Content-level AI help (Phase 1 philosophy): open to any
    signed-in user, same tier as /tweak and /generate -- it never touches
    kb_articles/kb_navigation.

    Unlike help-doc-v3 (whose Chat mode calls /assistant/tweak with a
    hand-crafted instruction and reads the answer back out of the
    `markdown` field), this is a real endpoint with its own system prompt
    and its own `reply` field -- see this module's docstring for why."""
    _require_llm_key()
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    if len(message) > 8000:
        raise HTTPException(status_code=400, detail="message too large (max 8k chars)")
    context_doc = (body.markdown or "").strip()
    if len(context_doc) > 40000:
        context_doc = context_doc[:40000]

    system_message = (
        "You are a writing coach embedded in a documentation editor. The user may ask for advice about the "
        "page they currently have open, or ask you to draft/rewrite a piece of it.\n\n"
        "If they're asking for advice or feedback, answer in 2-4 short, direct paragraphs (or a short bulleted "
        "list) -- do not restate the whole document back at them.\n"
        "If they explicitly ask you to rewrite or draft something, output the Markdown for that piece, "
        "using only this platform's component vocabulary:\n\n"
        f"{COMPONENT_GUIDE}"
    )
    doc_context = f"\n\nTHE PAGE THEY CURRENTLY HAVE OPEN:\n\"\"\"\n{context_doc}\n\"\"\"" if context_doc else ""
    user_prompt = f"{message}{doc_context}"

    try:
        reply = await _send(system_message, user_prompt, "assist_chat")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assistant chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Assistant failed: {e}")

    return {"reply": reply}
