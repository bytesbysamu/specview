import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SectionNavComponent, NavSection } from './section-nav.component';

describe('SectionNavComponent', () => {
  let component: SectionNavComponent;
  let fixture: ComponentFixture<SectionNavComponent>;

  const mockSections: NavSection[] = [
    { id: 'all', label: 'All', icon: 'grid' },
    { id: 'specs', label: 'Specs', icon: 'file-text' },
    { id: 'braindumps', label: 'Braindumps', icon: 'brain' },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SectionNavComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SectionNavComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('component creation', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });
  });

  describe('input bindings', () => {
    it('accepts sections input without throwing', () => {
      component.sections = mockSections;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts activeSection input without throwing', () => {
      component.activeSection = 'specs';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts sectionCounts input without throwing', () => {
      component.sectionCounts = { all: 10, specs: 7, braindumps: 3 };
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts pulsingSections input without throwing', () => {
      component.pulsingSections = new Set(['braindumps']);
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts contextFileCount input without throwing', () => {
      component.contextFileCount = 5;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts empty sections array without throwing', () => {
      component.sections = [];
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts empty pulsingSections set without throwing', () => {
      component.pulsingSections = new Set();
      expect(() => fixture.detectChanges()).not.toThrow();
    });
  });

  describe('sectionSelected output', () => {
    it('emits section id when selectSection is called', () => {
      const emitted: string[] = [];
      component.sectionSelected.subscribe((id: string) => emitted.push(id));

      component.selectSection('specs');

      expect(emitted).toEqual(['specs']);
    });

    it('emits the correct id for each section', () => {
      const emitted: string[] = [];
      component.sectionSelected.subscribe((id: string) => emitted.push(id));

      component.selectSection('all');
      component.selectSection('braindumps');

      expect(emitted).toEqual(['all', 'braindumps']);
    });

    it('emits each time selectSection is called', () => {
      let count = 0;
      component.sectionSelected.subscribe(() => { count++; });

      component.selectSection('all');
      component.selectSection('all');
      component.selectSection('all');

      expect(count).toBe(3);
    });
  });
});
