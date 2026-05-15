import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-landing-pitch',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './landing-pitch.component.html',
  styleUrl: './landing-pitch.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LandingPitchComponent {}
