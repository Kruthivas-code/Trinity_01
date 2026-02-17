/**
 * DocContent - AST-based MDX content renderer
 * Ported from help.emergent.sh reference
 */
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState, useMemo, useEffect, Children, isValidElement, cloneElement, Fragment } from 'react';
import { Copy, Check, Terminal, FileCode, Info, Lightbulb, AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Steps, Step } from './Steps';
import { Card, CardGroup, Columns } from './Cards';
import { Tabs, Tab } from './Tabs';
import { Accordion, AccordionItem } from './Accordion';
import { extractComponents, parseContent, generateTOC } from '../../lib/mdx/parser';

const codeTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: '#0f172a',
    margin: 0,
    padding: '1rem 1.25rem',
    fontSize: '0.875rem',
    lineHeight: '1.7',
  },
};

const LANG_NAMES = {
  js: 'JavaScript', javascript: 'JavaScript', ts: 'TypeScript', typescript: 'TypeScript',
  jsx: 'JSX', tsx: 'TSX', py: 'Python', python: 'Python',
  bash: 'Bash', sh: 'Shell', shell: 'Shell', json: 'JSON', yaml: 'YAML', yml: 'YAML',
  css: 'CSS', html: 'HTML', sql: 'SQL', go: 'Go', rust: 'Rust', java: 'Java',
  ruby: 'Ruby', php: 'PHP', swift: 'Swift', kotlin: 'Kotlin',
  graphql: 'GraphQL', dockerfile: 'Dockerfile', markdown: 'Markdown', md: 'Markdown',
  xml: 'XML', toml: 'TOML',
};

