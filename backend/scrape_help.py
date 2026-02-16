"""
Browser-based scraper for help.emergent.sh
Extracts all article content as structured JSON.
Read-only - no writes to the source.
"""
import asyncio
import json
import os
import sys

async def main():
    from playwright.async_api import async_playwright
    
    BASE = "https://help.emergent.sh"
    
    # Known page slugs from manual inspection of the sidebar
    PAGES = [
        # The Beginner's Guide
        {"slug": "welcome", "section": "Introduction", "nav": "The Beginner's Guide"},
        {"slug": "your-first-app", "section": "Introduction", "nav": "The Beginner's Guide"},
        {"slug": "plans-and-credits", "section": "Introduction", "nav": "The Beginner's Guide"},
        {"slug": "faqs", "section": "Introduction", "nav": "The Beginner's Guide"},
        # Understanding How Apps Work
        {"slug": "how-do-apps-work", "section": "Understanding How Apps Work", "nav": "The Beginner's Guide"},
        # Features - Core
        {"slug": "voice-mode", "section": "Core Features", "nav": "Features"},
        {"slug": "github-integration", "section": "Core Features", "nav": "Features"},
        {"slug": "universal-key", "section": "Core Features", "nav": "Features"},
        {"slug": "deployment-on-emergent", "section": "Core Features", "nav": "Features"},
        {"slug": "context-limits", "section": "Core Features", "nav": "Features"},
        {"slug": "mobile-app-development", "section": "Core Features", "nav": "Features"},
        {"slug": "teams-plan-collaboration", "section": "Core Features", "nav": "Features"},
        # Features - Advanced
        {"slug": "deployment-types", "section": "Advanced Features", "nav": "Features"},
        {"slug": "rollback-feature", "section": "Advanced Features", "nav": "Features"},
        {"slug": "forking-in-emergent", "section": "Advanced Features", "nav": "Features"},
        {"slug": "mcp", "section": "Advanced Features", "nav": "Features"},
        # Building Your App
        {"slug": "prompting-basics", "section": "Building Your App", "nav": "Building Your App"},
        # Deploy and Manage
        {"slug": "pre-deployment-health-check", "section": "Deploy and Manage", "nav": "Deploy and Manage"},
        # Troubleshooting
        {"slug": "fixing-design-inconsistencies", "section": "Troubleshooting", "nav": "Troubleshooting"},
        {"slug": "missing-app-functionality", "section": "Troubleshooting", "nav": "Troubleshooting"},
        {"slug": "deployment-related-issues", "section": "Troubleshooting", "nav": "Troubleshooting"},
    ]
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        for i, pg in enumerate(PAGES):
            url = f"{BASE}/{pg['slug']}"
            print(f"[{i+1}/{len(PAGES)}] Scraping {pg['slug']}...", flush=True)
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
                # Extract content from the main article area
                content = await page.evaluate("""
                () => {
                    // Get the main content area (middle column)
                    const article = document.querySelector('article') || 
                                    document.querySelector('main') ||
                                    document.querySelector('[class*=content]');
                    if (!article) return null;
                    
                    // Get title from h1
                    const h1 = article.querySelector('h1');
                    const title = h1 ? h1.textContent.trim() : '';
                    
                    // Get breadcrumb/section label
                    const breadcrumb = article.querySelector('[class*=breadcrumb]') || 
                                       article.querySelector('p:first-of-type');
                    
                    // Get all text content structured by headings
                    const sections = [];
                    let currentSection = { heading: '', level: 0, content: [] };
                    
                    const walker = document.createTreeWalker(
                        article,
                        NodeFilter.SHOW_ELEMENT,
                        null,
                        false
                    );
                    
                    let node;
                    while (node = walker.nextNode()) {
                        const tag = node.tagName;
                        
                        if (['H1', 'H2', 'H3', 'H4'].includes(tag)) {
                            if (currentSection.heading || currentSection.content.length > 0) {
                                sections.push({...currentSection, content: currentSection.content.join('\\n')});
                            }
                            currentSection = { 
                                heading: node.textContent.trim(), 
                                level: parseInt(tag[1]),
                                content: [] 
                            };
                        } else if (['P', 'LI', 'PRE', 'BLOCKQUOTE', 'TABLE'].includes(tag)) {
                            const text = node.textContent.trim();
                            if (text && text.length > 0) {
                                // For code blocks, wrap in backticks
                                if (tag === 'PRE') {
                                    currentSection.content.push('```\\n' + text + '\\n```');
                                } else if (tag === 'LI') {
                                    currentSection.content.push('- ' + text);
                                } else if (tag === 'BLOCKQUOTE') {
                                    currentSection.content.push('> ' + text);
                                } else {
                                    currentSection.content.push(text);
                                }
                            }
                        }
                    }
                    
                    // Push last section
                    if (currentSection.heading || currentSection.content.length > 0) {
                        sections.push({...currentSection, content: currentSection.content.join('\\n')});
                    }
                    
                    // Also get the full inner text as fallback
                    const fullText = article.innerText;
                    
                    // Get the "On This Page" sidebar links as TOC
                    const tocLinks = Array.from(document.querySelectorAll('[class*=toc] a, [class*="ON THIS PAGE"] ~ a, aside a'))
                        .filter(a => a.href.includes('#'))
                        .map(a => ({text: a.textContent.trim(), anchor: a.href.split('#')[1] || ''}));
                    
                    return { title, sections, fullText, toc: tocLinks };
                }
                """)
                
                if content and content.get('title'):
                    # Build markdown from sections
                    markdown_parts = []
                    for sec in content.get('sections', []):
                        if sec['heading']:
                            prefix = '#' * sec['level']
                            markdown_parts.append(f"\n{prefix} {sec['heading']}\n")
                        if sec['content']:
                            markdown_parts.append(sec['content'])
                    
                    markdown_body = '\n'.join(markdown_parts).strip()
                    
                    # If markdown is too short, use fullText
                    if len(markdown_body) < 100 and content.get('fullText'):
                        markdown_body = content['fullText'][:20000]
                    
                    result = {
                        "slug": pg['slug'],
                        "title": content['title'],
                        "section": pg['section'],
                        "nav_group": pg['nav'],
                        "url": url,
                        "content_markdown": markdown_body,
                        "toc": content.get('toc', []),
                        "content_length": len(markdown_body),
                    }
                    results.append(result)
                    print(f"  OK: '{content['title']}' ({len(markdown_body)} chars, {len(content.get('sections',[]))} sections)", flush=True)
                else:
                    print(f"  WARN: No content extracted for {pg['slug']}", flush=True)
                    
            except Exception as e:
                print(f"  ERROR: {pg['slug']} - {str(e)[:100]}", flush=True)
        
        await browser.close()
    
    # Also try to discover any pages we missed by checking the sidebar on the last page
    print(f"\nTotal scraped: {len(results)} pages", flush=True)
    
    # Save to JSON
    output_path = "/app/backend/scraped_docs.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to {output_path}", flush=True)
    
    # Print summary
    for r in results:
        print(f"  {r['nav_group']} > {r['section']} > {r['title']} ({r['content_length']} chars)")

if __name__ == "__main__":
    asyncio.run(main())
