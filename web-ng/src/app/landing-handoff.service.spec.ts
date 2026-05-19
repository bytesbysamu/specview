import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { DOCUMENT } from '@angular/common';
import { LandingHandoffService } from './landing-handoff.service';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function encodeBase64Url(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Build a service instance with a mocked document.location.
 * Uses Angular's DOCUMENT token so we don't need to mutate window.location.
 */
function buildService(opts: {
  search?: string;
  hash?: string;
  pathname?: string;
}): LandingHandoffService {
  const { search = '', hash = '', pathname = '/' } = opts;

  TestBed.configureTestingModule({
    imports: [HttpClientTestingModule],
    providers: [
      {
        provide: DOCUMENT,
        useValue: {
          location: { search, hash, pathname },
        },
      },
    ],
  });

  return TestBed.inject(LandingHandoffService);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('LandingHandoffService', () => {
  afterEach(() => {
    TestBed.resetTestingModule();
  });

  // ── No handoff ─────────────────────────────────────────────────────────────

  it('returns mode=none when no query param and no hash are present', () => {
    const svc = buildService({ search: '', hash: '', pathname: '/' });
    expect(svc.handoff.mode).toBe('none');
  });

  it('returns mode=none when hash is present but pathname is not /analyze', () => {
    const encoded = encodeBase64Url('some braindump');
    const svc = buildService({ search: '', hash: `#${encoded}`, pathname: '/' });
    expect(svc.handoff.mode).toBe('none');
  });

  it('returns mode=none when ?demo is present but has an empty value', () => {
    const svc = buildService({ search: '?demo=', hash: '', pathname: '/' });
    expect(svc.handoff.mode).toBe('none');
  });

  // ── Demo mode ──────────────────────────────────────────────────────────────

  it('returns mode=demo with the correct slug from ?demo query param', () => {
    const svc = buildService({ search: '?demo=mobile-app', hash: '', pathname: '/' });
    expect(svc.handoff).toEqual({ mode: 'demo', slug: 'mobile-app' });
  });

  it('trims whitespace from the demo slug', () => {
    const svc = buildService({ search: '?demo=%20saas-feature%20', hash: '', pathname: '/' });
    if (svc.handoff.mode === 'demo') {
      expect(svc.handoff.slug).toBe('saas-feature');
    } else {
      fail('Expected mode=demo');
    }
  });

  it('prefers demo mode over a hash fragment when both are present', () => {
    const encoded = encodeBase64Url('some braindump');
    const svc = buildService({
      search: '?demo=side-project',
      hash: `#${encoded}`,
      pathname: '/analyze',
    });
    expect(svc.handoff.mode).toBe('demo');
  });

  // ── Real mode ──────────────────────────────────────────────────────────────

  it('returns mode=real with decoded braindump text from /analyze hash', () => {
    const original = 'I want to build a mobile app for cat photos';
    const encoded = encodeBase64Url(original);
    const svc = buildService({ search: '', hash: `#${encoded}`, pathname: '/analyze' });
    expect(svc.handoff).toEqual({ mode: 'real', braindump: original });
  });

  it('correctly decodes Unicode emoji in the braindump', () => {
    const original = 'My idea includes emoji: rocket launch  and some accents: café naïve';
    const encoded = encodeBase64Url(original);
    const svc = buildService({ search: '', hash: `#${encoded}`, pathname: '/analyze' });
    if (svc.handoff.mode === 'real') {
      expect(svc.handoff.braindump).toBe(original);
    } else {
      fail('Expected mode=real');
    }
  });

  it('correctly decodes CJK characters in the braindump', () => {
    const original = '日本語テスト: ユーザーストーリーを書く';
    const encoded = encodeBase64Url(original);
    const svc = buildService({ search: '', hash: `#${encoded}`, pathname: '/analyze' });
    if (svc.handoff.mode === 'real') {
      expect(svc.handoff.braindump).toBe(original);
    } else {
      fail('Expected mode=real');
    }
  });

  it('correctly decodes accented Latin characters in the braindump', () => {
    const original = 'Construire une application SaaS avec des fonctionnalités avancées';
    const encoded = encodeBase64Url(original);
    const svc = buildService({ search: '', hash: `#${encoded}`, pathname: '/analyze' });
    if (svc.handoff.mode === 'real') {
      expect(svc.handoff.braindump).toBe(original);
    } else {
      fail('Expected mode=real');
    }
  });

  it('returns mode=none when the hash on /analyze is malformed base64url', () => {
    const svc = buildService({ search: '', hash: '#!!!invalid!!!', pathname: '/analyze' });
    expect(svc.handoff.mode).toBe('none');
  });

  it('returns mode=none when the hash on /analyze decodes to an empty string', () => {
    const encoded = encodeBase64Url('   ');
    const svc = buildService({ search: '', hash: `#${encoded}`, pathname: '/analyze' });
    expect(svc.handoff.mode).toBe('none');
  });
});
