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
  private readonly base = '/api/ai/text';

  constructor(private http: HttpClient) {}

  rewrite(text: string, instructions: string): Promise<TextOperationResponse> {
    return firstValueFrom(
      this.http.post<TextOperationResponse>(`${this.base}/rewrite`, { text, instructions })
        .pipe(timeout(AI_TIMEOUT_MS))
    );
  }

  generate(prompt: string): Promise<TextOperationResponse> {
    return firstValueFrom(
      this.http.post<TextOperationResponse>(`${this.base}/generate`, { prompt, tone: 'balanced' })
        .pipe(timeout(AI_TIMEOUT_MS))
    );
  }

  expand(text: string): Promise<TextOperationResponse> {
    return this.rewrite(text, 'Expand this with more detail and examples. Keep the same structure.');
  }

  compress(text: string): Promise<TextOperationResponse> {
    return this.rewrite(text, 'Make this more concise while keeping all key information.');
  }

  clarify(text: string): Promise<TextOperationResponse> {
    return this.rewrite(text, 'Make this clearer and easier to understand. Fix any ambiguity.');
  }
}
