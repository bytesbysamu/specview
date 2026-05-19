import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { DomSanitizer } from '@angular/platform-browser';

import { DemoResultComponent } from './demo-result.component';
import { LandingHandoffService, DemoResult } from '../landing-handoff.service';
import { createMockLandingHandoffService } from '../landing-handoff.service.mock';

const DEMO_FILES: DemoResult = {
  done: true,
  running: false,
  files: [
    { filename: 'analysis.md', content: '# Analysis\nContent here.' },
    { filename: 'epic.md', content: '# Epic\nEpic content.' },
  ],
};

describe('DemoResultComponent', () => {
  let fixture: ComponentFixture<DemoResultComponent>;
  let component: DemoResultComponent;
  let mockSvc: jasmine.SpyObj<LandingHandoffService>;

  function setup(handoffSlug: string | null = 'my-demo') {
    mockSvc = createMockLandingHandoffService(
      handoffSlug !== null
        ? { mode: 'demo', slug: handoffSlug }
        : { mode: 'none' }
    );

    TestBed.configureTestingModule({
      imports: [DemoResultComponent],
      providers: [
        { provide: LandingHandoffService, useValue: mockSvc },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => null } } },
        },
        {
          provide: DomSanitizer,
          useValue: {
            bypassSecurityTrustHtml: (html: string) => html,
            sanitize: (_ctx: unknown, val: string) => val,
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DemoResultComponent);
    component = fixture.componentInstance;
  }

  afterEach(() => TestBed.resetTestingModule());

  it('renders files from the demo JSON on successful fetch', async () => {
    setup('my-demo');
    mockSvc.fetchDemoResult.and.resolveTo(DEMO_FILES);

    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(mockSvc.fetchDemoResult).toHaveBeenCalledWith('my-demo');
    expect(component.files().length).toBe(2);
    expect(component.files()[0].filename).toBe('analysis.md');
  });

  it('auto-selects the first file after load', async () => {
    setup('my-demo');
    mockSvc.fetchDemoResult.and.resolveTo(DEMO_FILES);

    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    // analysis.md appears first in CANONICAL_ORDER
    expect(component.activeFilename()).toBe('analysis.md');
  });

  it('sets errorMsg when fetchDemoResult rejects', async () => {
    setup('bad-slug');
    mockSvc.fetchDemoResult.and.rejectWith({ statusText: 'Not Found' });

    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(component.errorMsg()).toBe('Not Found');
    expect(component.files().length).toBe(0);
  });

  it('sets errorMsg immediately when no slug is provided', async () => {
    setup(null);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.errorMsg()).toBe('No demo slug provided.');
    expect(mockSvc.fetchDemoResult).not.toHaveBeenCalled();
  });

  it('renders the conversion gate after files are loaded', async () => {
    setup('my-demo');
    mockSvc.fetchDemoResult.and.resolveTo(DEMO_FILES);

    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const gate = fixture.nativeElement.querySelector('[data-test="demo-conversion-gate"]');
    expect(gate).toBeTruthy();
  });

  it('selectFile updates the activeFilename signal', async () => {
    setup('my-demo');
    mockSvc.fetchDemoResult.and.resolveTo(DEMO_FILES);

    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    component.selectFile('epic.md');
    expect(component.activeFilename()).toBe('epic.md');
  });
});
