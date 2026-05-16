import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PgBordersComponent } from './pg-borders.component';

describe('PgBordersComponent', () => {
  let component: PgBordersComponent;
  let fixture: ComponentFixture<PgBordersComponent>;
  let el: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PgBordersComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(PgBordersComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('creates the component', () => {
    expect(component).toBeTruthy();
  });

  it('renders seven border demo cards', () => {
    const cards = el.querySelectorAll('.border-card');
    expect(cards.length).toBe(7);
  });

  it('renders the divider card with correct CSS class and label text', () => {
    const demoEl = el.querySelector('.demo-border--divider');
    expect(demoEl).toBeTruthy();
    const card = demoEl!.closest('.border-card');
    const label = card!.querySelector('.border-label');
    expect(label!.textContent).toContain('1px solid var(--border)');
  });

  it('renders the structural border card with correct CSS class and description', () => {
    const demoEl = el.querySelector('.demo-border--structural');
    expect(demoEl).toBeTruthy();
    const card = demoEl!.closest('.border-card');
    const description = card!.querySelector('.border-description');
    expect(description!.textContent).toContain('Major structural break');
  });

  it('renders the code-accent border card with correct CSS class', () => {
    const demoEl = el.querySelector('.demo-border--code-accent');
    expect(demoEl).toBeTruthy();
    const card = demoEl!.closest('.border-card');
    const description = card!.querySelector('.border-description');
    expect(description!.textContent).toContain('Code block accent');
  });
});
