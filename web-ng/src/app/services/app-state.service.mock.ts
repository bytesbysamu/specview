import { signal, computed } from '@angular/core';
import { AppStateService } from './app-state.service';
import { Project } from './projects.service';

/**
 * Creates a typed Jasmine spy object for AppStateService.
 *
 * Signals are real writeable signals so specs can call .set() and read their value.
 * Computed signals are backed by real computed() over those signals.
 * Methods are Jasmine spies.
 */
export function createMockAppStateService(): jasmine.SpyObj<AppStateService> {
  // ── State signals ──────────────────────────────────
  const projects = signal<Project[]>([]);
  const activeSection = signal('all');
  const activeProject = signal<Project | null>(null);
  const activeFile = signal<string | null>(null);
  const searchQuery = signal('');
  const isDark = signal(false);
  const updateBanner = signal('');
  const knownCount = signal(0);

  const aiLoading = signal(false);
  const aiResult = signal<string | null>(null);
  const aiLatencyMs = signal<number | null>(null);
  const aiError = signal(false);
  const activeOp = signal<string | null>(null);
  const copied = signal(false);

  const contextContent = signal<string | null>(null);
  const contextTitle = signal('');

  const showCreateModal = signal(false);
  const specGenLoading = signal(false);
  const specGenError = signal<string | null>(null);
  const specGenStep = signal<string | null>(null);
  const specGenProjectName = signal<string | null>(null);
  const specGenJobId = signal<string | null>(null);
  const specGenFailedStep = signal<string | null>(null);
  const cancelling = signal(false);

  const accessDenied = signal(false);

  const epicGuideLoading = signal(false);
  const epicGuideError = signal<string | null>(null);

  const shareUrl = signal<string | null>(null);
  const shareCopied = signal(false);
  const shareLoading = signal(false);

  const polling = signal(false);
  const pollOk = signal(true);
  const pollingError = signal<string | null>(null);
  const billingError = signal<string | null>(null);

  const lastSyncAt = signal<number | null>(null);
  const lastSyncElapsed = signal<number>(0);
  const statusMode = signal<'idle' | 'active' | 'success-flash' | 'failure'>('idle');
  const statusFailureMsg = signal<string | null>(null);

  const specGenStartTime = signal<number | null>(null);
  const specGenElapsed = signal<string>('0.0s');

  const activeOpFile = signal<string | null>(null);
  const fileOpState = signal<Record<string, 'running' | 'success' | 'failure'>>({});

  const pulsingSections = signal<Set<string>>(new Set());

  const undoStack = signal<Record<string, string[]>>({});
  const redoStack = signal<Record<string, string[]>>({});

  const brainstormQuestion = signal('');

  // ── Computed signals ───────────────────────────────
  const showGrid = computed(() => !activeProject() && contextContent() === null && !accessDenied());
  const showExpanded = computed(() => !!activeProject() || contextContent() !== null || accessDenied());
  const canRevert = computed(() => {
    const proj = activeProject();
    const file = activeFile();
    if (!proj || !file) return false;
    return (undoStack()[`${proj.id}/${file}`]?.length ?? 0) > 0;
  });
  const canRedo = computed(() => {
    const proj = activeProject();
    const file = activeFile();
    if (!proj || !file) return false;
    return (redoStack()[`${proj.id}/${file}`]?.length ?? 0) > 0;
  });
  const filteredProjects = computed(() => projects());
  const sectionCounts = computed(() => {
    const counts: Record<string, number> = {};
    projects().forEach(() => { counts['all'] = (counts['all'] || 0) + 1; });
    return counts;
  });
  const columns = computed(() => [projects()]);
  const currentSpec = computed(() => null);
  const parsedContent = computed(() => '');
  const diffHtmlUnified = computed(() => '');
  const parsedAiResult = computed(() => '');
  const isAdditiveOp = computed(() => false);
  const aiOpLabel = computed(() => 'Processing');
  const sectionLabel = computed(() => 'Projects');
  const canGenerateSpecs = computed(() => false);
  const canGenerateEpicGuide = computed(() => false);
  const expandedTitle = computed(() => '');
  const expandedProject = computed(() => '');
  const activeFileType = computed(() => null);
  const isBraindump = computed(() => false);
  const mode = computed(() => statusMode());
  const lastSyncLabel = computed(() => '0s ago');
  const activeStepLabel = computed(() => '');
  const projectsBySection = computed(() => []);

  // ── Spy object ─────────────────────────────────────
  const mock = jasmine.createSpyObj<AppStateService>('AppStateService', [
    'initTheme',
    'destroy',
    'toggleTheme',
    'loadProjects',
    'checkForUpdates',
    'onSearch',
    'selectSection',
    'selectProject',
    'closeExpanded',
    'selectFile',
    'openContext',
    'toggleOp',
    'runOp',
    'runStyle',
    'followupBrainstorm',
    'generateFromBrainstormResult',
    'generateFromBraindump',
    'generateEpicGuide',
    'dismissResult',
    'applyResult',
    'undoVersion',
    'redoVersion',
    'copyResult',
    'openCreateModal',
    'closeCreateModal',
    'createProject',
    'retryLastOp',
    'onCancel',
    'onRetry',
    'logout',
    'shareProject',
    'sectionForProject',
    'teaserFor',
  ]);

  // Attach all signals and computed as properties
  Object.defineProperties(mock, {
    projects:           { get: () => projects,           configurable: true },
    activeSection:      { get: () => activeSection,      configurable: true },
    activeProject:      { get: () => activeProject,      configurable: true },
    activeFile:         { get: () => activeFile,         configurable: true },
    searchQuery:        { get: () => searchQuery,        configurable: true },
    isDark:             { get: () => isDark,             configurable: true },
    updateBanner:       { get: () => updateBanner,       configurable: true },
    knownCount:         { get: () => knownCount,         configurable: true },

    aiLoading:          { get: () => aiLoading,          configurable: true },
    aiResult:           { get: () => aiResult,           configurable: true },
    aiLatencyMs:        { get: () => aiLatencyMs,        configurable: true },
    aiError:            { get: () => aiError,            configurable: true },
    activeOp:           { get: () => activeOp,           configurable: true },
    copied:             { get: () => copied,             configurable: true },

    contextContent:     { get: () => contextContent,     configurable: true },
    contextTitle:       { get: () => contextTitle,       configurable: true },

    showCreateModal:    { get: () => showCreateModal,    configurable: true },
    specGenLoading:     { get: () => specGenLoading,     configurable: true },
    specGenError:       { get: () => specGenError,       configurable: true },
    specGenStep:        { get: () => specGenStep,        configurable: true },
    specGenProjectName: { get: () => specGenProjectName, configurable: true },
    specGenJobId:       { get: () => specGenJobId,       configurable: true },
    specGenFailedStep:  { get: () => specGenFailedStep,  configurable: true },
    cancelling:         { get: () => cancelling,         configurable: true },

    accessDenied:       { get: () => accessDenied,       configurable: true },

    epicGuideLoading:   { get: () => epicGuideLoading,   configurable: true },
    epicGuideError:     { get: () => epicGuideError,     configurable: true },

    shareUrl:           { get: () => shareUrl,           configurable: true },
    shareCopied:        { get: () => shareCopied,        configurable: true },
    shareLoading:       { get: () => shareLoading,       configurable: true },

    polling:            { get: () => polling,            configurable: true },
    pollOk:             { get: () => pollOk,             configurable: true },
    pollingError:       { get: () => pollingError,       configurable: true },
    billingError:       { get: () => billingError,       configurable: true },

    lastSyncAt:         { get: () => lastSyncAt,         configurable: true },
    lastSyncElapsed:    { get: () => lastSyncElapsed,    configurable: true },
    statusMode:         { get: () => statusMode,         configurable: true },
    statusFailureMsg:   { get: () => statusFailureMsg,   configurable: true },

    specGenStartTime:   { get: () => specGenStartTime,   configurable: true },
    specGenElapsed:     { get: () => specGenElapsed,     configurable: true },

    activeOpFile:       { get: () => activeOpFile,       configurable: true },
    fileOpState:        { get: () => fileOpState,        configurable: true },

    pulsingSections:    { get: () => pulsingSections,    configurable: true },

    undoStack:          { get: () => undoStack,          configurable: true },
    redoStack:          { get: () => redoStack,          configurable: true },

    brainstormQuestion: { get: () => brainstormQuestion, configurable: true },

    // Computed
    showGrid:           { get: () => showGrid,           configurable: true },
    showExpanded:       { get: () => showExpanded,       configurable: true },
    canRevert:          { get: () => canRevert,          configurable: true },
    canRedo:            { get: () => canRedo,            configurable: true },
    filteredProjects:   { get: () => filteredProjects,   configurable: true },
    sectionCounts:      { get: () => sectionCounts,      configurable: true },
    columns:            { get: () => columns,            configurable: true },
    currentSpec:        { get: () => currentSpec,        configurable: true },
    parsedContent:      { get: () => parsedContent,      configurable: true },
    diffHtmlUnified:    { get: () => diffHtmlUnified,    configurable: true },
    parsedAiResult:     { get: () => parsedAiResult,     configurable: true },
    isAdditiveOp:       { get: () => isAdditiveOp,       configurable: true },
    aiOpLabel:          { get: () => aiOpLabel,          configurable: true },
    sectionLabel:       { get: () => sectionLabel,       configurable: true },
    canGenerateSpecs:   { get: () => canGenerateSpecs,   configurable: true },
    canGenerateEpicGuide: { get: () => canGenerateEpicGuide, configurable: true },
    expandedTitle:      { get: () => expandedTitle,      configurable: true },
    expandedProject:    { get: () => expandedProject,    configurable: true },
    activeFileType:     { get: () => activeFileType,     configurable: true },
    isBraindump:        { get: () => isBraindump,        configurable: true },
    mode:               { get: () => mode,               configurable: true },
    lastSyncLabel:      { get: () => lastSyncLabel,      configurable: true },
    activeStepLabel:    { get: () => activeStepLabel,    configurable: true },
    projectsBySection:  { get: () => projectsBySection,  configurable: true },

    // navigateToUpgrade callback
    navigateToUpgrade:  { value: () => {}, writable: true, configurable: true },
  });

  // Default spy return values
  mock.loadProjects.and.returnValue(Promise.resolve());
  mock.checkForUpdates.and.returnValue(Promise.resolve());
  mock.selectProject.and.returnValue(Promise.resolve());
  mock.openContext.and.returnValue(Promise.resolve());
  mock.generateFromBrainstormResult.and.returnValue(Promise.resolve());
  mock.generateFromBraindump.and.returnValue(Promise.resolve());
  mock.generateEpicGuide.and.returnValue(Promise.resolve());
  mock.copyResult.and.returnValue(Promise.resolve());
  mock.createProject.and.returnValue(Promise.resolve());
  mock.onCancel.and.returnValue(Promise.resolve());
  mock.onRetry.and.returnValue(Promise.resolve());
  mock.shareProject.and.returnValue(Promise.resolve());
  mock.sectionForProject.and.returnValue('Braindumps' as any);
  mock.teaserFor.and.returnValue('');

  return mock;
}
