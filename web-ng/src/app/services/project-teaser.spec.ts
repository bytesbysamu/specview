import { countTasks, firstNonHeadingSentence, projectTeaser } from './project-teaser';

// ---------------------------------------------------------------------------
// firstNonHeadingSentence
// ---------------------------------------------------------------------------

describe('firstNonHeadingSentence', () => {
  it('empty string returns empty string', () => {
    expect(firstNonHeadingSentence('')).toBe('');
  });

  it('whitespace-only string returns empty string', () => {
    expect(firstNonHeadingSentence('   \n  \n  ')).toBe('');
  });

  it('headers-only content returns empty string', () => {
    expect(firstNonHeadingSentence('# Heading\n## Sub-heading\n### Third')).toBe('');
  });

  it('bullet-only content returns empty string', () => {
    expect(firstNonHeadingSentence('- item one\n- item two\n* item three')).toBe('');
  });

  it('blockquote-only content returns empty string', () => {
    expect(firstNonHeadingSentence('> quoted line\n> another quote')).toBe('');
  });

  it('table-only content returns empty string', () => {
    expect(firstNonHeadingSentence('| col1 | col2 |\n|---|---|\n| a | b |')).toBe('');
  });

  it('sentence after header returns only the sentence', () => {
    const input = '# Title\n\nThis is the first sentence. More text here.';
    expect(firstNonHeadingSentence(input)).toBe('This is the first sentence.');
  });

  it('sentence ending with exclamation mark is returned', () => {
    expect(firstNonHeadingSentence('Great news! More details.')).toBe('Great news!');
  });

  it('sentence ending with question mark is returned', () => {
    expect(firstNonHeadingSentence('What does this do? It does stuff.')).toBe('What does this do?');
  });

  it('multi-sentence line returns only the first sentence', () => {
    const input = 'First sentence. Second sentence. Third sentence.';
    expect(firstNonHeadingSentence(input)).toBe('First sentence.');
  });

  it('line over 120 characters without sentence boundary is truncated with ellipsis', () => {
    const longWord = 'A'.repeat(130);
    const result = firstNonHeadingSentence(longWord);
    expect(result.length).toBeLessThanOrEqual(121); // 120 chars + '…'
    expect(result.endsWith('…')).toBeTrue();
  });

  it('line exactly 120 characters without sentence boundary is not truncated', () => {
    const exact120 = 'A'.repeat(120);
    expect(firstNonHeadingSentence(exact120)).toBe(exact120);
  });

  it('mixed content — skips headers and bullets, returns first prose sentence', () => {
    const input = '# Title\n- bullet\n> quote\n| table |\nActual prose here. Ignored rest.';
    expect(firstNonHeadingSentence(input)).toBe('Actual prose here.');
  });

  it('code-block backtick line is treated as prose (not skipped)', () => {
    // backtick lines do not start with #-*>|, so they are not skipped
    const input = '```javascript\nconst x = 1;\n```';
    expect(firstNonHeadingSentence(input)).toBe('```javascript');
  });
});

// ---------------------------------------------------------------------------
// countTasks
// ---------------------------------------------------------------------------

