import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export class AccessDeniedError extends Error {
  readonly status = 403;
  readonly type = 'access_denied';
  constructor() {
    super('You do not have access to this project.');
    this.name = 'AccessDeniedError';
  }
}

export interface Spec {
  filename: string;
  label: string;
  content?: string;
  teaser?: string;
}

export interface Project {
  id: string;
  name: string;
  createdAt: string;
  specs: Spec[];
}

export interface GeneratedFile {
  filename: string;
  content: string;
}

export interface PollStatusResponse {
  running: boolean;
  done: boolean;
  current_step: string | null;
  partial_files?: GeneratedFile[];
  files?: GeneratedFile[];
  error?: string;
}

export interface PollResultResponse {
  running: boolean;
  done: boolean;
  filename?: string;
  error?: string;
}

const CANONICAL_ORDER = [
  'braindump',
  'analysis',
  'epic',
  'architecture',
  'timeline',
  'implementation-guide',
];

function sortSpecs(specs: Spec[]): Spec[] {
  return [...specs].sort((a, b) => {
    const nameA = a.filename.replace(/\.md$/i, '');
    const nameB = b.filename.replace(/\.md$/i, '');
    const idxA = CANONICAL_ORDER.indexOf(nameA);
    const idxB = CANONICAL_ORDER.indexOf(nameB);
    const rankA = idxA === -1 ? CANONICAL_ORDER.length : idxA;
    const rankB = idxB === -1 ? CANONICAL_ORDER.length : idxB;
    if (rankA !== rankB) return rankA - rankB;
    // Both unknown — sort alphabetically by filename
    return a.filename.localeCompare(b.filename);
  });
}

@Injectable({ providedIn: 'root' })
export class ProjectsService {
  constructor(private http: HttpClient) {}

  listProjects(): Promise<Project[]> {
    return firstValueFrom(this.http.get<Project[]>('/api/projects')).then(
      projects => projects.map(p => ({ ...p, specs: sortSpecs(p.specs) }))
    );
  }

  getProject(id: string): Promise<Project> {
    return firstValueFrom(this.http.get<Project>(`/api/projects/${id}`)).then(
      p => ({ ...p, specs: sortSpecs(p.specs) })
    ).catch((err: HttpErrorResponse) => {
      if (err?.status === 403) throw new AccessDeniedError();
      throw err;
    });
  }

  getContext(key: string): Promise<{ content: string; text?: string }> {
    return firstValueFrom(this.http.get<{ content: string; text?: string }>(`/api/context/${key}`));
  }

  startBootstrap(projectName: string, braindump: string): Promise<{ job_id: string }> {
    return firstValueFrom(
      this.http.post<{ job_id: string }>('/api/ai/text/bootstrap-project', {
        project_name: projectName,
        braindump,
      })
    );
  }

  pollBootstrap(jobId: string): Promise<PollStatusResponse> {
    return firstValueFrom(
      this.http.get<PollStatusResponse>(`/api/ai/text/bootstrap-project/status/${jobId}`)
    );
  }

  createProject(name: string, files: GeneratedFile[]): Promise<Project> {
    return firstValueFrom(
      this.http.post<Project>('/api/projects', { name, files })
    );
  }

  saveFile(projectId: string, filename: string, content: string): Promise<void> {
    return firstValueFrom(
      this.http.put<void>(`/api/projects/${projectId}/files/${filename}`, { content })
    );
  }

  startEpicGuide(projectId: string): Promise<{ started: boolean; alreadyRunning?: boolean }> {
    return firstValueFrom(
      this.http.post<{ started: boolean; alreadyRunning?: boolean }>(
        `/api/projects/${projectId}/generate-epic-guide`, {}
      )
    );
  }

  pollEpicGuide(projectId: string): Promise<PollResultResponse> {
    return firstValueFrom(
      this.http.get<PollResultResponse>(`/api/projects/${projectId}/generate-epic-guide/status`)
    );
  }
}
