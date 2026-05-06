import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

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

@Injectable({ providedIn: 'root' })
export class ProjectsService {
  constructor(private http: HttpClient) {}

  listProjects(): Promise<Project[]> {
    return firstValueFrom(this.http.get<Project[]>('/api/projects'));
  }

  getProject(id: string): Promise<Project> {
    return firstValueFrom(this.http.get<Project>(`/api/projects/${id}`));
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

  pollBootstrap(jobId: string): Promise<{
    running: boolean;
    done: boolean;
    current_step: string | null;
    partial_files?: GeneratedFile[];
    files?: GeneratedFile[];
    error?: string;
  }> {
    return firstValueFrom(
      this.http.get<any>(`/api/ai/text/bootstrap-project/status/${jobId}`)
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

  pollEpicGuide(projectId: string): Promise<{ running: boolean; done: boolean; filename?: string; error?: string }> {
    return firstValueFrom(
      this.http.get<any>(`/api/projects/${projectId}/generate-epic-guide/status`)
    );
  }
}
