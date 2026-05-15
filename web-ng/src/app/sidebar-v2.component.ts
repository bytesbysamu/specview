import { Component, Input, Output, EventEmitter } from '@angular/core';
import { Project, Spec } from './services/projects.service';

export type StatusMode = 'idle' | 'active' | 'success-flash' | 'failure';
export type AiOp = 'expand' | 'compress' | 'clarify' | 'simplify' | 'tldr' | 'bullets' | 'brainstorm' | 'style';

@Component({
  selector: 'app-sidebar-v2',
  standalone: true,
  templateUrl: './sidebar-v2.component.html',
  styleUrl: './sidebar-v2.component.css',
})
export class SidebarV2Component {
  @Input() activeProject: Project | null = null;
  @Input() activeFile: string | null = null;
  @Input() expandedProject = '';
  @Input() mode: StatusMode = 'idle';
  @Input() specGenLoading = false;
  @Input() specGenStep: string | null = null;
  @Input() activeStepLabel = '';
  @Input() statusFailureMsg: string | null = null;
  @Input() shareLoading = false;
  @Input() shareUrl: string | null = null;
  @Input() shareCopied = false;
  @Input() canGenerateSpecs = false;
  @Input() canGenerateEpicGuide = false;
  @Input() epicGuideLoading = false;
  @Input() currentSpec: Spec | null = null;
  @Input() isBraindump = false;
  @Input() activeOp: string | null = null;
  @Input() aiLoading = false;
  @Input() aiResult: string | null = null;
  @Input() canRevert = false;
  @Input() canRedo = false;
  @Input() fileOpState: Record<string, 'running' | 'success' | 'failure'> = {};
  @Input() stylePresets: string[] = [];

  @Output() closeExpanded = new EventEmitter<void>();
  @Output() fileSelected = new EventEmitter<string>();
  @Output() retryClicked = new EventEmitter<void>();
  @Output() shareClicked = new EventEmitter<void>();
  @Output() generateSpecsClicked = new EventEmitter<void>();
  @Output() generateGuideClicked = new EventEmitter<void>();
  @Output() opToggled = new EventEmitter<AiOp>();
  @Output() styleRun = new EventEmitter<string>();
  @Output() undoClicked = new EventEmitter<void>();
  @Output() redoClicked = new EventEmitter<void>();

  onClose() { this.closeExpanded.emit(); }
  onFileSelect(filename: string) { this.fileSelected.emit(filename); }
  onRetry() { this.retryClicked.emit(); }
  onShare() { this.shareClicked.emit(); }
  onGenerateSpecs() { this.generateSpecsClicked.emit(); }
  onGenerateGuide() { this.generateGuideClicked.emit(); }
  onToggleOp(op: AiOp) { this.opToggled.emit(op); }
  onRunStyle(style: string) { this.styleRun.emit(style); }
  onUndo() { this.undoClicked.emit(); }
  onRedo() { this.redoClicked.emit(); }
}
