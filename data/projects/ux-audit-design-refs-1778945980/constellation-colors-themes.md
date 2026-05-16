---
sidebar_position: 8
---

# 🎨 Theming & Design System

The theme and color management in Constellation is based on **Ionic** and **Angular** with comprehensive theming capabilities for both web and mobile applications.

---

## **Theme Architecture**

### **Frontend Implementation**
Constellation's theming system is implemented in the frontend application using:
- **Ionic Framework**: Native mobile and web theming capabilities
- **Angular**: Component-based theme management
- **CSS Custom Properties**: Dynamic theme variable system
- **State Management**: Centralized theme state with @ngneat/elf

### **Theme Service Architecture**
```typescript
@Injectable({ providedIn: 'root' })
export class ThemeService {
  public readonly theme$ = this.settingsRepository.theme$;
  
  public setTheme(theme: Theme): void {
    this.settingsRepository.setTheme(theme);
    // Apply theme to Ionic components and status bar
  }
}
```

---

## **Theme Modes**

### **Available Themes**
```typescript
export enum Theme {
  System = 'system',    // Follows system preference
  Light = 'light',      // Light theme
  Dark = 'dark'         // Dark theme
}
```

### **System Theme Detection**
- **Automatic Detection**: Automatically detects system theme preference
- **Dynamic Switching**: Responds to system theme changes in real-time
- **User Override**: Users can override system preference with manual selection
- **Persistence**: Theme choice is remembered across sessions

---

## **Theme Implementation**

### **CSS Custom Properties**
```scss
// Theme variables in variables.scss
:root {
  --ion-color-primary: #3880ff;
  --ion-color-primary-rgb: 56, 128, 255;
  --ion-color-primary-contrast: #ffffff;
  --ion-color-primary-contrast-rgb: 255, 255, 255;
  --ion-color-primary-shade: #3171e0;
  --ion-color-primary-tint: #4c8dff;
}

// Dark theme overrides
@media (prefers-color-scheme: dark) {
  :root {
    --ion-color-primary: #428cff;
    --ion-color-primary-rgb: 66, 140, 255;
    --ion-color-primary-contrast: #ffffff;
    --ion-color-primary-contrast-rgb: 255, 255, 255;
    --ion-color-primary-shade: #3a7be0;
    --ion-color-primary-tint: #5598ff;
  }
}
```

### **Ionic Theme Integration**
```typescript
public setTheme(theme: Theme): void {
  switch (theme) {
    case Theme.Light: {
      // Apply light theme
      void this.statusBarService.setStyle({ style: Style.Light });
      void this.capacitorEdgeToEdgeService.setBackgroundColor({
        color: '#ffffff',
      });
      document.documentElement.classList.remove('ion-palette-dark');
      break;
    }
    case Theme.Dark: {
      // Apply dark theme
      void this.statusBarService.setStyle({ style: Style.Dark });
      void this.capacitorEdgeToEdgeService.setBackgroundColor({
        color: '#000000',
      });
      document.documentElement.classList.add('ion-palette-dark');
      break;
    }
    default: {
      // Follow system preference
      const hasDarkPreference = this.getMediaPreference().matches;
      // Apply appropriate theme based on system preference
    }
  }
}
```

---

## **Color System**

### **Primary Color Palette**
- **Primary**: Main brand color used for buttons, links, and highlights
- **Secondary**: Supporting color for secondary actions
- **Tertiary**: Additional accent color for special elements
- **Success**: Green color for positive actions and confirmations
- **Warning**: Yellow/Orange color for warnings and cautions
- **Danger**: Red color for errors and destructive actions

### **Semantic Colors**
```scss
// Success colors
--ion-color-success: #2dd36f;
--ion-color-success-rgb: 45, 211, 111;
--ion-color-success-contrast: #000000;
--ion-color-success-contrast-rgb: 0, 0, 0;
--ion-color-success-shade: #28ba62;
--ion-color-success-tint: #42d77d;

// Warning colors
--ion-color-warning: #ffc409;
--ion-color-warning-rgb: 255, 196, 9;
--ion-color-warning-contrast: #000000;
--ion-color-warning-contrast-rgb: 0, 0, 0;
--ion-color-warning-shade: #e0ac08;
--ion-color-warning-tint: #ffca22;

// Danger colors
--ion-color-danger: #eb445a;
--ion-color-danger-rgb: 235, 68, 90;
--ion-color-danger-contrast: #ffffff;
--ion-color-danger-contrast-rgb: 255, 255, 255;
--ion-color-danger-shade: #cf3c4f;
--ion-color-danger-tint: #ed576b;
```

---

## **Component Theming**

### **Ionic Components**
- **Buttons**: Automatically themed based on color system
- **Cards**: Background and text colors adapt to theme
- **Lists**: Item backgrounds and borders follow theme
- **Forms**: Input fields and labels use theme colors
- **Navigation**: Toolbars and navigation elements adapt

