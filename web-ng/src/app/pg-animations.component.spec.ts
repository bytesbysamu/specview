import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PgAnimationsComponent } from './pg-animations.component';

describe('PgAnimationsComponent', () => {
  let component: PgAnimationsComponent;
  let fixture: ComponentFixture<PgAnimationsComponent>;
  let el: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PgAnimationsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(PgAnimationsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('creates the component', () => {
    expect(component).toBeTruthy();
  });

  it('renders seven animation demo cards', () => {
    const cards = el.querySelectorAll('.anim-card');
    expect(cards.length).toBe(7);
  });

  it('renders the rise animation card with its name', () => {
    const names = el.querySelectorAll('.anim-name');
    const texts = Array.from(names).map(n => n.textContent?.trim());
    expect(texts).toContain('rise');
  });

  it('renders the gen-shimmer animation card with its name', () => {
    const names = el.querySelectorAll('.anim-name');
    const texts = Array.from(names).map(n => n.textContent?.trim());
    expect(texts).toContain('gen-shimmer');
  });

  it('renders replay buttons for one-shot animations', () => {
    const replayBtns = el.querySelectorAll('.anim-replay-btn');
    // One-shot animations: rise, count-pulse, status-success-flash = 3 replay buttons
    expect(replayBtns.length).toBeGreaterThanOrEqual(1);
  });

  it('renders "Always Running" labels for infinite animations', () => {
    const labels = el.querySelectorAll('.anim-badge-label');
    const texts = Array.from(labels).map(l => l.textContent?.trim());
    expect(texts.some(t => t === 'Always Running')).toBeTrue();
  });

  describe('replay() method — classList mutation sequence', () => {
    let targetEl: HTMLElement;
    const testClass = 'anim-rise';

    beforeEach(() => {
      // Create a synthetic element so we can spy on its classList methods.
      targetEl = document.createElement('div');
      targetEl.classList.add(testClass);

      spyOn(targetEl.classList, 'remove').and.callThrough();
      spyOn(targetEl.classList, 'add').and.callThrough();
    });

    it('calls classList.remove before classList.add', () => {
      const callOrder: string[] = [];
      (targetEl.classList.remove as jasmine.Spy).and.callFake((...args: string[]) => {
        callOrder.push('remove:' + args[0]);
        targetEl.className = targetEl.className
          .split(' ')
          .filter(c => !args.includes(c))
          .join(' ');
      });
      (targetEl.classList.add as jasmine.Spy).and.callFake((...args: string[]) => {
        callOrder.push('add:' + args[0]);
        if (!targetEl.className.split(' ').includes(args[0])) {
          targetEl.className = (targetEl.className + ' ' + args[0]).trim();
        }
      });

      component.replay(targetEl, testClass);

      expect(callOrder[0]).toBe('remove:' + testClass);
      expect(callOrder[1]).toBe('add:' + testClass);
    });

    it('calls classList.remove with the animation class', () => {
      component.replay(targetEl, testClass);
      expect(targetEl.classList.remove).toHaveBeenCalledWith(testClass);
    });

    it('calls classList.add with the animation class after remove', () => {
      component.replay(targetEl, testClass);
      expect(targetEl.classList.add).toHaveBeenCalledWith(testClass);
    });

    it('accesses offsetWidth between remove and add to force reflow', () => {
      const accessOrder: string[] = [];

      (targetEl.classList.remove as jasmine.Spy).and.callFake(() => {
        accessOrder.push('remove');
      });
      (targetEl.classList.add as jasmine.Spy).and.callFake(() => {
        accessOrder.push('add');
      });

      // Spy on the offsetWidth getter to record when it is read.
      const offsetWidthSpy = spyOnProperty(targetEl, 'offsetWidth', 'get').and.callFake(() => {
        accessOrder.push('offsetWidth');
        return 0;
      });

      component.replay(targetEl, testClass);

      expect(offsetWidthSpy).toHaveBeenCalled();
      const removeIdx = accessOrder.indexOf('remove');
      const offsetIdx = accessOrder.indexOf('offsetWidth');
      const addIdx = accessOrder.indexOf('add');
      expect(removeIdx).toBeLessThan(offsetIdx);
      expect(offsetIdx).toBeLessThan(addIdx);
    });
  });

  it('has a demos array with seven entries matching the rendered cards', () => {
    expect(component.animations.length).toBe(7);
    const cards = el.querySelectorAll('.anim-card');
    expect(cards.length).toBe(component.animations.length);
  });
});
