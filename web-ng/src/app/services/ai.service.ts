import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { map } from 'rxjs/operators';

import { brainstormText } from '../api/fn/operations/brainstorm-text';
import { expandText } from '../api/fn/operations/expand-text';
import { compressText } from '../api/fn/operations/compress-text';
import { clarifyText } from '../api/fn/operations/clarify-text';
import { simplifyText } from '../api/fn/operations/simplify-text';
import { tldrText } from '../api/fn/operations/tldr-text';
import { bulletsText } from '../api/fn/operations/bullets-text';
import { rewriteAction } from '../api/fn/operations/rewrite-action';
import { TextResponse } from '../api/models/text-response';


@Injectable({ providedIn: 'root' })
export class AiService {
  private readonly rootUrl = '';

  constructor(private http: HttpClient) {}

  brainstorm(text: string, question?: string, context?: string): Promise<TextResponse> {
    return firstValueFrom(
      brainstormText(this.http, this.rootUrl, {
        body: { text, ...(question ? { question } : {}), ...(context ? { context } : {}) },
      }).pipe(map(r => r.body!))
    );
  }

  expand(text: string): Promise<TextResponse> {
    return firstValueFrom(expandText(this.http, this.rootUrl, { body: { text } }).pipe(map(r => r.body!)));
  }

  compress(text: string): Promise<TextResponse> {
    return firstValueFrom(compressText(this.http, this.rootUrl, { body: { text } }).pipe(map(r => r.body!)));
  }

  clarify(text: string): Promise<TextResponse> {
    return firstValueFrom(clarifyText(this.http, this.rootUrl, { body: { text } }).pipe(map(r => r.body!)));
  }

  simplify(text: string): Promise<TextResponse> {
    return firstValueFrom(simplifyText(this.http, this.rootUrl, { body: { text } }).pipe(map(r => r.body!)));
  }

  tldr(text: string): Promise<TextResponse> {
    return firstValueFrom(tldrText(this.http, this.rootUrl, { body: { text } }).pipe(map(r => r.body!)));
  }

  bullets(text: string): Promise<TextResponse> {
    return firstValueFrom(bulletsText(this.http, this.rootUrl, { body: { text } }).pipe(map(r => r.body!)));
  }

  styleAs(text: string, style: string): Promise<TextResponse> {
    return firstValueFrom(
      rewriteAction(this.http, this.rootUrl, {
        body: { text, style: style as 'Concise' | 'Technical' | 'Executive' | 'Narrative' | 'Punchy' },
      }).pipe(map(r => r.body!))
    );
  }
}