### **Custom Components**
```typescript
@Component({
  selector: 'app-custom-component',
  template: `
    <ion-card [class.dark-theme]="isDarkTheme">
      <ion-card-header>
        <ion-card-title>{{ title }}</ion-card-title>
      </ion-card-header>
      <ion-card-content>
        {{ content }}
      </ion-card-content>
    </ion-card>
  `,
  styleUrls: ['./custom-component.component.scss']
})
export class CustomComponent {
  public readonly isDarkTheme = this.themeService.theme$.pipe(
    map(theme => theme === Theme.Dark)
  );
}
```

---

## **State Management**

### **Theme Repository**
```typescript
@Injectable({ providedIn: 'root' })
export class SettingsRepository {
  public theme$ = store.pipe(select(state => state.theme));
  
  public setTheme(theme: Theme): void {
    store.update(state => ({
      ...state,
      theme,
    }));
  }
}
```

### **Persistence**
- **Local Storage**: Theme preference stored in browser local storage
- **Cross-Session**: Theme choice persists across browser sessions
- **Device Sync**: Theme preference synchronized across devices (if configured)
- **Backup/Restore**: Theme settings included in user preferences backup

---

## **Mobile-Specific Features**

### **Status Bar Theming**
```typescript
// Status bar adapts to theme
public setTheme(theme: Theme): void {
  if (hasDarkPreference) {
    void this.statusBarService.setStyle({ style: Style.Dark });
  } else {
    void this.statusBarService.setStyle({ style: Style.Light });
  }
}
```

### **Edge-to-Edge Support**
```typescript
// Background color adapts to theme
void this.capacitorEdgeToEdgeService.setBackgroundColor({
  color: hasDarkPreference ? '#000000' : '#ffffff',
});
```

### **Platform-Specific Theming**
- **iOS**: Follows iOS design guidelines and theme system
- **Android**: Follows Material Design theme principles
- **Web**: Responsive web design with theme-aware styling

---

## **Theme Switching**

### **User Interface**
```typescript
// Theme toggle component
@Component({
  selector: 'app-theme-toggle',
  template: `
    <ion-item>
      <ion-label>Theme</ion-label>
      <ion-select [(ngModel)]="selectedTheme" (ionChange)="onThemeChange()">
        <ion-select-option [value]="Theme.System">System</ion-select-option>
        <ion-select-option [value]="Theme.Light">Light</ion-select-option>
        <ion-select-option [value]="Theme.Dark">Dark</ion-select-option>
      </ion-select>
    </ion-item>
  `
})
export class ThemeToggleComponent {
  public selectedTheme = this.themeService.getTheme();
  
  public onThemeChange(): void {
    this.themeService.setTheme(this.selectedTheme);
  }
}
```

### **Automatic Switching**
- **System Preference**: Automatically follows system theme changes
- **Time-based**: Optional time-based theme switching
- **Location-based**: Future support for location-based themes
- **Accessibility**: High contrast mode support

---

## **Customization**

### **Adding New Colors**
```scss
// Define new color in variables.scss
:root {
  --ion-color-custom: #9c27b0;
  --ion-color-custom-rgb: 156, 39, 176;
  --ion-color-custom-contrast: #ffffff;
  --ion-color-custom-contrast-rgb: 255, 255, 255;
  --ion-color-custom-shade: #8a229a;
  --ion-color-custom-tint: #a73db8;
}

// Use in components
.custom-element {
  background-color: var(--ion-color-custom);
  color: var(--ion-color-custom-contrast);
}
```

### **Theme Variants**
- **Brand Themes**: Different color schemes for different brands
- **Seasonal Themes**: Time-limited theme variations
- **Event Themes**: Special themes for events or promotions
- **User Themes**: User-customizable theme elements

---

## **Performance Considerations**

### **Theme Switching Performance**
- **CSS Variables**: Fast theme switching using CSS custom properties
- **Minimal Re-renders**: Efficient theme application without component re-rendering
- **Lazy Loading**: Theme-specific assets loaded on demand
- **Caching**: Theme configurations cached for faster switching

### **Bundle Optimization**
- **Tree Shaking**: Unused theme code removed from production builds
- **Code Splitting**: Theme-specific code split into separate chunks
- **Minification**: CSS and JavaScript optimized for production

---

## **Accessibility**

### **Color Contrast**
- **WCAG Compliance**: Meets WCAG 2.1 AA contrast requirements
- **High Contrast Mode**: Support for high contrast themes
- **Color Blind Support**: Color combinations accessible to color blind users
- **Focus Indicators**: Clear focus indicators for keyboard navigation

### **Theme Preferences**
- **System Integration**: Respects system accessibility settings
- **User Override**: Users can override system accessibility preferences
- **Accessibility Tools**: Integration with screen readers and assistive technologies

---

## **Future Enhancements**

### **Planned Features**
- **Advanced Color Palettes**: Extended color system with more options
- **Animation Themes**: Theme-aware animations and transitions
- **Custom Theme Builder**: Visual theme creation tool
- **Theme Marketplace**: Community-created theme sharing

### **Integration Expansion**
- **Design System**: Integration with design system tools
- **Theme Templates**: Pre-built theme templates for common use cases
- **Advanced Customization**: More granular theme customization options
- **Theme Analytics**: Usage analytics for theme preferences
