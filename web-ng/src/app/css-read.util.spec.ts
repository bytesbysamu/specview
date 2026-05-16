import { getCssVar } from './css-read.util';

describe('getCssVar', () => {
  let originalGetComputedStyle: typeof window.getComputedStyle;

  beforeEach(() => {
    originalGetComputedStyle = window.getComputedStyle;
  });

  afterEach(() => {
    window.getComputedStyle = originalGetComputedStyle;
  });

  it('returns the trimmed value from getComputedStyle', () => {
    window.getComputedStyle = jasmine.createSpy('getComputedStyle').and.returnValue({
      getPropertyValue: () => '  #ff0000  ',
    } as unknown as CSSStyleDeclaration);

    const result = getCssVar('--accent');

    expect(result).toBe('#ff0000');
  });

  it('returns "not set" sentinel when getComputedStyle returns empty string', () => {
    window.getComputedStyle = jasmine.createSpy('getComputedStyle').and.returnValue({
      getPropertyValue: () => '',
    } as unknown as CSSStyleDeclaration);

    const result = getCssVar('--missing-var');

    expect(result).toBe('not set');
  });

  it('returns "not set" sentinel when getComputedStyle returns whitespace-only string', () => {
    window.getComputedStyle = jasmine.createSpy('getComputedStyle').and.returnValue({
      getPropertyValue: () => '   ',
    } as unknown as CSSStyleDeclaration);

    const result = getCssVar('--whitespace-var');

    expect(result).toBe('not set');
  });

  it('handles a missing property gracefully by returning "not set"', () => {
    window.getComputedStyle = jasmine.createSpy('getComputedStyle').and.returnValue({
      getPropertyValue: () => '',
    } as unknown as CSSStyleDeclaration);

    const result = getCssVar('--undefined-property');

    expect(result).toBe('not set');
  });

  it('works against a real DOM element fixture created via document.createElement', () => {
    const el = document.createElement('div');
    document.body.appendChild(el);

    // Real getComputedStyle — no custom property set, so value is empty → 'not set'
    const result = getCssVar('--totally-unset-var');

    expect(result).toBe('not set');

    document.body.removeChild(el);
  });
});
