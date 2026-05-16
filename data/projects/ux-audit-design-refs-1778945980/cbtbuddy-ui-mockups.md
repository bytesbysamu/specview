# CBT Buddy - Professional UI Mockups & Design Specifications

## 🎯 **Design Philosophy: Maximum AI + Minimal Code**

### **Core Principles**
- **AI-First**: Background intelligence, instant fallbacks
- **Professional**: Clean, modern, consistent design language
- **Minimalistic**: Few features, perfect execution
- **Mood Calendar**: Essential tracking feature
- **Less Code**: Fewer files, fewer features, better performance

---

## 🎨 **Design System Specifications**

### **Color Palette**
- **Primary Blue**: `#4A90E2` (Trust, calm, stability)
- **Success Green**: `#7ED321` (Progress, growth, positivity)
- **Warm Orange**: `#F5A623` (Energy, motivation, warmth)
- **Background Gray**: `#F8F9FA` (Clean, focused, calm)
- **Text Dark**: `#2C3E50` (Readable, professional)
- **Border Light**: `#E1E8ED` (Subtle separation)

### **Typography**
- **Font Family**: Inter (iOS: SF Pro, Android: Roboto fallback)
- **Headings**: 600 weight, 24pt (main), 20pt (secondary)
- **Body**: 400 weight, 16pt (standard), 14pt (captions)
- **Buttons**: 600 weight, 16pt
- **Line Height**: 1.5 for readability

### **Spacing System**
- **Base Unit**: 8px
- **Small**: 8px, 16px
- **Medium**: 24px, 32px
- **Large**: 40px, 48px
- **Margins**: 16px between sections, 24px between major elements

### **Component Specifications**
- **Border Radius**: 16px (cards), 12px (buttons), 24px (mood circles)
- **Shadows**: `0 4px 16px rgba(0, 0, 0, 0.1)` (subtle elevation)
- **Transitions**: 200ms ease-out for all interactions

---

## 📱 **Screen 1: Home Tab - Main Dashboard**

### **Layout Structure**
```
┌─────────────────────────────────────────┐
│ Status Bar (iOS/Android)               │
├─────────────────────────────────────────┤
│ Header: CBT Buddy + Streak Badge       │
├─────────────────────────────────────────┤
│                                         │
│ 🎯 Start Today's Exercise              │
│ [Large Primary Button - Full Width]    │
│                                         │
│ Smart Status Card                       │
│ ✨ Personalized for you                 │
│ 🧠 Based on work stress patterns       │
│ ⚡ Ready instantly                      │
│                                         │
│ Quick Mood Check                        │
│ [😊😐😔😤😭]                        │
│                                         │
│ Progress Overview Card                  │
│ 📊 4/7 days completed                  │
│ 📈 Mood trend: ↗️ +2                   │
│ 🎯 Streak: 5 days                      │
│                                         │
│ Recent Activity Card                    │
│ • Thought Reframing (2h ago)           │
│ • Goal Setting (1d ago)                │
│ • Sleep Loop Breaker (2d ago)          │
├─────────────────────────────────────────┤
│ Tab Bar: Home | Journal | Insights     │
└─────────────────────────────────────────┘
```

### **Visual Design Details**

#### **Header Section**
- **App Title**: "CBT Buddy" in 24pt Inter, 600 weight, `#2C3E50`
- **Streak Badge**: 🔥 "5 Days" in 16pt Inter, 500 weight, `#F5A623`
- **Background**: Clean white with subtle shadow separation

#### **Primary CTA Button**
- **Background**: `#4A90E2` with gradient overlay
- **Text**: "Start Today's Exercise" in 18pt Inter, 600 weight, white
- **Size**: Full width, 56px height, 16px margins
- **Shadow**: `0 4px 16px rgba(74, 144, 226, 0.3)`
- **Hover State**: Slight scale (1.02) and shadow increase

