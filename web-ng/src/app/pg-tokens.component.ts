import {
  Component,
  ChangeDetectionStrategy,
  OnInit,
  OnDestroy,
  signal,
  computed,
} from '@angular/core';
import { getCssVar } from './css-read.util';

interface ColorToken {
  name: string;
  value: string;
}

@Component({
  selector: 'app-pg-tokens',
  standalone: true,
  templateUrl: './pg-tokens.component.html',
  styleUrl: './pg-tokens.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PgTokensComponent implements OnInit, OnDestroy {
  private observer: MutationObserver | null = null;
  private _tick = signal(0);

  readonly colorVarNames = [
    '--bg',
    '--ink',
    '--ink-light',
    '--ink-muted',
    '--border',
    '--border-dark',
    '--accent',
    '--red',
    '--status-idle',
    '--status-active',
    '--status-success',
    '--status-failure',
    '--status-running',
    '--status-success-bg',
    '--code-bg',
  ];

  readonly spacingSizes = [8, 12, 16, 20, 24, 32, 48];

  readonly typographySpecimens = [
    { label: 'Serif 36px', family: 'var(--serif)', size: '36px', sample: 'The Quick Brown Fox' },
    { label: 'Serif 24px', family: 'var(--serif)', size: '24px', sample: 'The Quick Brown Fox' },
    { label: 'Serif 18px', family: 'var(--serif)', size: '18px', sample: 'The Quick Brown Fox' },
    { label: 'Body 15px', family: 'var(--body)', size: '15px', sample: 'Body copy — Source Serif 4 at reading size.' },
    { label: 'Sans 13px', family: 'var(--sans)', size: '13px', sample: 'UI label — Source Sans 3 regular.' },
    { label: 'Sans 11px', family: 'var(--sans)', size: '11px', sample: 'OVERLINE — SOURCE SANS 3 SMALL CAPS.' },
  ];

  colorTokens = computed<ColorToken[]>(() => {
    void this._tick(); // subscribe to tick so computed re-runs on observer signal
    return this.colorVarNames.map(name => ({
      name,
      value: getCssVar(name),
    }));
  });

  ngOnInit(): void {
    this.observer = new MutationObserver(() => {
      this._tick.update(n => n + 1);
    });
    this.observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
    this.observer = null;
  }
}
