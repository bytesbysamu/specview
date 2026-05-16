import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PgComponentsAppComponent } from './pg-components-app.component';

describe('PgComponentsAppComponent', () => {
  let component: PgComponentsAppComponent;
  let fixture: ComponentFixture<PgComponentsAppComponent>;
  let el: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PgComponentsAppComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(PgComponentsAppComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('creates the component', () => {
    expect(component).toBeTruthy();
  });

  it('renders the masthead section with the masthead CSS class', () => {
    const masthead = el.querySelector('.masthead');
    expect(masthead).toBeTruthy();
  });

  it('renders the masthead title text "Design Playground"', () => {
    const title = el.querySelector('.masthead-title');
    expect(title).toBeTruthy();
    expect(title!.textContent).toContain('Design Playground');
  });

  it('renders the modal dialog structure with modal-header and modal-body', () => {
    const modalHeader = el.querySelector('.modal-header');
    const modalBody = el.querySelector('.modal-body');
    expect(modalHeader).toBeTruthy();
    expect(modalBody).toBeTruthy();
  });

  it('renders the search bar input element', () => {
    const searchBar = el.querySelector('.search-bar');
    expect(searchBar).toBeTruthy();
    const input = searchBar!.querySelector('input[type="search"]');
    expect(input).toBeTruthy();
  });

  it('renders three context card containers', () => {
    const cards = el.querySelectorAll('.context-card');
    expect(cards.length).toBe(3);
  });

  it('renders context card labels from the component data', () => {
    const labels = el.querySelectorAll('.context-card__label');
    const texts = Array.from(labels).map(l => l.textContent?.trim());
    expect(texts).toContain('Product Brief');
    expect(texts).toContain('Architecture Decision');
    expect(texts).toContain('Design Principles');
  });

  it('renders the update banner with its expected text', () => {
    const banner = el.querySelector('.update-banner');
    expect(banner).toBeTruthy();
    expect(banner!.textContent).toContain('A new version of Specview is available.');
  });
});
