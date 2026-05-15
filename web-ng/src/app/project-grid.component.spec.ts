import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProjectGridComponent, ContextFile, ProjectsBySection } from './project-grid.component';
import { Project } from './services/projects.service';

describe('ProjectGridComponent', () => {
  let component: ProjectGridComponent;
  let fixture: ComponentFixture<ProjectGridComponent>;

  const mockProject: Project = {
    id: 'proj-1',
    name: 'Test Project',
    files: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  } as unknown as Project;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProjectGridComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ProjectGridComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('component creation', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });
  });

  describe('input bindings', () => {
    it('accepts activeSection input without throwing', () => {
      component.activeSection = 'specs';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts filteredProjects input without throwing', () => {
      component.filteredProjects = [mockProject];
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts projectsBySection input without throwing', () => {
      const pbs: ProjectsBySection[] = [
        { section: 'Braindumps', projects: [mockProject] },
      ];
      component.projectsBySection = pbs;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts columns input without throwing', () => {
      component.columns = [[mockProject], []];
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts contextFiles input without throwing', () => {
      const files: ContextFile[] = [{ key: 'ctx-1', label: 'Context', desc: 'A context file' }];
      component.contextFiles = files;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts sectionLabel input without throwing', () => {
      component.sectionLabel = 'My Projects';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts teaserFn input without throwing', () => {
      component.teaserFn = (p: Project) => p.name ?? '';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts sectionFn input without throwing', () => {
      component.sectionFn = () => 'Braindumps';
      expect(() => fixture.detectChanges()).not.toThrow();
    });
  });

  describe('projectSelected output', () => {
    it('emits project id when onSelectProject is called', () => {
      const emitted: string[] = [];
      component.projectSelected.subscribe((id: string) => emitted.push(id));

      component.onSelectProject('proj-42');

      expect(emitted).toEqual(['proj-42']);
    });
  });

  describe('contextOpened output', () => {
    it('emits context key when onOpenContext is called', () => {
      const emitted: string[] = [];
      component.contextOpened.subscribe((key: string) => emitted.push(key));

      component.onOpenContext('ctx-key');

      expect(emitted).toEqual(['ctx-key']);
    });
  });
});
