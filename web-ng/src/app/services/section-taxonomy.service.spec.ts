import { Project } from './projects.service';
import { SECTION_ORDER, Section, sectionFor } from './section-taxonomy.service';

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

function makeProject(filenames: string[] = [], extra: Partial<Project> = {}): Project {
  return {
    id: 'proj-1',
    name: 'Test Project',
    createdAt: '2024-01-01T00:00:00Z',
    specs: filenames.map(f => ({ filename: f, label: f })),
    ...extra,
  };
}

// ---------------------------------------------------------------------------
// SECTION_ORDER — structural contract
// ---------------------------------------------------------------------------

describe('SECTION_ORDER', () => {
  it('contains exactly five sections', () => {
    expect(SECTION_ORDER.length).toBe(5);
  });

  it('lists sections in Active, Ready to build, Specced, Braindumps, Archive order', () => {
    expect(SECTION_ORDER).toEqual([
      'Active',
      'Ready to build',
      'Specced',
      'Braindumps',
      'Archive',
    ] as Section[]);
  });
});

// ---------------------------------------------------------------------------
// sectionFor — parameterised truth table
// ---------------------------------------------------------------------------

describe('sectionFor', () => {

  describe('active-state precedence — hasActiveJob overrides file state', () => {
    const cases: Array<{ desc: string; filenames: string[]; expected: Section }> = [
      {
        desc: 'no files + hasActiveJob → Active',
        filenames: [],
        expected: 'Active',
      },
      {
        desc: 'implementation-guide.md present + hasActiveJob → Active (not Specced)',
        filenames: ['implementation-guide.md'],
        expected: 'Active',
      },
      {
        desc: 'architecture.md present + hasActiveJob → Active (not Ready to build)',
        filenames: ['architecture.md'],
        expected: 'Active',
      },
      {
        desc: 'epic.md present + hasActiveJob → Active (not Ready to build)',
        filenames: ['epic.md'],
        expected: 'Active',
      },
    ];

    cases.forEach(({ desc, filenames, expected }) => {
      it(desc, () => {
        expect(sectionFor(makeProject(filenames), true)).toBe(expected);
      });
    });
  });

  describe('file-based classification — hasActiveJob is false', () => {
    const cases: Array<{ desc: string; filenames: string[]; expected: Section }> = [
      {
        desc: 'implementation-guide.md → Specced',
        filenames: ['implementation-guide.md'],
        expected: 'Specced',
      },
      {
        desc: 'implementation-guide.md with other files → Specced',
        filenames: ['braindump.md', 'epic.md', 'architecture.md', 'implementation-guide.md'],
        expected: 'Specced',
      },
      {
        desc: 'architecture.md only → Ready to build',
        filenames: ['architecture.md'],
        expected: 'Ready to build',
      },
      {
        desc: 'epic.md only → Ready to build',
        filenames: ['epic.md'],
        expected: 'Ready to build',
      },
      {
        desc: 'both architecture.md and epic.md → Ready to build',
        filenames: ['architecture.md', 'epic.md'],
        expected: 'Ready to build',
      },
      {
        desc: 'braindump.md only → Braindumps',
        filenames: ['braindump.md'],
        expected: 'Braindumps',
      },
      {
        desc: 'no files at all → Braindumps',
        filenames: [],
        expected: 'Braindumps',
      },
      {
        desc: 'unknown file only → Braindumps',
        filenames: ['notes.md'],
        expected: 'Braindumps',
      },
    ];

    cases.forEach(({ desc, filenames, expected }) => {
      it(desc, () => {
        expect(sectionFor(makeProject(filenames), false)).toBe(expected);
      });
    });
  });

  describe('archive override — archived flag wins over all file states', () => {
    const cases: Array<{ desc: string; filenames: string[] }> = [
      { desc: 'no files + archived → Archive', filenames: [] },
      { desc: 'implementation-guide.md + archived → Archive (not Specced)', filenames: ['implementation-guide.md'] },
      { desc: 'architecture.md + archived → Archive (not Ready to build)', filenames: ['architecture.md'] },
    ];

    cases.forEach(({ desc, filenames }) => {
      it(desc, () => {
        const project = makeProject(filenames);
        (project as any).archived = true;
        expect(sectionFor(project, false)).toBe('Archive');
      });
    });

    it('archived flag wins even when hasActiveJob is true', () => {
      const project = makeProject([]);
      (project as any).archived = true;
      expect(sectionFor(project, true)).toBe('Archive');
    });
  });
});
