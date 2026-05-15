import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StatusBarComponent, StatusMode } from './status-bar.component';

describe('StatusBarComponent', () => {
  let component: StatusBarComponent;
  let fixture: ComponentFixture<StatusBarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StatusBarComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(StatusBarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('component creation', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });
  });

  describe('input bindings', () => {
    it('accepts mode input without throwing', () => {
      const modes: StatusMode[] = ['idle', 'active', 'success-flash', 'failure'];
      modes.forEach(mode => {
        component.mode = mode;
        expect(() => fixture.detectChanges()).not.toThrow();
      });
    });

    it('accepts specGenProjectName input without throwing', () => {
      component.specGenProjectName = 'my-project';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts specGenStep input without throwing', () => {
      component.specGenStep = 'architecture';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts specGenElapsed input without throwing', () => {
      component.specGenElapsed = '12.5s';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts specGenJobId input without throwing', () => {
      component.specGenJobId = 'job-abc-123';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts statusFailureMsg input without throwing', () => {
      component.statusFailureMsg = 'Step failed: architecture';
      expect(() => fixture.detectChanges()).not.toThrow();
    });

    it('accepts cancelling input without throwing', () => {
      component.cancelling = true;
      expect(() => fixture.detectChanges()).not.toThrow();
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

  describe('retryClicked output', () => {
    it('emits when onRetry is called', () => {
      let emitted = false;
      component.retryClicked.subscribe(() => { emitted = true; });
      component.onRetry();
      expect(emitted).toBeTrue();
    });
  });
});
