import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AppStateService } from './services/app-state.service';
import { AuthService } from './services/auth.service';
import { SubscriptionService } from './services/subscription.service';

import { SectionNavComponent } from './section-nav.component';
import { StatusBarComponent } from './status-bar.component';
import { ProjectGridComponent } from './project-grid.component';
import { SidebarV2Component } from './sidebar-v2.component';
import { ReaderPanelComponent } from './reader-panel.component';
import { LandingPitchComponent } from './landing-pitch.component';
import { UsageMeterComponent } from './components/usage-meter/usage-meter.component';

@Component({
  selector: 'app-v3-root',
  standalone: true,
  imports: [
    SectionNavComponent,
    StatusBarComponent,
    ProjectGridComponent,
    SidebarV2Component,
    ReaderPanelComponent,
    LandingPitchComponent,
    UsageMeterComponent,
  ],
  templateUrl: './app-v3.component.html',
  styleUrl: './app-v2.component.css',
})
export class AppV3Component implements OnInit, OnDestroy {
  state = inject(AppStateService);
  auth = inject(AuthService);
  subscription = inject(SubscriptionService);
  private router = inject(Router);

  ngOnInit() {
    this.state.navigateToUpgrade = () => this.router.navigate(['/upgrade']);
    this.state.initTheme();
  }

  ngOnDestroy() {
    this.state.destroy();
  }
}
