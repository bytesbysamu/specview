import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { filter, map, timeout } from 'rxjs/operators';
import { HttpResponse } from '@angular/common/http';

import { ApiConfiguration } from '../api/api-configuration';
import { brainstormText } from '../api/fn/operations/brainstorm-text';
import { expandText } from '../api/fn/operations/expand-text';
import { compressText } from '../api/fn/operations/compress-text';
import { clarifyText } from '../api/fn/operations/clarify-text';
import { simplifyText } from '../api/fn/operations/simplify-text';
import { tldrText } from '../api/fn/operations/tldr-text';
import { bulletsText } from '../api/fn/operations/bullets-text';
import { rewriteAction } from '../api/fn/operations/rewrite-action';

const AI_TIMEOUT_MS = 1_800_000;

export interface TextOperationResponse {
  text: string;
  latencyMs: number;
}

@Injectable({ providedIn: 'root' })
export class AiService {
  private readonly rootUrl = '';

  constructor(
    private http: HttpClient,
    private apiConfig: ApiConfiguration,
  ) {}

  private call<T extends TextOperationResponse>(
    fn: (http: HttpClient, rootUrl: string, params: any) => any,
    body: object,
  ): Promise<T> {
    return firstValueFrom(
      fn(this.http, this.rootUrl, { body }).pipe(
        filter((r: any) => r instanceof HttpResponse),
        map((r: any) => r.body as T),
        timeout(AI_TIMEOUT_MS),
      )
    );
  }

  brainstorm(text: string, question?: string, context?: string): Promise<TextOperationResponse> {
    return this.call(brainstormText, { text, ...(question ? { question } : {}), ...(context ? { context } : {}) });
  }

  expand(text: string): Promise<TextOperationResponse> {
    return this.call(expandText, { text });
  }

  compress(text: string): Promise<TextOperationResponse> {
    return this.call(compressText, { text });
  }

  clarify(text: string): Promise<TextOperationResponse> {
    return this.call(clarifyText, { text });
  }

  simplify(text: string): Promise<TextOperationResponse> {
    return this.call(simplifyText, { text });
  }

  tldr(text: string): Promise<TextOperationResponse> {
    return this.call(tldrText, { text });
  }

  bullets(text: string): Promise<TextOperationResponse> {
    return this.call(bulletsText, { text });
  }

  styleAs(text: string, style: string): Promise<TextOperationResponse> {
    return this.call(rewriteAction, { text, style });
  }
}
