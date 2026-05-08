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
    return this.call('/api/brainstorm', {
      text,
      ...(question ? { question } : {}),
      ...(context ? { context } : {}),
    });
  }

  expand(text: string): Promise<TextOperationResponse> {
    return this.call('/api/expand', { text });
  }

  compress(text: string): Promise<TextOperationResponse> {
    return this.call('/api/compress', { text });
  }

  clarify(text: string): Promise<TextOperationResponse> {
    return this.call('/api/clarify', { text });
  }

  simplify(text: string): Promise<TextOperationResponse> {
    return this.call('/api/simplify', { text });
  }

  tldr(text: string): Promise<TextOperationResponse> {
    return this.call('/api/tldr', { text });
  }

  bullets(text: string): Promise<TextOperationResponse> {
    return this.call('/api/bullets', { text });
  }

  styleAs(text: string, style: string): Promise<TextOperationResponse> {
    return this.call('/api/rewrite', { text, style });
  }
}
