import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PgTokensComponent } from './pg-tokens.component';

describe('PgTokensComponent', () => {
  let component: PgTokensComponent;
  let fixture: ComponentFixture<PgTokensComponent>;
  let el: HTMLElement;

  // Captured MutationObserver callback so tests can invoke it manually.
  let capturedCallback: MutationCallback;
  let mockObserveSpy: jasmine.Spy;
  let mockDisconnectSpy: jasmine.Spy;

  let OriginalMutationObserver: typeof MutationObserver;
  let originalGetComputedStyle: typeof window.getComputedStyle;

  beforeEach(async () => {
    OriginalMutationObserver = window.MutationObserver;
    originalGetComputedStyle = window.getComputedStyle;

    mockObserveSpy = jasmine.createSpy('observe');
    mockDisconnectSpy = jasmine.createSpy('disconnect');

    // Replace MutationObserver with a class-style mock that TypeScript accepts.
    class MockMutationObserver implements MutationObserver {
      constructor(cb: MutationCallback) {
        capturedCallback = cb;
      }
      observe = mockObserveSpy;
      disconnect = mockDisconnectSpy;
      takeRecords(): MutationRecord[] { return []; }
    }

    // Assign the mock to the global; use Object.defineProperty for strict environments.
    Object.defineProperty(window, 'MutationObserver', {
      value: MockMutationObserver,
      writable: true,
      configurable: true,
    });

    // Spy on getComputedStyle to return controlled token values.
    window.getComputedStyle = jasmine.createSpy('getComputedStyle').and.returnValue({
      getPropertyValue: (name: string) => {
        if (name === '--bg') return ' #ffffff ';
        if (name === '--accent') return ' #0066cc ';
        return '';
      },
    } as unknown as CSSStyleDeclaration);

    await TestBed.configureTestingModule({
      imports: [PgTokensComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(PgTokensComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  afterEach(() => {
    Object.defineProperty(window, 'MutationObserver', {
      value: OriginalMutationObserver,
      writable: true,
      configurable: true,
    });
    window.getComputedStyle = originalGetComputedStyle;
    fixture.destroy();
  });

  it('creates the component', () => {
    expect(component).toBeTruthy();
  });

  it('sets up MutationObserver targeting document.documentElement on init', () => {
    expect(mockObserveSpy).toHaveBeenCalledOnceWith(
      document.documentElement,
      jasmine.objectContaining({ attributes: true })
    );
  });

  it('observes with attributeFilter containing data-theme', () => {
    const callArgs = mockObserveSpy.calls.first().args as [Node, MutationObserverInit];
    expect(callArgs[1]['attributeFilter']).toContain('data-theme');
  });

  it('renders color token values from mocked getComputedStyle', () => {
    const colorValues = el.querySelectorAll('.color-value');
    // At least one token should show a value from our mock (trimmed or 'not set')
    const texts = Array.from(colorValues).map(v => v.textContent ?? '');
    const hasMockedValue = texts.some(t => t === '#ffffff' || t === '#0066cc' || t === 'not set');
    expect(hasMockedValue).toBeTrue();
  });

  it('re-reads token values when the MutationObserver callback is manually invoked', () => {
    const getComputedStyleSpy = window.getComputedStyle as jasmine.Spy;
    const callCountBefore = getComputedStyleSpy.calls.count();

    // Manually invoke the captured MutationObserver callback to simulate dark-mode toggle.
    capturedCallback([], {} as MutationObserver);
    fixture.detectChanges();

    // getComputedStyle should have been called again after the tick update.
    expect(getComputedStyleSpy.calls.count()).toBeGreaterThan(callCountBefore);
  });

  it('renders the Colors section heading', () => {
    const headings = el.querySelectorAll('.tokens-heading');
    const texts = Array.from(headings).map(h => h.textContent?.trim());
    expect(texts).toContain('Colors');
  });

  it('renders the Typography section heading', () => {
    const headings = el.querySelectorAll('.tokens-heading');
    const texts = Array.from(headings).map(h => h.textContent?.trim());
    expect(texts).toContain('Typography');
  });

  it('renders the Spacing section heading', () => {
    const headings = el.querySelectorAll('.tokens-heading');
    const texts = Array.from(headings).map(h => h.textContent?.trim());
    expect(texts).toContain('Spacing');
  });

  it('disconnects the MutationObserver when the component is destroyed', () => {
    fixture.destroy();
    expect(mockDisconnectSpy).toHaveBeenCalled();
  });
});
