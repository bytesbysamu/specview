/**
 * Pure teaser resolver — no class, no DI.
 *
 * Replaces the old `teaser(content.slice(0, 100))` approach with
 * section-aware, state-aware copy.
 */

import { Section } from './section-taxonomy.service';

/**
 * Extract the first non-heading sentence from markdown text.
 *
 * Skips lines that start with: #  -  *  >  |
 * Returns the first sentence (up to .!? followed by whitespace or EOL)
 * of the first remaining line, or the full first remaining line if no
 * sentence boundary is found.
 */
export function firstNonHeadingSentence(content: string): string {
  const lines = content.split('\n');
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (/^[#\-*>|]/.test(line)) continue;

    // Match first sentence ending with .!? followed by whitespace or EOL
    const match = line.match(/^(.+?[.!?])(?:\s|$)/);
    if (match) return match[1].trim();

    // No sentence boundary — return the whole line (truncated to 120 chars)
    return line.length > 120 ? line.slice(0, 120).trimEnd() + '…' : line;
  }
  return '';
}

/**
 * Count `## Task` headings in an implementation guide.
 */
export function countTasks(content: string): number {
  return (content.match(/^## Task/gm) ?? []).length;
}

/**
 * Produce a one-line teaser string for a project card.
 *
 * Priority:
 *  1. Active + step known → "generating <step>…"
 *  2. Specced + taskCount → "Implementation guide ready · N task(s)"
 *  3. Specced + leadFileContent → first non-heading sentence
 *  4. Braindumps → "Braindump — ready to generate"
 *  5. Ready to build + leadFileContent → first non-heading sentence
 *  6. Archive + archivedAt → "Archived <date>"
 *  7. Fallback → empty string
 */
export function projectTeaser(
  section: Section,
  activeStep: string | null | undefined,
  leadFileContent: string | null | undefined,
  taskCount: number | null | undefined,
  archivedAt?: string | null,
): string {
  if (section === 'Active' && activeStep) {
    return `generating ${activeStep}…`;
  }

  if (section === 'Specced') {
    if (taskCount != null && taskCount > 0) {
      return `Implementation guide ready · ${taskCount} task${taskCount !== 1 ? 's' : ''}`;
    }
    if (leadFileContent) {
      const sentence = firstNonHeadingSentence(leadFileContent);
      if (sentence) return sentence;
    }
  }

  if (section === 'Ready to build') {
    if (leadFileContent) {
      const sentence = firstNonHeadingSentence(leadFileContent);
      if (sentence) return sentence;
    }
    return 'Ready to build';
  }

  if (section === 'Braindumps') {
    return 'Braindump — ready to generate';
  }

  if (section === 'Archive') {
    if (archivedAt) {
      const d = new Date(archivedAt);
      const label = isNaN(d.getTime())
        ? archivedAt
        : d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
      return `Archived ${label}`;
    }
    return 'Archived';
  }

  return '';
}
