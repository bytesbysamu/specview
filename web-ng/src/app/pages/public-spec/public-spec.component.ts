import { Component, Input, OnInit, signal, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { firstValueFrom } from 'rxjs';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { LandingCtaBarComponent } from './landing-cta-bar.component';
import { SpecviewBadgeComponent } from './specview-badge.component';

interface PublicDoc {
  filename: string;
  label: string;
  content: string;
}

interface PublicSpecResponse {
  name: string;
  id: string;
  docs: PublicDoc[];
}

/** Canonical doc ordering mirrors the main app's CANONICAL_ORDER. */
const CANONICAL_ORDER = [
  'braindump',
  'analysis',
  'epic',
  'architecture',
  'timeline',
  'implementation-guide',
];

function sortDocs(docs: PublicDoc[]): PublicDoc[] {
  return [...docs].sort((a, b) => {
    const nameA = a.filename.replace(/\.md$/i, '');
    const nameB = b.filename.replace(/\.md$/i, '');
    const idxA = CANONICAL_ORDER.indexOf(nameA);
    const idxB = CANONICAL_ORDER.indexOf(nameB);
    const rankA = idxA === -1 ? CANONICAL_ORDER.length : idxA;
    const rankB = idxB === -1 ? CANONICAL_ORDER.length : idxB;
    if (rankA !== rankB) return rankA - rankB;
    return a.filename.localeCompare(b.filename);
  });
}

@Component({
  selector: 'app-public-spec',
  standalone: true,
  imports: [LandingCtaBarComponent, SpecviewBadgeComponent],
  templateUrl: './public-spec.component.html',
  styleUrl: './public-spec.component.css',
})
export class PublicSpecComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);
  private sanitizer = inject(DomSanitizer);

  @Input() isLanding = false;

  project = signal<PublicSpecResponse | null>(null);
  activeDoc = signal<string | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  isLandingMode = signal(false);

  parsedContent = signal<SafeHtml>('');

  ngOnInit(): void {
    // Route data takes precedence (landing page route injects slug + isLanding)
    const routeData = this.route.snapshot.data;
    const dataSlug: string | undefined = routeData['slug'];
    const dataIsLanding: boolean | undefined = routeData['isLanding'];

    if (dataIsLanding || this.isLanding) {
      this.isLandingMode.set(true);
    }

    const slug = dataSlug ?? this.route.snapshot.paramMap.get('slug');
    if (!slug) {
      this.error.set('Invalid share link.');
      this.loading.set(false);
      return;
    }
    this.loadProject(slug);
  }

  private async loadProject(slug: string): Promise<void> {
    try {
      const data = await firstValueFrom(
        this.http.get<PublicSpecResponse>(`/api/public/share/${slug}`)
      );
      const sorted = { ...data, docs: sortDocs(data.docs) };
      this.project.set(sorted);

      // Prefer analysis.md; fall back to first doc
      const preferred = sorted.docs.find(d => d.filename === 'analysis.md') ?? sorted.docs[0];
      if (preferred) {
        this.activeDoc.set(preferred.filename);
        this.renderDoc(preferred.content);
      }
    } catch (err: any) {
      if (err?.status === 404) {
        this.error.set('This share link does not exist or has been removed.');
      } else {
        this.error.set('Could not load the shared spec. Please try again later.');
      }
    } finally {
      this.loading.set(false);
    }
  }

  selectDoc(filename: string): void {
    const proj = this.project();
    if (!proj) return;
    const doc = proj.docs.find(d => d.filename === filename);
    if (!doc) return;
    this.activeDoc.set(filename);
    this.renderDoc(doc.content);
  }

  private renderDoc(content: string): void {
    const html = DOMPurify.sanitize(marked.parse(content) as string);
    this.parsedContent.set(this.sanitizer.bypassSecurityTrustHtml(html));
  }
}
