import { Component, ChangeDetectionStrategy, OnInit, ElementRef, inject } from '@angular/core';

@Component({
  selector: 'app-design-playground',
  standalone: true,
  template: '<div class="playground-host"></div>',
  styles: [':host { display: block; }'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DesignPlaygroundComponent implements OnInit {
  private el = inject(ElementRef);

  ngOnInit(): void {
    // Load the static playground HTML via fetch to avoid Angular template parsing
    // (the playground has { } in code samples that conflict with Angular interpolation)
    fetch('/assets/playground.html')
      .then(r => r.text())
      .then(html => {
        // Extract body content and styles
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const style = doc.querySelector('style');
        const body = doc.body;

        const host: HTMLElement = this.el.nativeElement.querySelector('.playground-host');
        if (style) {
          host.appendChild(style.cloneNode(true));
        }
        if (body) {
          host.innerHTML += body.innerHTML;
        }
      });
  }
}