#### **Smart Status Card**
- **Background**: White with `#F8F9FA` border
- **Icon**: ✨ Sparkle emoji, 20pt
- **Text**: "Personalized for you" in 16pt Inter, 500 weight
- **Subtext**: "Based on work stress patterns" in 14pt Inter, 400 weight
- **Status**: "Ready instantly" with ⚡ icon, `#7ED321` color

#### **Quick Mood Check**
- **Mood Icons**: 5 emojis in 32pt size
- **Layout**: Horizontal row with 12px spacing
- **Selection**: Active state with `#4A90E2` background and white text
- **Inactive**: Light gray border (`#E1E8ED`)

#### **Progress Overview Card**
- **Background**: White with subtle shadow
- **Metrics**: 3-column layout with icons and values
- **Icons**: 📊📈🎯 in 20pt size
- **Values**: 16pt Inter, 600 weight, `#2C3E50`
- **Trend Arrow**: ↗️ in `#7ED321` color

#### **Recent Activity Card**
- **Background**: White with `#F8F9FA` border
- **Items**: List with bullet points and timestamps
- **Text**: 14pt Inter, 400 weight, `#2C3E50`
- **Timestamps**: 12pt Inter, 400 weight, `#7A8C9A`

---

## 📓 **Screen 2: Journal Tab - Create + Timeline**

### **Layout Structure**
```
┌─────────────────────────────────────────┐
│ Status Bar (iOS/Android)               │
├─────────────────────────────────────────┤
│ Header: Journal + Quick Actions        │
├─────────────────────────────────────────┤
│                                         │
│ New Entry Card (Fixed at Top)          │
│ ✨ New Entry                           │
│ How are you feeling? [Mood Scale]      │
│ What's on your mind? [Text Input]      │
│ [Save Entry Button]                    │
│                                         │
│ Timeline Section                        │
│ Today (Date Header)                    │
│ • Journal Entry Card                   │
│ • Exercise Completed Card              │
│                                         │
│ Yesterday (Date Header)                │
│ • Journal Entry Card                   │
│                                         │
│ Earlier This Week (Date Header)        │
│ • Multiple Entry Cards                 │
├─────────────────────────────────────────┤
│ Tab Bar: Home | Journal | Insights     │
└─────────────────────────────────────────┘
```

### **Visual Design Details**

#### **New Entry Card (Fixed)**
- **Background**: White with `#4A90E2` accent border (top)
- **Header**: ✨ "New Entry" in 18pt Inter, 600 weight, `#4A90E2`
- **Mood Question**: "How are you feeling?" in 16pt Inter, 500 weight
- **Mood Scale**: 5 emojis in 40pt size with selection states
- **Text Input**: "What's on your mind?" with expandable textarea
- **Save Button**: `#4A90E2` background, white text, 16pt Inter, 600 weight

#### **Timeline Section**
- **Date Headers**: 14pt Inter, 600 weight, `#7A8C9A`, 16px margins
- **Entry Cards**: White background, subtle shadows, 16px margins
- **Journal Entries**: Mood emoji + timestamp + text snippet
- **Exercise Entries**: 🧠 icon + exercise type + context
- **Timestamps**: 12pt Inter, 400 weight, `#7A8C9A`

#### **Card Interactions**
- **Hover State**: Slight elevation increase
- **Tap State**: Scale down (0.98) with haptic feedback
- **Selection**: Subtle `#4A90E2` border highlight

---

## 📊 **Screen 3: Insights Tab - Stats + Patterns**

