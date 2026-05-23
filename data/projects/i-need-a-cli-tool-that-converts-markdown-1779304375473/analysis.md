# Markdown-to-PDF CLI Tool

## The Problem
No straightforward CLI for converting markdown to polished PDF reports with consistent branding. Teams either use manual tools (requiring design skills) or generic converters that can't match org styling. This tool adds automated, themeable conversion with built-in TOC, headers, and footers.

## Hard Constraints
- Installable via npm (Node.js runtime required)
- No additional constraints stated

## Open Questions
- **Markdown flavor**: CommonMark, GitHub Flavored, or extended syntax?
- **Theme system**: CSS-based, YAML templates, or built-in presets only?
- **PDF library**: pdfkit, Puppeteer, wkhtmltopdf, or pinecone? (headless browser dependency acceptable?)
- **Configuration**: File-based (JSON/YAML), CLI flags, or both?
- **Scope of documents**: Single file per run, or batch processing?
- **Media handling**: Images embedded, linked, or option for both? Diagrams (Mermaid)?
- **Code blocks**: Syntax highlighting required? Which languages?

## Dependencies & Sequencing
1. **Markdown parser** → enables TOC generation
2. **Theme system** → enables header/footer customization
3. **PDF renderer** → depends on theme and parser being stable
4. **CLI interface** → wraps all above; last to implement

## Explicitly Out of Scope
- Web UI or preview server
- Real-time document watching
- Reverse conversion (PDF → markdown)
- Output formats other than PDF (DOCX, HTML)
- CMS integrations