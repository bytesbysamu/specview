import { Component, Input, Output, EventEmitter } from '@angular/core';
import { SafeHtml } from '@angular/platform-browser';
import { Project, Spec } from './services/projects.service';

@Component({
  selector: 'app-reader-panel',
  standalone: true,
  templateUrl: './reader-panel.component.html',
  styleUrl: './reader-panel.component.css',
})
export class ReaderPanelComponent {
  @Input() activeProject: Project | null = null;
  @Input() currentSpec: Spec | null = null;
  @Input() accessDenied = false;
  @Input() expandedTitle = '';
  @Input() expandedProject = '';
  @Input() activeFileType: string | null = null;
  @Input() parsedContent: SafeHtml = '';
  @Input() parsedAiResult: SafeHtml = '';
  @Input() diffHtmlUnified: SafeHtml = '';

  // AI state
  @Input() aiResult: string | null = null;
  @Input() aiLoading = false;
  @Input() aiError = false;
  @Input() aiLatencyMs: number | null = null;
  @Input() activeOp: string | null = null;
  @Input() isAdditiveOp = false;
  @Input() billingError: string | null = null;
  @Input() copied = false;

  // Brainstorm
  @Input() brainstormQuestion = '';
  @Input() canGenerateSpecs = false;
  @Input() specGenLoading = false;
  @Input() specGenProjectName: string | null = null;
  @Input() specGenStep: string | null = null;
  @Input() specGenError: string | null = null;
  @Input() specGenFailedStep: string | null = null;
  @Input() cancelling = false;

  @Output() closeExpanded = new EventEmitter<void>();
  @Output() applyResult = new EventEmitter<void>();
  @Output() dismissResult = new EventEmitter<void>();
  @Output() copyResult = new EventEmitter<void>();
  @Output() followupBrainstorm = new EventEmitter<string>();
  @Output() brainstormQuestionChange = new EventEmitter<string>();
  @Output() generateFromBrainstormResult = new EventEmitter<void>();
  @Output() cancelClicked = new EventEmitter<void>();
  @Output() retryFailedStep = new EventEmitter<void>();

  onApply() { this.applyResult.emit(); }
  onDismiss() { this.dismissResult.emit(); }
  onCopy() { this.copyResult.emit(); }
  onClose() { this.closeExpanded.emit(); }
  onFollowup(question: string) { this.followupBrainstorm.emit(question); }
  onQuestionChange(value: string) { this.brainstormQuestionChange.emit(value); }
  onGenerateFromBrainstorm() { this.generateFromBrainstormResult.emit(); }
  onCancel() { this.cancelClicked.emit(); }
  onRetryStep() { this.retryFailedStep.emit(); }
}
