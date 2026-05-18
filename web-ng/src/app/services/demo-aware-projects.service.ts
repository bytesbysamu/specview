import { Injectable, computed, inject, signal } from '@angular/core';
import { AuthService } from './auth.service';
import { Project, Spec, ProjectsService } from './projects.service';
import { DEMO_FIXTURE_PROJECTS } from './demo-fixtures';

/**
 * Auth-aware data abstraction that makes demo mode invisible to consuming
 * components.
 *
 * When the user is unauthenticated, all methods return data from the static
 * demo fixtures without making any HTTP calls.  When the user is
 * authenticated, all methods delegate to the real `ProjectsService`.
 *
 * Auth-state transitions are signal-reactive: no imperative switch-mode call,
 * no event bus, and no page reload is required.  Consuming components that
 * read the `loading` signal can suppress the visual flash that would otherwise
 * appear when mock data is replaced by real API data immediately after login.
 */
@Injectable({ providedIn: 'root' })
export class DemoAwareProjectsService {
  private readonly auth = inject(AuthService);
  private readonly projects = inject(ProjectsService);

  /**
   * Reactive auth flag derived from `AuthService.isLoggedIn`.
   * Used internally to fork between demo fixtures and real HTTP calls.
   */
  private readonly isAuthenticated = computed(() => this.auth.isLoggedIn());

  /**
   * True while the first real API call is in-flight after the user logs in.
   * Consuming components can bind to this to hide the fixture-to-real-data
   * transition.
   */
  readonly loading = signal(false);

  // ── Public API ───────────────────────────────────────────────────────────

  /**
   * Return the list of projects.
   * Unauthenticated: returns demo fixture projects immediately.
   * Authenticated: delegates to `ProjectsService.listProjects()`.
   */
  async getProjects(): Promise<Project[]> {
    if (!this.isAuthenticated()) {
      return Promise.resolve([...DEMO_FIXTURE_PROJECTS]);
    }
    this.loading.set(true);
    try {
      return await this.projects.listProjects();
    } finally {
      this.loading.set(false);
    }
  }

  /**
   * Return a single project by ID.
   * Unauthenticated: looks up the ID in demo fixture projects.
   * Authenticated: delegates to `ProjectsService.getProject(id)`.
   */
  async getProject(id: string): Promise<Project> {
    if (!this.isAuthenticated()) {
      const found = DEMO_FIXTURE_PROJECTS.find(p => p.id === id);
      if (found) return Promise.resolve({ ...found, specs: [...found.specs] });
      return Promise.reject(new Error(`Demo project not found: ${id}`));
    }
    this.loading.set(true);
    try {
      return await this.projects.getProject(id);
    } finally {
      this.loading.set(false);
    }
  }

  /**
   * Return a single spec (by section/filename) for a project.
   * Unauthenticated: looks up the spec in demo fixture data.
   * Authenticated: fetches the project via `ProjectsService` and returns the
   * matching spec, or rejects if the spec is not found.
   *
   * @param id       Project ID.
   * @param section  Spec filename (e.g. `"analysis.md"`).
   */
  async getSpec(id: string, section: string): Promise<Spec> {
    const project = await this.getProject(id);
    const spec = project.specs.find(s => s.filename === section);
    if (!spec) {
      return Promise.reject(new Error(`Spec "${section}" not found in project "${id}"`));
    }
    return spec;
  }
}
