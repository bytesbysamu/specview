import { AiService } from './ai.service';
import { TextResponse } from '../api/models/text-response';

const MOCK_RESULT: TextResponse = { text: 'mock result', latencyMs: 100 };

export function createAiServiceMock(): jasmine.SpyObj<AiService> {
  const mock = jasmine.createSpyObj<AiService>('AiService', [
    'brainstorm', 'expand', 'compress', 'clarify',
    'simplify', 'tldr', 'bullets', 'styleAs',
  ]);
  mock.brainstorm.and.returnValue(Promise.resolve(MOCK_RESULT));
  mock.expand.and.returnValue(Promise.resolve(MOCK_RESULT));
  mock.compress.and.returnValue(Promise.resolve(MOCK_RESULT));
  mock.clarify.and.returnValue(Promise.resolve(MOCK_RESULT));
  mock.simplify.and.returnValue(Promise.resolve(MOCK_RESULT));
  mock.tldr.and.returnValue(Promise.resolve(MOCK_RESULT));
  mock.bullets.and.returnValue(Promise.resolve(MOCK_RESULT));
  mock.styleAs.and.returnValue(Promise.resolve(MOCK_RESULT));
  return mock;
}
