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
}
