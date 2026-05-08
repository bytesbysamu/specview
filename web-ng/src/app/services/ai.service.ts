import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { timeout } from 'rxjs/operators';

const AI_TIMEOUT_MS = 1_800_000;

export interface TextOperationResponse {
  text: string;
  latencyMs: number;
}

@Injectable({ providedIn: 'root' })
export class AiService {
  private readonly rootUrl = '';

  constructor(private http: HttpClient) {}

  private call(endpoint: string, body: object): Promise<TextOperationResponse> {
    return firstValueFrom(
      this.http.post<TextOperationResponse>(`${this.rootUrl}${endpoint}`, body, {
        observe: 'body',
      }).pipe(timeout(AI_TIMEOUT_MS))
    );
  }

  brainstorm(text: string, question?: string, context?: string): Promise<TextOperationResponse> {
    return this.call('/api/operations/brainstorm-text', {
      text,
      ...(question ? { question } : {}),
      ...(context ? { context } : {}),
    });
  }

  expand(text: string): Promise<TextOperationResponse> {
    return this.call('/api/operations/expand-text', { text });
  }

  compress(text: string): Promise<TextOperationResponse> {
    return this.call('/api/operations/compress-text', { text });
  }

  clarify(text: string): Promise<TextOperationResponse> {
    return this.call('/api/operations/clarify-text', { text });
  }

  simplify(text: string): Promise<TextOperationResponse> {
    return this.call('/api/operations/simplify-text', { text });
  }

  tldr(text: string): Promise<TextOperationResponse> {
    return this.call('/api/operations/tldr-text', { text });
  }

  bullets(text: string): Promise<TextOperationResponse> {
    return this.call('/api/operations/bullets-text', { text });
  }

  styleAs(text: string, style: string): Promise<TextOperationResponse> {
    return this.call('/api/operations/rewrite-action', { text, style });
  }
}
