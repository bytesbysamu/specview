import { NavSection } from './section-nav.component';
import { ContextFile } from './project-grid.component';

export const NAV_SECTIONS: NavSection[] = [
  { id: 'context',        label: 'Context',        icon: 'ruler' },
  { id: 'all',            label: 'All',             icon: '' },
  { id: 'Active',         label: 'Active',          icon: 'zap' },
  { id: 'Ready to build', label: 'Ready to build',  icon: 'hammer' },
  { id: 'Specced',        label: 'Specced',         icon: 'check-circle' },
  { id: 'Braindumps',     label: 'Braindumps',      icon: 'brain' },
  { id: 'Archive',        label: 'Archive',         icon: 'archive' },
];

export const CONTEXT_FILES: ContextFile[] = [
  { key: 'builder',    label: 'Builder',    desc: 'How to build with spec-doc' },
  { key: 'principles', label: 'Principles', desc: 'Core development principles' },
  { key: 'codebase',   label: 'Codebase',   desc: 'Codebase overview & conventions' },
  { key: 'references', label: 'References', desc: 'External references & links' },
  { key: 'quality',    label: 'Quality',    desc: 'Quality rules & linting' },
  { key: 'versions',   label: 'Versions',   desc: 'Deployment fact sheet' },
];
