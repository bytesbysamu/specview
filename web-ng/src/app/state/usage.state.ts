import { signal } from '@angular/core';

export interface UsageRemaining {
  remaining: number;
  limit: number;
}

export const usageRemaining = signal<UsageRemaining | null>(null);
