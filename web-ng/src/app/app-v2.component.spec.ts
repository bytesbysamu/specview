import { TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';

import { AppV2Component } from './app-v2.component';

describe('AppV2Component', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppV2Component],
      providers: [provideRouter([]), provideHttpClient()],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
  });

  afterEach(() => TestBed.resetTestingModule());

  it('creates the component', () => {
    const fixture = TestBed.createComponent(AppV2Component);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('renders the top bar', () => {
    const fixture = TestBed.createComponent(AppV2Component);
    fixture.detectChanges();
    const topBar = fixture.debugElement.nativeElement.querySelector('app-top-bar');
    expect(topBar).toBeTruthy();
  });

  it('renders a router-outlet', () => {
    const fixture = TestBed.createComponent(AppV2Component);
    fixture.detectChanges();
    const outlet = fixture.debugElement.nativeElement.querySelector('router-outlet');
    expect(outlet).toBeTruthy();
  });
});
