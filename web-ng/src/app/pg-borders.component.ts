import { Component, ChangeDetectionStrategy } from '@angular/core';

interface BorderDemo {
  label: string;
  description: string;
  cssClass: string;
}

@Component({
  selector: 'app-pg-borders',
  standalone: true,
  templateUrl: './pg-borders.component.html',
  styleUrl: './pg-borders.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PgBordersComponent {
  readonly demos: BorderDemo[] = [
    {
      label: '1px solid var(--border)',
      description: 'Content divider',
      cssClass: 'demo-border--divider',
    },
    {
      label: '2px solid var(--ink)',
      description: 'Section label underline',
      cssClass: 'demo-border--section-underline',
    },
    {
      label: '3px solid var(--ink)',
      description: 'Major structural break',
      cssClass: 'demo-border--structural',
    },
    {
      label: '3px solid var(--border-dark)',
      description: 'hr thick rule',
      cssClass: 'demo-border--hr-thick',
    },
    {
      label: 'border-left: 3px solid var(--ink-muted)',
      description: 'Code block accent',
      cssClass: 'demo-border--code-accent',
    },
    {
      label: 'border-left: 2px solid var(--ink)',
      description: 'Sidebar active file',
      cssClass: 'demo-border--sidebar-active',
    },
    {
      label: '1px dashed var(--accent)',
      description: 'Generate button',
      cssClass: 'demo-border--generate-btn',
    },
  ];
}