### **Layout Structure**
```
┌─────────────────────────────────────────┐
│ Status Bar (iOS/Android)               │
├─────────────────────────────────────────┤
│ Header: Insights & Progress            │
├─────────────────────────────────────────┤
│                                         │
│ Weekly Mood Chart Card                 │
│ 📈 Weekly Mood Chart                   │
│ [Line Chart: 7 days, smooth curve]     │
│ 🔥 Streak: 5 days | 🎯 80%            │
│                                         │
│ Quick Input Card                       │
│ 📝 Quick Input                         │
│ Mood: [😊😐😔😤😭]                    │
│ Note: [Quick text input]               │
│ [Save Button]                          │
│                                         │
│ Pattern Recognition Card                │
│ 🎯 This Week's Patterns                │
│ • Catastrophizing (3×)                 │
│ • All-or-nothing thinking (2×)         │
│ • Mind reading (1×)                    │
│ 💬 Encouragement message                │
│                                         │
│ Mood Calendar Card (Monthly View)      │
│ 📅 August 2024                         │
│ [Calendar Grid with Mood Colors]       │
│ Legend: 😊😐😔😤😭                    │
├─────────────────────────────────────────┤
│ Tab Bar: Home | Journal | Insights     │
└─────────────────────────────────────────┘
```

### **Visual Design Details**

#### **Weekly Mood Chart Card**
- **Background**: White with subtle shadow
- **Header**: 📈 "Weekly Mood Chart" in 18pt Inter, 600 weight
- **Chart**: Line chart with smooth curves, `#4A90E2` primary color
- **Metrics Row**: Streak and completion % in horizontal layout
- **Streak Icon**: 🔥 in `#F5A623` color
- **Completion**: 🎯 with percentage in `#7ED321` color

#### **Quick Input Card**
- **Background**: White with `#F8F9FA` border
- **Header**: 📝 "Quick Input" in 16pt Inter, 600 weight
- **Mood Scale**: 5 emojis in 32pt size
- **Text Input**: Single line input with placeholder
- **Save Button**: `#4A90E2` background, compact size

#### **Pattern Recognition Card**
- **Background**: White with `#F8F9FA` border
- **Header**: 🎯 "This Week's Patterns" in 16pt Inter, 600 weight
- **Pattern List**: Bullet points with counts in parentheses
- **Text**: 14pt Inter, 400 weight, `#2C3E50`
- **Encouragement**: 💬 icon with motivational message in `#7ED321`

#### **Mood Calendar Card (Essential Feature)**
- **Background**: White with subtle shadow
- **Header**: 📅 "August 2024" in 16pt Inter, 600 weight
- **Calendar Grid**: 7x5 grid with mood color coding
- **Mood Colors**: 
  - 😊 Happy: `#7ED321` (light green)
  - 😐 Neutral: `#E1E8ED` (light gray)
  - 😔 Sad: `#4A90E2` (blue)
  - 😤 Stressed: `#F5A623` (orange)
  - 😭 Very Low: `#E74C3C` (red)
- **Legend**: 5 mood emojis with color indicators below calendar

---

## 🔄 **Screen 4: Exercise Session Flow (5 Questions)**

### **Layout Structure**
```
┌─────────────────────────────────────────┐
│ Status Bar (iOS/Android)               │
├─────────────────────────────────────────┤
│ Header: Exercise Type + Progress Bar   │
├─────────────────────────────────────────┤
│                                         │
│ Progress Indicator                      │
│ [Progress Bar: 2/5]                    │
│                                         │
│ Question Card                           │
│ Question 2                              │
│                                         │
│ How strong did this thought feel?       │
│ (0-10 scale)                           │
│                                         │
│ [0] [1] [2] [3] [4]                    │
│ [5] [6] [7] [8] [9]                    │
│ [10]                                    │
│                                         │
│ Navigation                              │
│ [← Back]                    [Next →]   │
│                                         │
│ Status: Auto-saved ✓                    │
├─────────────────────────────────────────┤
│ No Tab Bar (Full Screen Exercise)      │
└─────────────────────────────────────────┘
```

### **Visual Design Details**

#### **Header Section**
- **Exercise Type**: "Thought Reframing" in 20pt Inter, 600 weight
- **Progress Bar**: Horizontal bar with 5 segments, current segment highlighted
- **Progress Text**: "2/5" in 14pt Inter, 500 weight, `#7A8C9A`

#### **Question Card**
- **Background**: White with subtle shadow
- **Question Number**: "Question 2" in 16pt Inter, 500 weight, `#7A8C9A`
- **Question Text**: "How strong did this thought feel?" in 18pt Inter, 600 weight
- **Subtext**: "(0-10 scale)" in 14pt Inter, 400 weight, `#7A8C9A`

