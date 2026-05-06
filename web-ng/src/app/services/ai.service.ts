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

  simplify(text: string): Promise<TextOperationResponse> {
    return this.rewrite(text, 'Rewrite in plain language — remove jargon, simplify for a non-technical reader, keep all key points.');
  }

  tldr(text: string): Promise<TextOperationResponse> {
    return this.rewrite(text, 'Write a concise TL;DR executive summary of the key points as 4-6 tight bullet points. Lead with the most important insight.');
  }

  bullets(text: string): Promise<TextOperationResponse> {
    return this.rewrite(text, 'Convert this into well-organised bullet points grouped by logical sections. Keep all key information.');
  }

  brainstorm(text: string): Promise<TextOperationResponse> {
    return this.rewrite(text, [
      'You are a product thinking partner. Given this raw brain dump, generate a structured brainstorm response with four sections:',
      '1. **Key Themes** — the 3-5 core ideas buried in this dump',
      '2. **Hidden Connections** — non-obvious links between the ideas',
      '3. **Open Questions** — 4-6 sharp questions this raises that need answering',
      '4. **Ideas to Explore** — 5+ concrete next steps, experiments, or extensions that follow from this thinking',
      'Be provocative, creative, and direct. Do not repeat the original text back.',
    ].join('\n'));
  }

  styleAs(text: string, style: string): Promise<TextOperationResponse> {
    const instructions: Record<string, string> = {
      'Concise':    'Rewrite in a concise style — cut to the essentials, no fluff, every word earns its place.',
      'Technical':  'Rewrite with deeper technical precision and specificity — be exact, use correct terminology.',
      'Executive':  'Rewrite as an executive brief — high-level, decision-focused, outcome-oriented.',
      'Narrative':  'Rewrite with a clear narrative arc — story-driven, engaging, builds to a point.',
      'Punchy':     'Rewrite in a bold, confident, action-oriented style — short sentences, strong verbs.',
    };
    return this.rewrite(text, instructions[style] ?? `Rewrite in a ${style} style.`);
  }
}
