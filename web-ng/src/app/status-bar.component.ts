import { Component, Input, Output, EventEmitter } from '@angular/core';

export type StatusMode = 'idle' | 'active' | 'success-flash' | 'failure';

@Component({
  selector: 'app-status-bar',
  standalone: true,
  templateUrl: './status-bar.component.html',
  styleUrl: './status-bar.component.css',
})
export class StatusBarComponent {
  @Input() mode: StatusMode = 'idle';
  @Input() specGenProjectName: string | null = null;
  @Input() specGenStep: string | null = null;
  @Input() specGenElapsed = '0.0s';
  @Input() specGenJobId: string | null = null;
  @Input() statusFailureMsg: string | null = null;
  @Input() cancelling = false;

  @Output() cancelClicked = new EventEmitter<void>();
  @Output() retryClicked = new EventEmitter<void>();

  onCancel() {
    this.cancelClicked.emit();
  }

  onRetry() {
    this.retryClicked.emit();
  }
}
