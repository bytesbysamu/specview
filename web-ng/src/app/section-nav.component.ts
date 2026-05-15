import { Component, Input, Output, EventEmitter, signal } from '@angular/core';

export interface NavSection {
  id: string;
  label: string;
  icon: string;
}

@Component({
  selector: 'app-section-nav',
  standalone: true,
  templateUrl: './section-nav.component.html',
  styleUrl: './section-nav.component.css',
})
export class SectionNavComponent {
  @Input() sections: NavSection[] = [];
  @Input() activeSection = '';
  @Input() sectionCounts: Record<string, number> = {};
  @Input() pulsingSections: Set<string> = new Set();
  @Input() contextFileCount = 0;

  @Output() sectionSelected = new EventEmitter<string>();

  selectSection(id: string) {
    this.sectionSelected.emit(id);
  }
}
