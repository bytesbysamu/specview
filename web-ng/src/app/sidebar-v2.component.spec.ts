import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SidebarV2Component, StatusMode, AiOp } from './sidebar-v2.component';
import { Project, Spec } from './services/projects.service';

describe('SidebarV2Component', () => {
  let component: SidebarV2Component;
  let fixture: ComponentFixture<SidebarV2Component>;

  const mockProject: Project = {
    id: 'proj-1',
    name: 'Test Project',
    files: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  } as unknown as Project;

  const mockSpec: Spec = {
    filename: 'analysis.md',
    content: '# Analysis',
  } as unknown as Spec;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarV2Component],
    }).compileComponents();

    fixture = TestBed.createComponent(SidebarV2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('component creation', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });
  });

  describe('input bindings', () => {
    it('accepts activeProject input without throwing', () => {
      component.activeProject = mockProject;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts activeFile input without throwing', () => {
      component.activeFile = 'analysis.md';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts expandedProject input without throwing', () => {
      component.expandedProject = 'proj-1';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts mode input without throwing', () => {
      const modes: StatusMode[] = ['idle', 'active', 'success-flash', 'failure'];
      modes.forEach(mode => {
        component.mode = mode;
        expect(() => fixture.detectChanges()).not.toThrow();
      });
    });

    it('accepts specGenLoading input without throwing', () => {
      component.specGenLoading = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts specGenStep input without throwing', () => {
      component.specGenStep = 'analysis';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts activeStepLabel input without throwing', () => {
      component.activeStepLabel = 'Generating analysis…';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts statusFailureMsg input without throwing', () => {
      component.statusFailureMsg = 'Something went wrong';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts shareLoading input without throwing', () => {
      component.shareLoading = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts shareUrl input without throwing', () => {
      component.shareUrl = 'https://example.com/share/abc';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts shareCopied input without throwing', () => {
      component.shareCopied = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts canGenerateSpecs input without throwing', () => {
      component.canGenerateSpecs = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts canGenerateEpicGuide input without throwing', () => {
      component.canGenerateEpicGuide = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts epicGuideLoading input without throwing', () => {
      component.epicGuideLoading = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts currentSpec input without throwing', () => {
      component.currentSpec = mockSpec;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts isBraindump input without throwing', () => {
      component.isBraindump = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts activeOp input without throwing', () => {
      component.activeOp = 'expand';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts aiLoading input without throwing', () => {
      component.aiLoading = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts aiResult input without throwing', () => {
      component.aiResult = 'AI output text';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts canRevert input without throwing', () => {
      component.canRevert = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts canRedo input without throwing', () => {
      component.canRedo = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts fileOpState input without throwing', () => {
      component.fileOpState = { 'analysis.md': 'running' };
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts stylePresets input without throwing', () => {
      component.stylePresets = ['formal', 'casual'];
      expect(() => fixture.detectChanges()).not.toThrow();
    });
  });

  describe('closeExpanded output', () => {
    it('emits when onClose is called', () => {
      let emitted = false;
      component.closeExpanded.subscribe(() => { emitted = true; });
      component.onClose();
      expect(emitted).toBeTrue();
    });
  });

  describe('fileSelected output', () => {
    it('emits filename when onFileSelect is called', () => {
      const emitted: string[] = [];
      component.fileSelected.subscribe((f: string) => emitted.push(f));
      component.onFileSelect('epic.md');
      expect(emitted).toEqual(['epic.md']);
    });
  });

  describe('retryClicked output', () => {
    it('emits when onRetry is called', () => {
      let emitted = false;
      component.retryClicked.subscribe(() => { emitted = true; });
      component.onRetry();
      expect(emitted).toBeTrue();
    });
  });

  describe('shareClicked output', () => {
    it('emits when onShare is called', () => {
      let emitted = false;
      component.shareClicked.subscribe(() => { emitted = true; });
      component.onShare();
      expect(emitted).toBeTrue();
    });
  });

  describe('generateSpecsClicked output', () => {
    it('emits when onGenerateSpecs is called', () => {
      let emitted = false;
      component.generateSpecsClicked.subscribe(() => { emitted = true; });
      component.onGenerateSpecs();
      expect(emitted).toBeTrue();
    });
  });

  describe('generateGuideClicked output', () => {
    it('emits when onGenerateGuide is called', () => {
      let emitted = false;
      component.generateGuideClicked.subscribe(() => { emitted = true; });
      component.onGenerateGuide();
      expect(emitted).toBeTrue();
    });
  });

  describe('opToggled output', () => {
    it('emits the op when onToggleOp is called', () => {
      const emitted: AiOp[] = [];
      component.opToggled.subscribe((op: AiOp) => emitted.push(op));
      component.onToggleOp('brainstorm');
      expect(emitted).toEqual(['brainstorm']);
    });

    it('emits different ops correctly', () => {
      const emitted: AiOp[] = [];
      component.opToggled.subscribe((op: AiOp) => emitted.push(op));

      const ops: AiOp[] = ['expand', 'compress', 'clarify', 'simplify', 'tldr', 'bullets'];
      ops.forEach(op => component.onToggleOp(op));

      expect(emitted).toEqual(ops);
    });
  });

  describe('styleRun output', () => {
    it('emits the style name when onRunStyle is called', () => {
      const emitted: string[] = [];
      component.styleRun.subscribe((s: string) => emitted.push(s));
      component.onRunStyle('formal');
      expect(emitted).toEqual(['formal']);
    });
  });

  describe('undoClicked output', () => {
    it('emits when onUndo is called', () => {
      let emitted = false;
      component.undoClicked.subscribe(() => { emitted = true; });
      component.onUndo();
      expect(emitted).toBeTrue();
    });
  });

  describe('redoClicked output', () => {
    it('emits when onRedo is called', () => {
      let emitted = false;
      component.redoClicked.subscribe(() => { emitted = true; });
      component.onRedo();
      expect(emitted).toBeTrue();
    });
  });
});
