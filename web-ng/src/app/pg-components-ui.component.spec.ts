import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PgComponentsUiComponent } from './pg-components-ui.component';

describe('PgComponentsUiComponent', () => {
  let component: PgComponentsUiComponent;
  let fixture: ComponentFixture<PgComponentsUiComponent>;
  let el: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PgComponentsUiComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(PgComponentsUiComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('creates the component', () => {
    expect(component).toBeTruthy();
  });

  it('renders four op chip buttons', () => {
    const chips = el.querySelectorAll('.op-chip');
    expect(chips.length).toBe(4);
  });

  it('renders the active op chip with the "active" CSS class', () => {
    const activeChips = el.querySelectorAll('.op-chip.active');
    expect(activeChips.length).toBeGreaterThanOrEqual(1);
    expect(activeChips[0].textContent?.trim()).toBe('Expand');
  });

  it('renders the accent op chip with the "op-chip--accent" CSS class', () => {
    const accentChip = el.querySelector('.op-chip--accent');
    expect(accentChip).toBeTruthy();
    expect(accentChip!.textContent?.trim()).toBe('Brainstorm');
  });

  it('renders style chip buttons with their labels', () => {
    const styleChips = el.querySelectorAll('.style-chip');
    const texts = Array.from(styleChips).map(c => c.textContent?.trim());
    expect(texts).toContain('Technical');
    expect(texts).toContain('Concise');
    expect(texts).toContain('Formal');
    expect(texts).toContain('Plain');
  });

  it('renders the new-project-btn button variant', () => {
    const btn = el.querySelector('.new-project-btn');
    expect(btn).toBeTruthy();
  });

  it('renders disabled button states for each variant', () => {
    const disabledBtns = el.querySelectorAll('button[disabled]');
    expect(disabledBtns.length).toBeGreaterThanOrEqual(1);
  });

  it('renders overline elements with their label text', () => {
    const overlines = el.querySelectorAll('.overline');
    expect(overlines.length).toBeGreaterThanOrEqual(3);
    const texts = Array.from(overlines).map(o => o.textContent?.trim());
    expect(texts).toContain('Section Label');
  });

  it('renders badge variants with correct CSS classes', () => {
    const badgeNew = el.querySelector('.badge.badge--new');
    const badgeComplete = el.querySelector('.badge.badge--complete');
    expect(badgeNew).toBeTruthy();
    expect(badgeComplete).toBeTruthy();
  });

  it('renders col-badge elements', () => {
    const colBadges = el.querySelectorAll('.col-badge');
    expect(colBadges.length).toBeGreaterThanOrEqual(2);
  });
});
