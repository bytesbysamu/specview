import { Component, ChangeDetectionStrategy } from '@angular/core';

interface AnimationDemo {
  name: string;
  timing: string;
  cssClass: string;
  infinite: boolean;
  description: string;
}

@Component({
  selector: 'app-pg-animations',
  standalone: true,
  templateUrl: './pg-animations.component.html',
  styleUrl: './pg-animations.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PgAnimationsComponent {
  readonly animations: AnimationDemo[] = [
    {
      name: 'rise',
      timing: '0.2s ease, one-shot',
      cssClass: 'anim-rise',
      infinite: false,
      description: 'Panel enter',
    },
    {
      name: 'gen-shimmer',
      timing: '1.6s linear, infinite',
      cssClass: 'anim-gen-shimmer',
      infinite: true,
      description: 'Status bar track',
    },
    {
      name: 'poll-pulse',
      timing: '0.7s ease-out, infinite alternate',
      cssClass: 'anim-poll-pulse',
      infinite: true,
      description: 'Polling dot',
    },
    {
      name: 'dot-pulse',
      timing: '1s ease-in-out, infinite',
      cssClass: 'anim-dot-pulse',
      infinite: true,
      description: 'Thinking dots',
    },
    {
      name: 'thinking-pulse',
      timing: '1.2s ease-in-out, infinite',
      cssClass: 'anim-thinking-pulse',
      infinite: true,
      description: 'AI loading',
    },
    {
      name: 'count-pulse',
      timing: '200ms ease-out, one-shot',
      cssClass: 'anim-count-pulse',
      infinite: false,
      description: 'Badge flash',
    },
    {
      name: 'status-success-flash',
      timing: '2s ease-out, one-shot',
      cssClass: 'anim-status-success-flash',
      infinite: false,
      description: 'Success bar',
    },
  ];

  replay(el: HTMLElement, cls: string): void {
    el.classList.remove(cls);
    void el.offsetWidth; // force reflow
    el.classList.add(cls);
  }
}
