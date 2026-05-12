import { WordCountPipe } from './word-count.pipe';

// Pure pipe — no Angular DI needed; instantiate directly.

describe('WordCountPipe', () => {
  let pipe: WordCountPipe;

  beforeEach(() => {
    pipe = new WordCountPipe();
  });

  // -------------------------------------------------------------------------
  // Falsy guard
  // -------------------------------------------------------------------------

  it('returns 0 for null', () => {
    expect(pipe.transform(null)).toBe(0);
  });

  it('returns 0 for undefined', () => {
    expect(pipe.transform(undefined)).toBe(0);
  });

  it('returns 0 for empty string', () => {
    expect(pipe.transform('')).toBe(0);
  });

  it('returns 0 for whitespace-only string', () => {
    expect(pipe.transform('   \t\n  ')).toBe(0);
  });

  // -------------------------------------------------------------------------
  // Word counting
  // -------------------------------------------------------------------------

  it('counts a single word', () => {
    expect(pipe.transform('hello')).toBe(1);
  });

  it('counts two space-separated words', () => {
    expect(pipe.transform('hello world')).toBe(2);
  });

  it('counts words separated by multiple spaces', () => {
    expect(pipe.transform('one   two    three')).toBe(3);
  });

  it('counts words separated by tabs', () => {
    expect(pipe.transform('word1\tword2\tword3')).toBe(3);
  });

  it('counts words separated by newlines', () => {
    expect(pipe.transform('line one\nline two\nline three')).toBe(6);
  });

  it('counts words in a typical markdown sentence', () => {
    // "This is a short sentence." = 5 words
    expect(pipe.transform('This is a short sentence.')).toBe(5);
  });

  it('ignores leading and trailing whitespace', () => {
    expect(pipe.transform('  hello world  ')).toBe(2);
  });
});
