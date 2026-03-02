/**
 * Simplified MDX parser - regex-based component extraction and heading TOC generation.
 */

export function parseContent(content) {
  if (!content) return { headings: [], errors: [] };
  const headings = [];
  const regex = /^(#{1,6})\s+(.+)$/gm;
  let match;
  while ((match = regex.exec(content)) !== null) {
    const text = match[2].trim();
    const id = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    headings.push({ level: match[1].length, text, id });
  }
  return { headings, errors: [] };
}

export function generateTOC(headings) {
  const unique = new Map();
  headings.filter(h => h.level >= 2 && h.level <= 3).forEach(h => {
    if (!unique.has(h.id)) unique.set(h.id, { level: h.level, text: h.text, id: h.id });
  });
  return Array.from(unique.values());
}

function dedent(text) {
  if (!text) return text;
  const lines = text.split('\n');
  let minIndent = Infinity;
  for (const line of lines) {
    if (line.trim() === '') continue;
    const indent = line.match(/^(\s*)/)[1].length;
    minIndent = Math.min(minIndent, indent);
  }
  if (minIndent === Infinity || minIndent === 0) return text.trim();
  return lines.map(line => line.slice(minIndent)).join('\n').trim();
}

function parseCardProps(propsString) {
  const props = {};
  const titleMatch = propsString.match(/title="([^"]*)"/);
  if (titleMatch) props.title = titleMatch[1];
  const iconMatch = propsString.match(/icon="([^"]*)"/);
  if (iconMatch) props.icon = iconMatch[1];
  const colorMatch = propsString.match(/color="([^"]*)"/);
  if (colorMatch) props.color = colorMatch[1];
  const hrefMatch = propsString.match(/href="([^"]*)"/);
  if (hrefMatch) props.href = hrefMatch[1];
  return props;
}

function parseIframeProps(propsString) {
  const props = {};
  const srcMatch = propsString.match(/src="([^"]*)"/);
  if (srcMatch) props.src = srcMatch[1];
  const titleMatch = propsString.match(/title="([^"]*)"/);
  if (titleMatch) props.title = titleMatch[1];
  const allowMatch = propsString.match(/allow="([^"]*)"/);
  if (allowMatch) props.allow = allowMatch[1];
  if (propsString.includes('allowfullscreen') || propsString.includes('allowFullScreen')) props.allowFullScreen = true;
  return props;
}

function extractInnerComponents(content, parentType) {
  const patterns = {
    Steps: /<Step\s+title="([^"]*)"(?:\s+icon="([^"]*)")?>([\s\S]*?)<\/Step>/gi,
    CardGroup: /<Card\s+title="([^"]*)"(?:\s+icon="([^"]*)")?(?:\s+href="([^"]*)")?>([\s\S]*?)<\/Card>/gi,
    Tabs: /<Tab\s+label="([^"]*)">([\s\S]*?)<\/Tab>/gi,
    Accordion: /<AccordionItem\s+title="([^"]*)"(?:\s+defaultOpen)?>([\s\S]*?)<\/AccordionItem>/gi,
    AccordionGroup: /<Accordion\s+title="([^"]*)"(?:\s+icon="([^"]*)")?(?:\s+defaultOpen)?>([\s\S]*?)<\/Accordion>/gi,
    CodeGroup: /<Tab\s+label="([^"]*)">([\s\S]*?)<\/Tab>/gi,
  };
  const pattern = patterns[parentType];
  if (!pattern) return [];
  const items = [];
  let m;
  while ((m = pattern.exec(content)) !== null) {
    if (parentType === 'Steps') items.push({ title: m[1], icon: m[2] || null, content: dedent(m[3]) });
    else if (parentType === 'CardGroup') items.push({ title: m[1], icon: m[2] || null, href: m[3] || null, content: dedent(m[4]) });
    else if (parentType === 'Tabs' || parentType === 'CodeGroup') items.push({ label: m[1], content: dedent(m[2]) });
    else if (parentType === 'Accordion') items.push({ title: m[1], defaultOpen: m[0].includes('defaultOpen'), content: dedent(m[2]) });
    else if (parentType === 'AccordionGroup') items.push({ title: m[1], icon: m[2] || null, defaultOpen: m[0].includes('defaultOpen'), content: dedent(m[3]) });
  }
  return items;
}

