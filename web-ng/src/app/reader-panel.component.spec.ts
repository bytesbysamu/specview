import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReaderPanelComponent } from './reader-panel.component';
import { Project, Spec } from './services/projects.service';

describe('ReaderPanelComponent', () => {
  let component: ReaderPanelComponent;
  let fixture: ComponentFixture<ReaderPanelComponent>;

  const mockProject: Project = {
    id: 'proj-1',
    name: 'Test Project',
    files: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  } as unknown as Project;

  const mockSpec: Spec = {
    filename: 'analysis.md',
    content: '# Analysis\nSome content',
  } as unknown as Spec;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReaderPanelComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ReaderPanelComponent);
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

    it('accepts currentSpec input without throwing', () => {
      component.currentSpec = mockSpec;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts accessDenied input without throwing', () => {
      component.accessDenied = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts expandedTitle input without throwing', () => {
      component.expandedTitle = 'My Title';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts expandedProject input without throwing', () => {
      component.expandedProject = 'proj-1';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts activeFileType input without throwing', () => {
      component.activeFileType = 'analysis';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts parsedContent input without throwing', () => {
      component.parsedContent = '<p>Content</p>';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts parsedAiResult input without throwing', () => {
      component.parsedAiResult = '<p>AI Result</p>';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts diffHtmlUnified input without throwing', () => {
      component.diffHtmlUnified = '<div class="diff">...</div>';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts aiResult input without throwing', () => {
      component.aiResult = 'Some AI output';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts aiLoading input without throwing', () => {
      component.aiLoading = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts aiError input without throwing', () => {
      component.aiError = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts aiLatencyMs input without throwing', () => {
      component.aiLatencyMs = 1234;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts activeOp input without throwing', () => {
      component.activeOp = 'expand';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts isAdditiveOp input without throwing', () => {
      component.isAdditiveOp = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts billingError input without throwing', () => {
      component.billingError = 'Billing limit reached';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts copied input without throwing', () => {
      component.copied = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts brainstormQuestion input without throwing', () => {
      component.brainstormQuestion = 'What should I build next?';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts canGenerateSpecs input without throwing', () => {
      component.canGenerateSpecs = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts specGenLoading input without throwing', () => {
      component.specGenLoading = true;
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts specGenProjectName input without throwing', () => {
      component.specGenProjectName = 'my-project';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts specGenStep input without throwing', () => {
      component.specGenStep = 'analysis';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts specGenError input without throwing', () => {
      component.specGenError = 'Generation failed';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts specGenFailedStep input without throwing', () => {
      component.specGenFailedStep = 'architecture';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts cancelling input without throwing', () => {
      component.cancelling = true;
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

  describe('applyResult output', () => {
    it('emits when onApply is called', () => {
      let emitted = false;
      component.applyResult.subscribe(() => { emitted = true; });
      component.onApply();
      expect(emitted).toBeTrue();
    });
  });

  describe('dismissResult output', () => {
    it('emits when onDismiss is called', () => {
      let emitted = false;
      component.dismissResult.subscribe(() => { emitted = true; });
      component.onDismiss();
      expect(emitted).toBeTrue();
    });
  });

  describe('copyResult output', () => {
    it('emits when onCopy is called', () => {
      let emitted = false;
      component.copyResult.subscribe(() => { emitted = true; });
      component.onCopy();
      expect(emitted).toBeTrue();
    });
  });

  describe('followupBrainstorm output', () => {
    it('emits the question when onFollowup is called', () => {
      const emitted: string[] = [];
      component.followupBrainstorm.subscribe((q: string) => emitted.push(q));
      component.onFollowup('How does this scale?');
      expect(emitted).toEqual(['How does this scale?']);
    });
  });

  describe('brainstormQuestionChange output', () => {
    it('emits the new value when onQuestionChange is called', () => {
      const emitted: string[] = [];
      component.brainstormQuestionChange.subscribe((v: string) => emitted.push(v));
      component.onQuestionChange('new question text');
      expect(emitted).toEqual(['new question text']);
    });
  });

  describe('generateFromBrainstormResult output', () => {
    it('emits when onGenerateFromBrainstorm is called', () => {
      let emitted = false;
      component.generateFromBrainstormResult.subscribe(() => { emitted = true; });
      component.onGenerateFromBrainstorm();
      expect(emitted).toBeTrue();
    });
  });

  describe('cancelClicked output', () => {
    it('emits when onCancel is called', () => {
      let emitted = false;
      component.cancelClicked.subscribe(() => { emitted = true; });
      component.onCancel();
      expect(emitted).toBeTrue();
    });
  });

  describe('retryFailedStep output', () => {
    it('emits when onRetryStep is called', () => {
      let emitted = false;
      component.retryFailedStep.subscribe(() => { emitted = true; });
      component.onRetryStep();
      expect(emitted).toBeTrue();
    });
  });
});