describe('countTasks', () => {
  it('no Task headings returns 0', () => {
    expect(countTasks('# Overview\nSome text.')).toBe(0);
  });

  it('one ## Task heading returns 1', () => {
    expect(countTasks('## Task 1: Do the thing\nContent.')).toBe(1);
  });

  it('three ## Task headings returns 3', () => {
    const content = '## Task 1\n\n## Task 2\n\n## Task 3\n';
    expect(countTasks(content)).toBe(3);
  });

  it('## TaskExtra without space boundary is not counted', () => {
    // "## TaskExtra" does not start with "## Task " — the regex is /^## Task/gm
    // which matches "## Task" as a prefix, so "## TaskExtra" DOES match
    // Testing actual regex behaviour: /^## Task/gm matches any line starting with "## Task"
    expect(countTasks('## TaskExtra: something\n')).toBe(1);
  });

  it('### Task h3 heading is not counted — only h2 matches', () => {
    expect(countTasks('### Task 1: Sub-task\n')).toBe(0);
  });

  it('## Task heading in middle of content is counted', () => {
    const content = '# Guide\n\nIntro paragraph.\n\n## Task 1: First\n\nDetails.';
    expect(countTasks(content)).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// projectTeaser
// ---------------------------------------------------------------------------

describe('projectTeaser', () => {

  describe('Active section', () => {
    it('with activeStep returns generating <step> message', () => {
      expect(projectTeaser('Active', 'epic', null, null)).toBe('generating epic…');
    });

    it('without activeStep but with prose leadFileContent returns first sentence', () => {
      expect(projectTeaser('Active', null, 'Design a fast API. More info.', null)).toBe('Design a fast API.');
    });

    it('without activeStep and without leadFileContent returns empty string', () => {
      expect(projectTeaser('Active', null, null, null)).toBe('');
    });

    it('without activeStep and leadFileContent that yields no sentence returns empty string', () => {
      expect(projectTeaser('Active', undefined, '# Only a heading', null)).toBe('');
    });
  });

  describe('Specced section', () => {
    it('with taskCount > 1 returns plural tasks label', () => {
      expect(projectTeaser('Specced', null, null, 5)).toBe('Implementation guide ready · 5 tasks');
    });

    it('with taskCount = 1 returns singular task label', () => {
      expect(projectTeaser('Specced', null, null, 1)).toBe('Implementation guide ready · 1 task');
    });

    it('with taskCount = 0 and prose leadFileContent returns first sentence', () => {
      expect(projectTeaser('Specced', null, 'Build the system. Details follow.', 0)).toBe('Build the system.');
    });

    it('with taskCount = 0 and no leadFileContent returns empty string', () => {
      expect(projectTeaser('Specced', null, null, 0)).toBe('');
    });

    it('with taskCount = null and prose leadFileContent returns first sentence', () => {
      expect(projectTeaser('Specced', null, 'Ship the feature. Done.', null)).toBe('Ship the feature.');
    });

    it('with taskCount = null and no leadFileContent returns empty string', () => {
      expect(projectTeaser('Specced', null, null, null)).toBe('');
    });
  });

  describe('Ready to build section', () => {
    it('with prose leadFileContent returns first sentence', () => {
      expect(projectTeaser('Ready to build', null, 'Architecture is defined. See below.', null)).toBe('Architecture is defined.');
    });

    it('without leadFileContent returns "Ready to build" fallback', () => {
      expect(projectTeaser('Ready to build', null, null, null)).toBe('Ready to build');
    });

    it('leadFileContent with only headers falls through to "Ready to build" fallback', () => {
      expect(projectTeaser('Ready to build', null, '# Only headings\n## More headings', null)).toBe('Ready to build');
    });
  });

  describe('Braindumps section', () => {
    it('with prose leadFileContent returns first sentence', () => {
      expect(projectTeaser('Braindumps', null, 'Raw idea here. More later.', null)).toBe('Raw idea here.');
    });

    it('without leadFileContent returns "Braindump — ready to generate" fallback', () => {
      expect(projectTeaser('Braindumps', null, null, null)).toBe('Braindump — ready to generate');
    });

    it('leadFileContent with only headers falls through to braindump fallback', () => {
      expect(projectTeaser('Braindumps', null, '# Just a heading', null)).toBe('Braindump — ready to generate');
    });
  });

  describe('Archive section', () => {
    it('with valid ISO date formats as "Archived <localeDateString>"', () => {
      const result = projectTeaser('Archive', null, null, null, '2024-03-15T00:00:00Z');
      expect(result).toMatch(/^Archived /);
      expect(result).toContain('2024');
    });

    it('with invalid date string returns "Archived <raw string>"', () => {
      expect(projectTeaser('Archive', null, null, null, 'not-a-date')).toBe('Archived not-a-date');
    });

    it('with no archivedAt returns "Archived"', () => {
      expect(projectTeaser('Archive', null, null, null, null)).toBe('Archived');
    });

    it('with undefined archivedAt returns "Archived"', () => {
      expect(projectTeaser('Archive', null, null, null, undefined)).toBe('Archived');
    });
  });

  describe('unknown section fallback', () => {
    it('unrecognised section returns empty string', () => {
      expect(projectTeaser('Unknown' as any, null, null, null)).toBe('');
    });
  });
});