function extractCardsFromColumns(content) {
  const cards = [];
  const cardRegex = /<Card\s+([^>]*?)>([\s\S]*?)<\/Card>/gi;
  let m;
  while ((m = cardRegex.exec(content)) !== null) {
    cards.push({ ...parseCardProps(m[1]), content: m[2].trim() });
  }
  const iframeRegex = /<iframe\s+([^>]*?)(?:\/>|><\/iframe>|>[\s\S]*?<\/iframe>)/gi;
  while ((m = iframeRegex.exec(content)) !== null) {
    cards.push({ type: 'iframe', ...parseIframeProps(m[1]) });
  }
  return cards;
}

export function extractComponents(content) {
  if (!content) return [];
  const result = [];
  let lastIndex = 0;
  const patterns = [
    { regex: /<(Steps|CardGroup|Tabs|Accordion|CodeGroup|AccordionGroup)>([\s\S]*?)<\/\1>/gi, type: 'container' },
    { regex: /<Columns\s+cols=\{(\d+)\}>([\s\S]*?)<\/Columns>/gi, type: 'columns' },
    { regex: /<ColumnLayout\s+cols=\{(\d+)\}>([\s\S]*?)<\/ColumnLayout>/gi, type: 'column-layout' },
    { regex: /<Callout\s+type="([^"]*)"(?:\s+title="([^"]*)")?>([\s\S]*?)<\/Callout>/gi, type: 'callout' },
    { regex: /<(YouTube|Loom|Video|Figure)\s+([^>]*?)\/>/gi, type: 'media' },
    { regex: /<Card\s+([^>]*?)>([\s\S]*?)<\/Card>/gi, type: 'standalone-card' },
    { regex: /<iframe\s+([^>]*?)(?:\/>|><\/iframe>|>[\s\S]*?<\/iframe>)/gi, type: 'iframe' },
  ];
  const allMatches = [];
  for (const { regex, type } of patterns) {
    let m;
    regex.lastIndex = 0;
    while ((m = regex.exec(content)) !== null) {
      allMatches.push({ type, match: m, index: m.index, length: m[0].length });
    }
  }
  allMatches.sort((a, b) => a.index - b.index);
  for (const item of allMatches) {
    if (item.index < lastIndex) continue;
    if (item.index > lastIndex) {
      const textBefore = content.slice(lastIndex, item.index);
      if (textBefore.trim()) result.push({ type: 'markdown', content: textBefore });
    }
    if (item.type === 'container') {
      result.push({ type: 'component', component: item.match[1], content: item.match[2], children: extractInnerComponents(item.match[2], item.match[1]) });
    } else if (item.type === 'columns') {
      result.push({ type: 'component', component: 'Columns', props: { cols: parseInt(item.match[1], 10) || 2 }, children: extractCardsFromColumns(item.match[2]) });
    } else if (item.type === 'column-layout') {
      const cols = parseInt(item.match[1], 10) || 2;
      const panes = [];
      const colRegex = /<Col>([\s\S]*?)<\/Col>/gi;
      let cm;
      while ((cm = colRegex.exec(item.match[2])) !== null) {
        panes.push(cm[1].trim());
      }
      result.push({ type: 'component', component: 'ColumnLayout', props: { cols }, children: panes });
    } else if (item.type === 'callout') {
      result.push({ type: 'component', component: 'Callout', props: { type: item.match[1], title: item.match[2] }, content: item.match[3].trim() });
    } else if (item.type === 'media') {
      const props = {};
      const propMatches = item.match[2].matchAll(/(\w+)="([^"]*)"/g);
      for (const pm of propMatches) props[pm[1]] = pm[2];
      result.push({ type: 'component', component: item.match[1], props });
    } else if (item.type === 'standalone-card') {
      result.push({ type: 'component', component: 'Card', props: parseCardProps(item.match[1]), content: item.match[2].trim() });
    } else if (item.type === 'iframe') {
      result.push({ type: 'component', component: 'iframe', props: parseIframeProps(item.match[1]) });
    }
    lastIndex = item.index + item.length;
  }
  if (lastIndex < content.length) {
    const remaining = content.slice(lastIndex);
    if (remaining.trim()) result.push({ type: 'markdown', content: remaining });
  }
  return result.length > 0 ? result : [{ type: 'markdown', content }];
}
