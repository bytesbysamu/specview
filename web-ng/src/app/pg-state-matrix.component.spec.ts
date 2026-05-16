import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import DOMPurify from 'dompurify';
import { PgStateMatrixComponent } from './pg-state-matrix.component';
import { DEMO_NAV_SECTIONS, DEMO_SECTION_COUNTS } from './playground-demo-data';

describe('PgStateMatrixComponent', () => {
  let component: PgStateMatrixComponent;
  let fixture: ComponentFixture<PgStateMatrixComponent>;
  let el: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PgStateMatrixComponent],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(PgStateMatrixComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  afterEach(() => {
    fixture.destroy();
  });

  // ── Creation ────────────────────────────────────────────────────────────────

  it('creates the component', () => {
    expect(component).toBeTruthy();
  });

  // ── Project Card Variants (5) ────────────────────────────────────────────────

  it('renders five project card matrix cells', () => {
    const cells = el.querySelectorAll('.matrix-cards-row .matrix-cell');
    expect(cells.length).toBe(5);
  });

  it('renders the featured card with the featured CSS class', () => {
    const fileItems = el.querySelectorAll('.matrix-cards-row .file-item');
    const featuredItem = fileItems[0];
    expect(featuredItem.classList).toContain('featured');
  });

  it('renders a normal card without the featured class', () => {
    const fileItems = el.querySelectorAll('.matrix-cards-row .file-item');
    const normalCard = fileItems[1];
    expect(normalCard.classList).not.toContain('featured');
  });

  it('renders the correct title for the featured card', () => {
    const titles = el.querySelectorAll('.matrix-cards-row .file-item-title');
    expect(titles[0].textContent).toContain('Payment Gateway Redesign');
  });

  it('renders the generating teaser text for the Active card', () => {
    const teasers = el.querySelectorAll('.matrix-cards-row .file-item-teaser');
    expect(teasers[2].textContent).toContain('generating');
  });

  it('renders the implementation guide teaser for the Specced card', () => {
    const teasers = el.querySelectorAll('.matrix-cards-row .file-item-teaser');
    expect(teasers[3].textContent).toContain('Implementation guide ready');
  });

  it('renders the braindump teaser for the Braindumps card', () => {
    const teasers = el.querySelectorAll('.matrix-cards-row .file-item-teaser');
    expect(teasers[4].textContent).toContain('Braindump');
  });

  // ── Sidebar File Nav Dot States (5) ─────────────────────────────────────────

  it('renders five sidebar file nav buttons', () => {
    const buttons = el.querySelectorAll('.sidebar-nav .sidebar-file');
    expect(buttons.length).toBe(5);
  });

  it('applies the active class to the active file nav item', () => {
    const buttons = el.querySelectorAll('.sidebar-nav .sidebar-file');
    // Analysis (index 1) is active per component data
    expect(buttons[1].classList).toContain('active');
  });

  it('does not render a file-dot for the idle nav item (Braindump)', () => {
    const buttons = el.querySelectorAll('.sidebar-nav .sidebar-file');
    const dot = buttons[0].querySelector('.file-dot');
    expect(dot).toBeNull();
  });

  it('renders a running dot for the Epic nav item', () => {
    const buttons = el.querySelectorAll('.sidebar-nav .sidebar-file');
    const dot = buttons[2].querySelector('.file-dot');
    expect(dot).toBeTruthy();
    expect(dot!.classList).toContain('file-dot--running');
  });

  it('renders a success dot for the Architecture nav item', () => {
    const buttons = el.querySelectorAll('.sidebar-nav .sidebar-file');
    const dot = buttons[3].querySelector('.file-dot');
    expect(dot).toBeTruthy();
    expect(dot!.classList).toContain('file-dot--success');
  });

  it('renders a failure dot for the Impl. Guide nav item', () => {
    const buttons = el.querySelectorAll('.sidebar-nav .sidebar-file');
    const dot = buttons[4].querySelector('.file-dot');
    expect(dot).toBeTruthy();
    expect(dot!.classList).toContain('file-dot--failure');
  });

  // ── Section Nav Configurations (3) ──────────────────────────────────────────

  it('renders three section nav demo cells', () => {
    const cells = el.querySelectorAll('.matrix-nav-demos .matrix-cell');
    expect(cells.length).toBe(3);
  });

  it('renders cell labels for all three section nav configurations', () => {
    const labels = el.querySelectorAll('.matrix-nav-demos .matrix-cell-label');
    const texts = Array.from(labels).map(l => l.textContent?.trim());
    expect(texts[0]).toContain('"All" active');
    expect(texts[1]).toContain('"Specced" active');
    expect(texts[2]).toContain('Badge pulsing');
  });

  // ── Reader Panel Modes ───────────────────────────────────────────────────────

  it('renders the normal spec content panel with the expanded-title "Analysis"', () => {
    const titles = el.querySelectorAll('.matrix-reader-cell .expanded-title');
    expect(titles[0].textContent).toContain('Analysis');
  });

  it('renders the access-denied panel with "Access Denied" overline text', () => {
    const overline = el.querySelector('.access-denied-state .overline');
    expect(overline).toBeTruthy();
    expect(overline!.textContent).toContain('Access Denied');
  });

  it('renders the access-denied heading message', () => {
    const heading = el.querySelector('.access-denied-heading');
    expect(heading).toBeTruthy();
    expect(heading!.textContent).toContain("don't have access");
  });

  it('renders the AI diff panel with the "AI Result" title', () => {
    const titles = el.querySelectorAll('.matrix-reader-cell .expanded-title');
    expect(titles[1].textContent).toContain('AI Result');
  });

  it('renders diff-block-remove and diff-block-add elements in the diff panel', () => {
    const removeBlocks = el.querySelectorAll('.diff-block-remove');
    const addBlocks = el.querySelectorAll('.diff-block-add');
    expect(removeBlocks.length).toBeGreaterThanOrEqual(1);
    expect(addBlocks.length).toBeGreaterThanOrEqual(1);
  });

  // ── DOMPurify Sanitization — XSS Prevention ──────────────────────────────────

  it('strips a script-tag XSS vector via DOMPurify before rendering', () => {
    const xssInput = '<p>Safe text</p><script>window.__xss_executed = true;</script>';
    const sanitized = DOMPurify.sanitize(xssInput);

    expect(sanitized).not.toContain('<script>');
    expect((window as any).__xss_executed).toBeUndefined();
  });

  it('strips event-handler XSS vectors via DOMPurify', () => {
    const xssInput = '<img src="x" onerror="window.__xss_event=true">';
    const sanitized = DOMPurify.sanitize(xssInput);

    expect(sanitized).not.toContain('onerror');
    expect((window as any).__xss_event).toBeUndefined();
  });

  it('preserves safe HTML content through DOMPurify sanitization', () => {
    const safeInput = '<h2>Analysis</h2><p>The <strong>existing</strong> payment gateway.</p>';
    const sanitized = DOMPurify.sanitize(safeInput);

    expect(sanitized).toContain('<h2>');
    expect(sanitized).toContain('<strong>');
    expect(sanitized).toContain('existing');
  });

  it('renders parsed markdown content in the reader panel without script tags', () => {
    const readerBody = el.querySelector('.matrix-reader-body');
    expect(readerBody).toBeTruthy();
    const inner = readerBody!.innerHTML;
    expect(inner).not.toContain('<script>');
    expect(inner).toContain('Analysis');
  });

  // ── Demo data wiring ─────────────────────────────────────────────────────────

  it('exposes demoSections matching DEMO_NAV_SECTIONS', () => {
    expect(component.demoSections).toBe(DEMO_NAV_SECTIONS);
  });

  it('exposes demoCounts matching DEMO_SECTION_COUNTS', () => {
    expect(component.demoCounts).toBe(DEMO_SECTION_COUNTS);
  });

  it('getPulsingSet returns a non-empty set when pulsing is true', () => {
    const set = component.getPulsingSet(true);
    expect(set.size).toBeGreaterThan(0);
    expect(set.has('Active')).toBeTrue();
  });

  it('getPulsingSet returns an empty set when pulsing is false', () => {
    const set = component.getPulsingSet(false);
    expect(set.size).toBe(0);
  });
});
