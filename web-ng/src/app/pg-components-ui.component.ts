import { Component, ChangeDetectionStrategy } from '@angular/core';

interface OpChip {
  label: string;
  active: boolean;
  accent: boolean;
}

interface StyleChip {
  label: string;
}

interface ButtonDemo {
  label: string;
  cssClass: string;
  disabled: boolean;
}

interface BadgeDemo {
  label: string;
  modifier: string;
}

@Component({
  selector: 'app-pg-components-ui',
  standalone: true,
  templateUrl: './pg-components-ui.component.html',
  styleUrl: './pg-components-ui.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PgComponentsUiComponent {
  readonly opChips: OpChip[] = [
    { label: 'Condense',   active: false, accent: false },
    { label: 'Expand',     active: true,  accent: false },
    { label: 'Style',      active: false, accent: false },
    { label: 'Brainstorm', active: false, accent: true  },
  ];

  readonly styleChips: StyleChip[] = [
    { label: 'Technical' },
    { label: 'Concise'   },
    { label: 'Formal'    },
    { label: 'Plain'     },
  ];

  readonly buttons: ButtonDemo[] = [
    { label: 'New Project', cssClass: 'new-project-btn', disabled: false },
    { label: 'New Project (disabled)', cssClass: 'new-project-btn', disabled: true },
    { label: 'Logout', cssClass: 'logout-btn', disabled: false },
    { label: 'Logout (disabled)', cssClass: 'logout-btn', disabled: true },
    { label: 'Apply Changes', cssClass: 'editor-apply-btn', disabled: false },
    { label: 'Apply (disabled)', cssClass: 'editor-apply-btn', disabled: true },
    { label: 'Generate Spec', cssClass: 'sidebar-generate', disabled: false },
    { label: 'Generate (disabled)', cssClass: 'sidebar-generate', disabled: true },
  ];

  readonly badges: BadgeDemo[] = [
    { label: 'Default',  modifier: ''            },
    { label: 'New',      modifier: 'badge--new'  },
    { label: 'Complete', modifier: 'badge--complete' },
    { label: 'Ready',    modifier: 'badge--ready' },
  ];
}