#### **Scale Input**
- **Scale Values**: 0-10 in circular buttons
- **Button Size**: 48px diameter with 12px spacing
- **Default State**: Light gray border (`#E1E8ED`)
- **Selected State**: `#4A90E2` background with white text
- **Hover State**: Slight scale increase (1.05)

#### **Navigation**
- **Back Button**: Outlined style, `#7A8C9A` border and text
- **Next Button**: Filled style, `#4A90E2` background
- **Button Size**: 44px height, 80px width
- **Status Text**: "Auto-saved ✓" in 12pt Inter, 400 weight, `#7ED321`

---

## 🎨 **Design Consistency Rules**

### **Card Design**
- **Background**: Always white (`#FFFFFF`)
- **Border**: Subtle `#E1E8ED` or `#F8F9FA` borders
- **Shadow**: `0 4px 16px rgba(0, 0, 0, 0.1)` for elevation
- **Radius**: 16px for all cards
- **Padding**: 24px internal spacing

### **Button Hierarchy**
- **Primary**: `#4A90E2` background, white text, 600 weight
- **Secondary**: White background, `#4A90E2` border and text
- **Tertiary**: `#7A8C9A` text, no background, minimal styling

### **Icon Usage**
- **Emojis**: For mood and quick visual communication
- **System Icons**: For navigation and actions (SF Symbols/iOS, Material/Android)
- **Custom Icons**: Minimal, consistent with design language

### **Spacing Consistency**
- **Section Margins**: 24px between major sections
- **Card Margins**: 16px between cards
- **Internal Padding**: 24px within cards
- **Element Spacing**: 16px between related elements

---

## 🚀 **Implementation Notes**

### **AI Integration Points**
- **Background Fetch**: Always running, never blocking UI
- **Fallback Logging**: Clear console logs when local templates used
- **Performance**: Optimize later, focus on functionality first

### **Code Organization**
- **Fewer Files**: Consolidate components where possible
- **Shared Styles**: Use CSS variables for consistent theming
- **Component Reuse**: Maximize component sharing between screens

### **Accessibility**
- **Touch Targets**: Minimum 44px for all interactive elements
- **Color Contrast**: WCAG AA compliant color combinations
- **Text Size**: Minimum 14pt for all text content
- **Focus States**: Clear focus indicators for keyboard navigation

---

## 📱 **Device Specifications**

### **iOS (iPhone)**
- **Safe Areas**: Respect notch and home indicator
- **Haptic Feedback**: Use system haptics for interactions
- **System Fonts**: SF Pro Display, SF Pro Text
- **Gestures**: Support native iOS gestures

### **Android**
- **Material Design**: Follow Material Design 3 principles
- **System Fonts**: Roboto with Inter fallback
- **Back Navigation**: Support Android back button
- **Adaptive Icons**: Use adaptive icon system

### **Responsive Design**
- **Breakpoints**: Mobile-first design (320px+)
- **Flexible Layouts**: Use flexbox and grid for adaptability
- **Touch Optimization**: Optimize for thumb navigation
- **Performance**: 60fps animations, smooth scrolling

---

## 🎯 **Next Steps**

### **Design Phase**
1. **Create High-Fidelity Mockups** using Figma/Sketch
2. **Design System Library** with all components
3. **Interactive Prototypes** for user testing
4. **Asset Preparation** (icons, images, animations)

### **Development Phase**
1. **Component Library** implementation
2. **Screen-by-Screen** development
3. **AI Integration** with fallback logging
4. **Testing & Polish** for professional finish

### **Quality Assurance**
1. **Design Consistency** review across all screens
2. **Accessibility** testing and compliance
3. **Performance** optimization and testing
4. **User Experience** validation and feedback

---

*This document provides the complete design specifications for CBT Buddy's professional, minimalistic UI. Focus on execution quality over feature quantity.*
