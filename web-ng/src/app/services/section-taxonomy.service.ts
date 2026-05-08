/**
 * Pure section taxonomy functions — no class, no DI.
 *
 * A project's section is derived entirely from its file list and job state.
 * The old categorise() function used ID-prefix matching; this replaces it
 * with file-state logic so newly created projects land in the right bucket
 * automatically regardless of how they're named.
 */

import { Project } from './projects.service';

export type Section = 'Active' | 'Ready to build' | 'Specced' | 'Braindumps' | 'Archive';

/** Canonical display order for the five sections. */
export const SECTION_ORDER: Section[] = [
  'Active',
  'Ready to build',
  'Specced',
  'Braindumps',
  'Archive',
];

/**
 * Determine which section a project belongs to.
 *
 * @param project   The project from the API (specs[] is the file list)
 * @param hasActiveJob  True when a spec-gen or epic-guide job is currently
 *                      running for this specific project
 */
export function sectionFor(project: Project, hasActiveJob: boolean): Section {
  const filenames = project.specs.map(s => s.filename);

  // archived flag — not on the current API shape but guarded for future use
  if ((project as any).archived) return 'Archive';

  if (hasActiveJob) return 'Active';

  if (filenames.includes('implementation-guide.md')) return 'Specced';

  if (filenames.includes('architecture.md') || filenames.includes('epic.md')) {
    return 'Ready to build';
  }

  // braindump.md present (or no files at all) → Braindumps
  return 'Braindumps';
}
