import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { AiService } from './ai.service';
import { TextResponse } from '../api/models/text-response';

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

function makeTextResponse(overrides: Partial<TextResponse> = {}): TextResponse {
  return { text: 'result text', latencyMs: 42, ...overrides };
}

// ---------------------------------------------------------------------------
// AiService
// ---------------------------------------------------------------------------

describe('AiService', () => {
  let service: AiService;
  let httpController: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    });

    service = TestBed.inject(AiService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpController.verify();
  });

  // -------------------------------------------------------------------------
  // brainstorm
  // -------------------------------------------------------------------------

  describe('brainstorm', () => {
    it('POSTs to /api/brainstorm with text only when optional fields are absent', async () => {
      const promise = service.brainstorm('input text');

      const req = httpController.expectOne('/api/brainstorm');
      expect(req.request.method).toBe('POST');
      const body = req.request.body;
      expect(body['text']).toBe('input text');
      expect(body['question']).toBeUndefined();
      expect(body['context']).toBeUndefined();
      req.flush(makeTextResponse());

      await promise;
    });

    it('includes question in POST body when provided', async () => {
      const promise = service.brainstorm('input text', 'what is this?');

      const req = httpController.expectOne('/api/brainstorm');
      expect(req.request.body['question']).toBe('what is this?');
      req.flush(makeTextResponse());

      await promise;
    });

    it('includes context in POST body when provided', async () => {
      const promise = service.brainstorm('input text', undefined, 'extra context');

      const req = httpController.expectOne('/api/brainstorm');
      expect(req.request.body['context']).toBe('extra context');
      req.flush(makeTextResponse());

      await promise;
    });

    it('includes both question and context when both are provided', async () => {
      const promise = service.brainstorm('input text', 'a question', 'some context');

      const req = httpController.expectOne('/api/brainstorm');
      expect(req.request.body['question']).toBe('a question');
      expect(req.request.body['context']).toBe('some context');
      req.flush(makeTextResponse());

      await promise;
    });

    it('resolves with the body of the HTTP response', async () => {
      const expected = makeTextResponse({ text: 'brainstorm output', latencyMs: 100 });
      const promise = service.brainstorm('input text');

      const req = httpController.expectOne('/api/brainstorm');
      req.flush(expected);

      const result = await promise;
      expect(result).toEqual(expected);
    });

    it('omits question from body when question is empty string (falsy)', async () => {
      const promise = service.brainstorm('text', '');

      const req = httpController.expectOne('/api/brainstorm');
      expect(req.request.body['question']).toBeUndefined();
      req.flush(makeTextResponse());

      await promise;
    });

    it('omits context from body when context is empty string (falsy)', async () => {
      const promise = service.brainstorm('text', undefined, '');

      const req = httpController.expectOne('/api/brainstorm');
      expect(req.request.body['context']).toBeUndefined();
      req.flush(makeTextResponse());

      await promise;
    });
  });

  // -------------------------------------------------------------------------
  // expand
  // -------------------------------------------------------------------------

  describe('expand', () => {
    it('POSTs to /api/expand with text', async () => {
      const promise = service.expand('short text');

      const req = httpController.expectOne('/api/expand');
      expect(req.request.method).toBe('POST');
      expect(req.request.body['text']).toBe('short text');
      req.flush(makeTextResponse({ text: 'expanded text' }));

      await promise;
    });

    it('resolves with the response body', async () => {
      const expected = makeTextResponse({ text: 'expanded' });
      const promise = service.expand('input');

      const req = httpController.expectOne('/api/expand');
      req.flush(expected);

      expect(await promise).toEqual(expected);
    });
  });

  // -------------------------------------------------------------------------
  // compress
  // -------------------------------------------------------------------------

  describe('compress', () => {
    it('POSTs to /api/compress with text', async () => {
      const promise = service.compress('long text here');

      const req = httpController.expectOne('/api/compress');
      expect(req.request.method).toBe('POST');
      expect(req.request.body['text']).toBe('long text here');
      req.flush(makeTextResponse({ text: 'compressed' }));

      await promise;
    });

    it('resolves with the response body', async () => {
      const expected = makeTextResponse({ text: 'compressed' });
      const promise = service.compress('input');

      const req = httpController.expectOne('/api/compress');
      req.flush(expected);

      expect(await promise).toEqual(expected);
    });
  });

  // -------------------------------------------------------------------------
  // clarify
  // -------------------------------------------------------------------------

  describe('clarify', () => {
    it('POSTs to /api/clarify with text', async () => {
      const promise = service.clarify('confusing text');

      const req = httpController.expectOne('/api/clarify');
      expect(req.request.method).toBe('POST');
      expect(req.request.body['text']).toBe('confusing text');
      req.flush(makeTextResponse({ text: 'clarified' }));

      await promise;
    });

    it('resolves with the response body', async () => {
      const expected = makeTextResponse({ text: 'clarified output' });
      const promise = service.clarify('input');

      const req = httpController.expectOne('/api/clarify');
      req.flush(expected);

      expect(await promise).toEqual(expected);
    });
  });

  // -------------------------------------------------------------------------
  // simplify
  // -------------------------------------------------------------------------

  describe('simplify', () => {
    it('POSTs to /api/simplify with text', async () => {
      const promise = service.simplify('complex text');

      const req = httpController.expectOne('/api/simplify');
      expect(req.request.method).toBe('POST');
      expect(req.request.body['text']).toBe('complex text');
      req.flush(makeTextResponse({ text: 'simplified' }));

      await promise;
    });

    it('resolves with the response body', async () => {
      const expected = makeTextResponse({ text: 'simple output' });
      const promise = service.simplify('input');

      const req = httpController.expectOne('/api/simplify');
      req.flush(expected);

      expect(await promise).toEqual(expected);
    });
  });

  // -------------------------------------------------------------------------
  // tldr
  // -------------------------------------------------------------------------

  describe('tldr', () => {
    it('POSTs to /api/tldr with text', async () => {
      const promise = service.tldr('very long document');

      const req = httpController.expectOne('/api/tldr');
      expect(req.request.method).toBe('POST');
      expect(req.request.body['text']).toBe('very long document');
      req.flush(makeTextResponse({ text: 'tl;dr summary' }));

      await promise;
    });

    it('resolves with the response body', async () => {
      const expected = makeTextResponse({ text: 'summary' });
      const promise = service.tldr('input');

      const req = httpController.expectOne('/api/tldr');
      req.flush(expected);

      expect(await promise).toEqual(expected);
    });
  });

  // -------------------------------------------------------------------------
  // bullets
  // -------------------------------------------------------------------------

  describe('bullets', () => {
    it('POSTs to /api/bullets with text', async () => {
      const promise = service.bullets('prose text to convert');

      const req = httpController.expectOne('/api/bullets');
      expect(req.request.method).toBe('POST');
      expect(req.request.body['text']).toBe('prose text to convert');
      req.flush(makeTextResponse({ text: '- bullet one\n- bullet two' }));

      await promise;
    });

    it('resolves with the response body', async () => {
      const expected = makeTextResponse({ text: '- item' });
      const promise = service.bullets('input');

      const req = httpController.expectOne('/api/bullets');
      req.flush(expected);

      expect(await promise).toEqual(expected);
    });
  });

  // -------------------------------------------------------------------------
  // styleAs
  // -------------------------------------------------------------------------

  describe('styleAs', () => {
    it('POSTs to /api/rewrite with text and style', async () => {
      const promise = service.styleAs('some text', 'Concise');

      const req = httpController.expectOne('/api/rewrite');
      expect(req.request.method).toBe('POST');
      expect(req.request.body['text']).toBe('some text');
      expect(req.request.body['style']).toBe('Concise');
      req.flush(makeTextResponse({ text: 'concise output' }));

      await promise;
    });

    it('passes style value as-is to the request body', async () => {
      const promise = service.styleAs('text', 'Technical');

      const req = httpController.expectOne('/api/rewrite');
      expect(req.request.body['style']).toBe('Technical');
      req.flush(makeTextResponse());

      await promise;
    });

    it('resolves with the response body', async () => {
      const expected = makeTextResponse({ text: 'styled result' });
      const promise = service.styleAs('input', 'Executive');

      const req = httpController.expectOne('/api/rewrite');
      req.flush(expected);

      expect(await promise).toEqual(expected);
    });
  });
});
