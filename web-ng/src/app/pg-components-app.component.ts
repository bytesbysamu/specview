import { Component, ChangeDetectionStrategy } from '@angular/core';

interface ContextCard {
  label: string;
  desc: string;
}

@Component({
  selector: 'app-pg-components-app',
  standalone: true,
  templateUrl: './pg-components-app.component.html',
  styleUrl: './pg-components-app.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PgComponentsAppComponent {
  readonly contextCards: ContextCard[] = [
    {
      label: 'Product Brief',
      desc: 'Core vision, target audience, and constraints for the initiative.',
    },
    {
      label: 'Architecture Decision',
      desc: 'Selected technology stack and key architectural trade-offs.',
    },
    {
      label: 'Design Principles',
      desc: 'Visual language, interaction patterns, and accessibility standards.',
    },
  ];
}