const CALLOUT_CONFIG = {
  NOTE: { icon: Info, bg: 'bg-blue-500/10', border: 'border-blue-500/30', iconColor: 'text-blue-400', title: 'Note' },
  INFO: { icon: Info, bg: 'bg-blue-500/10', border: 'border-blue-500/30', iconColor: 'text-blue-400', title: 'Info' },
  TIP: { icon: Lightbulb, bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', iconColor: 'text-emerald-400', title: 'Tip' },
  WARNING: { icon: AlertTriangle, bg: 'bg-amber-500/10', border: 'border-amber-500/30', iconColor: 'text-amber-400', title: 'Warning' },
  CAUTION: { icon: AlertTriangle, bg: 'bg-amber-500/10', border: 'border-amber-500/30', iconColor: 'text-amber-400', title: 'Caution' },
  ERROR: { icon: AlertCircle, bg: 'bg-red-500/10', border: 'border-red-500/30', iconColor: 'text-red-400', title: 'Error' },
  DANGER: { icon: AlertCircle, bg: 'bg-red-500/10', border: 'border-red-500/30', iconColor: 'text-red-400', title: 'Danger' },
  SUCCESS: { icon: CheckCircle, bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', iconColor: 'text-emerald-400', title: 'Success' },
};

const CodeBlockRenderer = ({ children, className }) => {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';
  const code = String(children).replace(/\n$/, '');
  const langName = LANG_NAMES[language] || language?.toUpperCase() || 'CODE';
  const isTerminal = ['bash', 'sh', 'shell', 'zsh'].includes(language);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!match) return <code className={className}>{children}</code>;

  return (
    <div className="code-block my-4 rounded-lg overflow-hidden border border-slate-800" data-testid="code-block">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-2 text-slate-400">
          {isTerminal ? <Terminal className="w-4 h-4" /> : <FileCode className="w-4 h-4" />}
          <span className="text-xs font-medium">{langName}</span>
        </div>
        <button onClick={handleCopy} className="flex items-center gap-1.5 px-2 py-1 text-xs text-slate-400 hover:text-white rounded transition-colors" data-testid="copy-code-btn">
          {copied ? <><Check className="w-3.5 h-3.5 text-emerald-400" /><span className="text-emerald-400">Copied</span></> : <><Copy className="w-3.5 h-3.5" /><span>Copy</span></>}
        </button>
      </div>
      <SyntaxHighlighter language={language} style={codeTheme} customStyle={{ margin: 0, borderRadius: 0 }}>
        {code}
      </SyntaxHighlighter>
    </div>
  );
};

const Callout = ({ type, title, children }) => {
  const config = CALLOUT_CONFIG[type?.toUpperCase()] || CALLOUT_CONFIG.NOTE;
  const Icon = config.icon;
  const displayTitle = title || config.title;

  return (
    <div className={`my-6 p-4 rounded-lg border relative z-10 ${config.bg} ${config.border}`} data-testid="callout">
      <div className="flex gap-3">
        <div className={`flex-shrink-0 mt-0.5 ${config.iconColor}`}><Icon className="w-5 h-5" /></div>
        <div className="flex-1 min-w-0">
          {displayTitle && <p className={`font-semibold ${config.iconColor} mb-1`}>{displayTitle}</p>}
          <div className="text-[15px] leading-relaxed text-slate-200 [&>p]:m-0 [&>p:not(:last-child)]:mb-2 [&>div]:text-slate-200">{children}</div>
        </div>
      </div>
    </div>
  );
};

const YouTubeEmbed = ({ id, title }) => {
  if (!id) return null;
  let videoId = id;
  if (id.includes('youtube.com') || id.includes('youtu.be')) {
    const match = id.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    if (match) videoId = match[1];
    else { const short = id.match(/youtu\.be\/([a-zA-Z0-9_-]+)/); if (short) videoId = short[1].split('?')[0]; }
  }
  return (
    <div className="my-6 relative z-10" data-testid="youtube-embed">
      <div className="relative w-full rounded-xl overflow-hidden border border-slate-800 shadow-lg bg-slate-900" style={{ paddingBottom: '56.25%' }}>
        <iframe className="absolute inset-0 w-full h-full" src={`https://www.youtube.com/embed/${videoId}`} title={title || 'Video'} frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen />
      </div>
      {title && title.trim() && <p className="mt-2 text-sm text-slate-400 text-center">{title}</p>}
    </div>
  );
};

const LoomEmbed = ({ id, title }) => {
  if (!id) return null;
  let loomId = id;
  if (id.includes('loom.com')) { const m = id.match(/loom\.com\/(?:share|embed)\/([a-zA-Z0-9]+)/); if (m) loomId = m[1]; }
  return (
    <div className="my-6 relative z-10" data-testid="loom-embed">
      <div className="relative w-full rounded-xl overflow-hidden border border-slate-800 shadow-lg bg-slate-900" style={{ paddingBottom: '56.25%' }}>
        <iframe className="absolute inset-0 w-full h-full" src={`https://www.loom.com/embed/${loomId}`} title={title || 'Video'} frameBorder="0" allowFullScreen />
      </div>
      {title && title.trim() && <p className="mt-2 text-sm text-slate-400 text-center">{title}</p>}
    </div>
  );
};

const Figure = ({ src, alt, caption }) => {
  if (!src) return null;
  return (
    <figure className="my-6 relative z-10" data-testid="figure">
      <div className="rounded-xl overflow-hidden border border-slate-800 shadow-lg bg-slate-900">
        <img src={src} alt={alt || caption || 'Image'} className="w-full h-auto" loading="lazy" />
      </div>
      {caption && caption.trim() && (
        <figcaption className="mt-2 text-sm text-slate-400 text-center">{caption}</figcaption>
      )}
    </figure>
  );
};

const NestedContent = ({ content, mdComponents }) => {
  if (!content) return null;
  const hasCustom = /<(Steps|CardGroup|Columns|Card|Tabs|Accordion|Callout|YouTube|Loom|Video|Figure)/i.test(content) || />\s*\[!(NOTE|TIP|WARNING|CAUTION|ERROR|INFO|SUCCESS)\]/i.test(content);
  if (hasCustom) {
    const parsed = extractComponents(content);
    return <>{parsed.map((block, i) => block.type === 'markdown' ? <ReactMarkdown key={i} remarkPlugins={[remarkGfm]} components={mdComponents}>{block.content}</ReactMarkdown> : <RenderComponent key={i} type={block.component} items={block.children} props={block.props} content={block.content} mdComponents={mdComponents} />)}</>;
  }
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{content}</ReactMarkdown>;
};

const RenderComponent = ({ type, items, props, content, mdComponents }) => {
  switch (type) {
    case 'Steps':
      return <Steps>{items?.map((item, i) => <Step key={i} title={item.title} icon={item.icon}><NestedContent content={item.content} mdComponents={mdComponents} /></Step>)}</Steps>;
    case 'CardGroup':
      return <CardGroup>{items?.map((item, i) => <Card key={i} title={item.title} icon={item.icon} href={item.href} color={item.color}><NestedContent content={item.content} mdComponents={mdComponents} /></Card>)}</CardGroup>;
    case 'Columns':
      return <Columns cols={props?.cols || 2}>{items?.map((item, i) => item.type === 'iframe' ? <div key={i} className="relative w-full aspect-video rounded-xl overflow-hidden"><iframe src={item.src} title={item.title || 'Embedded'} className="absolute inset-0 w-full h-full" frameBorder="0" allowFullScreen /></div> : <Card key={i} title={item.title} icon={item.icon} href={item.href} color={item.color}><NestedContent content={item.content} mdComponents={mdComponents} /></Card>)}</Columns>;
    case 'Card':
      return <div className="my-6"><Card title={props?.title} icon={props?.icon} href={props?.href} color={props?.color}><NestedContent content={content} mdComponents={mdComponents} /></Card></div>;
    case 'iframe':
      return <div className="my-6 relative w-full aspect-video rounded-xl overflow-hidden border border-slate-800"><iframe src={props?.src} title={props?.title || 'Embedded'} className="absolute inset-0 w-full h-full" frameBorder="0" allowFullScreen /></div>;
    case 'Tabs': case 'CodeGroup':
      return <Tabs>{items?.map((item, i) => <Tab key={i} label={item.label}><NestedContent content={item.content} mdComponents={mdComponents} /></Tab>)}</Tabs>;
    case 'Accordion':
      return <Accordion>{items?.map((item, i) => <AccordionItem key={i} title={item.title} defaultOpen={item.defaultOpen}><NestedContent content={item.content} mdComponents={mdComponents} /></AccordionItem>)}</Accordion>;
    case 'AccordionGroup':
      return <Accordion>{items?.map((item, i) => <AccordionItem key={i} title={item.title} defaultOpen={item.defaultOpen}><NestedContent content={item.content} mdComponents={mdComponents} /></AccordionItem>)}</Accordion>;
    case 'Callout':
      return <Callout type={props?.type} title={props?.title}><NestedContent content={content} mdComponents={mdComponents} /></Callout>;
    case 'Info': case 'Note': case 'Tip': case 'Warning': case 'Caution': case 'Error': case 'Danger': case 'Success':
      return <Callout type={type} title={props?.title}><NestedContent content={content} mdComponents={mdComponents} /></Callout>;
    case 'YouTube':
      return <YouTubeEmbed id={props?.id} title={props?.title} />;
    case 'Loom':
      return <LoomEmbed id={props?.id} title={props?.title} />;
    case 'Figure':
      return <Figure src={props?.src} alt={props?.alt} caption={props?.caption} />;
    case 'Video':
      return props?.src ? <Figure src={props?.src} alt={props?.alt} caption={props?.caption || props?.title} /> : null;
    default: return null;
  }
};

export const DocContent = ({ content, className = '', onHeadings }) => {
  // Preprocess content: convert GitHub-style blockquote callouts to <Callout> components
  const preprocessed = useMemo(() => {
    if (!content) return content;
    // Match blockquotes that start with > [!TYPE]
    return content.replace(
      /^(>\s*\[!(NOTE|INFO|TIP|WARNING|CAUTION|ERROR|DANGER|SUCCESS)\])\s*\n((?:>.*\n?)*)/gim,
      (match, marker, type, body) => {
        const cleanBody = body.replace(/^>\s?/gm, '').trim();
        return `<Callout type="${type}">\n${cleanBody}\n</Callout>\n`;
      }
    );
  }, [content]);

  const { sections, headings } = useMemo(() => {
    const parsed = parseContent(preprocessed);
    const sections = extractComponents(preprocessed);
    const toc = generateTOC(parsed.headings);
    return { sections, headings: toc };
  }, [preprocessed]);

  useEffect(() => {
    if (onHeadings && headings.length > 0) onHeadings(headings);
  }, [headings, onHeadings]);

  const mdComponents = useMemo(() => ({
    code: ({ node, inline, className, children, ...props }) => {
      if (inline) return <code className="px-1.5 py-0.5 bg-slate-800 text-pink-400 rounded text-[0.875em] font-mono" {...props}>{children}</code>;
      return <CodeBlockRenderer className={className}>{children}</CodeBlockRenderer>;
    },
    h1: ({ children }) => { const id = String(children).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''); return <h1 id={id} className="scroll-mt-20 !text-white font-bold">{children}</h1>; },
    h2: ({ children }) => { const id = String(children).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''); return <h2 id={id} className="scroll-mt-20 !text-white text-2xl font-semibold mt-10 mb-4">{children}</h2>; },
    h3: ({ children }) => { const id = String(children).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''); return <h3 id={id} className="scroll-mt-20 !text-white text-xl font-semibold mt-8 mb-3">{children}</h3>; },
    h4: ({ children }) => { const id = String(children).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''); return <h4 id={id} className="scroll-mt-20 !text-white text-lg font-semibold mt-6 mb-2">{children}</h4>; },
    blockquote: ({ children }) => {
      return <blockquote className="lead-quote my-6 pl-4 border-l-4 border-indigo-500 italic [&>*]:!text-slate-300 [&_p]:!text-slate-300">{children}</blockquote>;
    },
    table: ({ children }) => <div className="overflow-x-auto my-6 rounded-lg border border-slate-800"><table className="w-full">{children}</table></div>,
    thead: ({ children }) => <thead className="bg-slate-900">{children}</thead>,
    th: ({ children }) => <th className="text-left px-4 py-3 text-sm font-semibold !text-slate-200 border-b border-slate-800">{children}</th>,
    td: ({ children }) => <td className="px-4 py-3 text-sm !text-slate-300 border-b border-slate-800/50">{children}</td>,
    a: ({ href, children }) => { const ext = href?.startsWith('http'); return <a href={href} target={ext ? '_blank' : undefined} rel={ext ? 'noopener noreferrer' : undefined} className="text-[#188455] hover:text-[#1fa968] underline-offset-2 hover:underline">{children}</a>; },
    img: ({ src, alt }) => <img src={src} alt={alt} className="rounded-lg border border-slate-800 my-6 max-w-full" loading="lazy" />,
    hr: () => <hr className="border-slate-800 my-8" />,
    ul: ({ children }) => <ul className="my-4 ml-6 list-disc space-y-2 !text-slate-300">{children}</ul>,
    ol: ({ children }) => <ol className="my-4 ml-6 list-decimal space-y-2 !text-slate-300">{children}</ol>,
    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
    p: ({ children }) => <p className="my-4 leading-relaxed !text-slate-300">{children}</p>,
    strong: ({ children }) => <strong className="font-semibold !text-slate-100">{children}</strong>,
  }), []);

  if (!content) return <div className="text-slate-500 italic" data-testid="doc-empty">No content available.</div>;

  return (
    <div className={`doc-content ${className}`} data-testid="doc-content">
      {sections.map((section, index) => (
        <Fragment key={index}>
          {section.type === 'markdown' ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{section.content}</ReactMarkdown>
          ) : (
            <RenderComponent type={section.component} items={section.children} props={section.props} content={section.content} mdComponents={mdComponents} />
          )}
        </Fragment>
      ))}
    </div>
  );
};

export default DocContent;
