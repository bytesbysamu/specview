import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { TokenLifecycleService } from './token-lifecycle.service';

describe('TokenLifecycleService', () => {
  let service: TokenLifecycleService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule],
    });
    service = TestBed.inject(TokenLifecycleService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('isLoggedIn is false when localStorage has no token', () => {
    expect(service.isLoggedIn()).toBeFalse();
  });

  it('storeToken sets isLoggedIn to true', () => {
    service.storeToken('fake.jwt.token');
    expect(service.isLoggedIn()).toBeTrue();
  });

  it('getRawToken returns null when no token stored', () => {
    expect(service.getRawToken()).toBeNull();
  });

  it('getRawToken returns stored token after storeToken', () => {
    service.storeToken('fake.jwt.token');
    expect(service.getRawToken()).toBe('fake.jwt.token');
  });
});
