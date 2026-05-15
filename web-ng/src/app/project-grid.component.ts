import { Component, Input, Output, EventEmitter } from '@angular/core';
import { Project } from './services/projects.service';
import { Section } from './services/section-taxonomy.service';

export interface ContextFile {
  key: string;
  label: string;
  desc: string;
}

export interface ProjectsBySection {
  section: Section;
  projects: Project[];
}

@Component({
  selector: 'app-project-grid',
  standalone: true,
  templateUrl: './project-grid.component.html',
  styleUrl: './project-grid.component.css',
})
export class ProjectGridComponent {
  @Input() activeSection = 'all';
  @Input() filteredProjects: Project[] = [];
  @Input() projectsBySection: ProjectsBySection[] = [];
  @Input() columns: Project[][] = [];
  @Input() contextFiles: ContextFile[] = [];
  @Input() sectionLabel = 'Projects';

  /** Callback to get a teaser string for a project card. */
  @Input() teaserFn: (p: Project) => string = () => '';

  /** Callback to get a section name for a project. */
  @Input() sectionFn: (p: Project) => Section = () => 'Braindumps';

  @Output() projectSelected = new EventEmitter<string>();
  @Output() contextOpened = new EventEmitter<string>();

  onSelectProject(id: string) {
    this.projectSelected.emit(id);
  }

  onOpenContext(key: string) {
    this.contextOpened.emit(key);
  }
}
