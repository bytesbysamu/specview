import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { TopBarComponent } from './components/top-bar/top-bar.component';

@Component({
  selector: 'app-v2-root',
  standalone: true,
  imports: [RouterOutlet, TopBarComponent],
  template: `
    <app-top-bar />
    <router-outlet />
  `,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
  `],
})
export class AppV2Component {}
