# The Açaí Truck - Admin Dashboard Design Specification

## 🎨 Design System

### Color Palette

#### Primary Colors
```css
--acai-purple: #68217A;      /* Primary brand color */
--berry-red: #D94370;        /* Secondary brand color */
--tropical-yellow: #F7C948;  /* Accent color */
```

#### Secondary/Neutral Colors
```css
--cream: #FFF8F3;           /* Light background */
--light-gray: #F5F5F5;      /* Card backgrounds */
--charcoal: #333333;        /* Text color */
--white: #FFFFFF;           /* Pure white */
```

#### Functional Colors
```css
--success: #4CAF50;         /* Green for completed/verified */
--warning: #FFA726;         /* Orange for pending */
--error: #EF5350;          /* Red for cancelled/failed */
--info: #42A5F5;           /* Blue for informational */
```

#### Gradients
```css
--gradient-primary: linear-gradient(135deg, #68217A 0%, #D94370 100%);
--gradient-accent: linear-gradient(135deg, #D94370 0%, #F7C948 100%);
--gradient-subtle: linear-gradient(180deg, #FFF8F3 0%, #FFFFFF 100%);
```

### Typography

**Font Family**:
- Primary: 'Poppins', sans-serif
- Secondary: 'Nunito Sans', sans-serif
- Monospace: 'JetBrains Mono', monospace (for order IDs)

**Type Scale**:
```css
--text-xs: 0.75rem;      /* 12px */
--text-sm: 0.875rem;     /* 14px */
--text-base: 1rem;       /* 16px */
--text-lg: 1.125rem;     /* 18px */
--text-xl: 1.25rem;      /* 20px */
--text-2xl: 1.5rem;      /* 24px */
--text-3xl: 1.875rem;    /* 30px */
--text-4xl: 2.25rem;     /* 36px */

--font-weight-normal: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;
```

### Spacing
```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
```

### Border Radius
```css
--radius-sm: 0.375rem;   /* 6px */
--radius-md: 0.5rem;     /* 8px */
--radius-lg: 0.75rem;    /* 12px */
--radius-xl: 1rem;       /* 16px */
--radius-2xl: 1.5rem;    /* 24px */
--radius-full: 9999px;   /* Circular */
```

### Shadows
```css
--shadow-sm: 0 1px 2px 0 rgba(104, 33, 122, 0.05);
--shadow-md: 0 4px 6px -1px rgba(104, 33, 122, 0.1);
--shadow-lg: 0 10px 15px -3px rgba(104, 33, 122, 0.1);
--shadow-xl: 0 20px 25px -5px rgba(104, 33, 122, 0.1);
```

---

## 🧭 Layout Structure

### Sidebar Navigation (260px width)

```
┌─────────────────────────────────────────┐
│  🥥 The Açaí Truck                      │
│                                         │
│  📊 Analytics                           │
│  🚚 Delivery Orders                     │
│  🏪 Pickup Orders                       │
│  📅 Deliveries                          │
│  ⚙️  Settings                           │
│                                         │
│  ───────────────────────────────        │
│                                         │
│  👤 Admin Name                          │
│  🌙 Dark Mode Toggle                    │
│  🚪 Logout                              │
└─────────────────────────────────────────┘
```

**Specifications**:
- Background: `--acai-purple` with `linear-gradient(180deg, #68217A 0%, #501960 100%)`
- Text: White/Cream
- Active item: Berry Red background with rounded corners
- Hover: Slightly lighter purple with smooth transition
- Icons: 20px, aligned left with 12px padding
- Collapse to icon-only on mobile (64px width)

### Top App Bar (64px height)

```
┌─────────────────────────────────────────────────────────┐
│  🔍 Search...     🔄 Refresh    🔔 (3)    👤 Admin ▼   │
└─────────────────────────────────────────────────────────┘
```

**Specifications**:
- Background: White with subtle shadow
- Search bar: Cream background, rounded, magnifying glass icon
- Icons: 24px, charcoal color with hover states
- Notification badge: Berry Red circle with white text
- Profile dropdown: Shows name, role, logout option

### Main Content Area

```
┌─────────────────────────────────────────────────────────┐
│  Breadcrumb / Page Title                                │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  [Content Grid - Responsive]                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Specifications**:
- Padding: 32px on desktop, 16px on mobile
- Background: Cream gradient
- Max-width: 1440px centered
- Grid: 12-column responsive grid system

---

## 📱 Component Library

### Metric Card

```
┌─────────────────────────────┐
│  💰 Total Revenue           │
│  $1,234.56                  │
│  ↗️ +12.5% vs last month   │
└─────────────────────────────┘
```

**Specifications**:
- Background: White with `--shadow-md`
- Border-radius: `--radius-lg`
- Padding: 24px
- Icon: 32px in colored circle (purple/red/yellow)
- Title: `--text-sm`, `--font-weight-medium`, gray
- Value: `--text-3xl`, `--font-weight-bold`, charcoal
- Trend: `--text-sm`, green (up) or red (down) with arrow icon
- Hover: Slight lift with `--shadow-lg`
- Transition: 200ms ease

### Status Badge

**Variants**:
```
[Pending]   - Yellow background, dark text
[Submitted] - Berry Red background, white text
[Verified]  - Green background, white text
[Completed] - Purple background, white text
[Cancelled] - Gray background, white text
```

**Specifications**:
- Border-radius: `--radius-full`
- Padding: 4px 12px
- Font-size: `--text-xs`
- Font-weight: `--font-weight-semibold`
- Text-transform: uppercase
- Letter-spacing: 0.05em

### Button

**Primary Button**:
```css
background: var(--gradient-primary);
color: white;
padding: 12px 24px;
border-radius: var(--radius-md);
font-weight: 600;
box-shadow: var(--shadow-md);
transition: all 200ms ease;

&:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}
```

**Secondary Button**:
```css
background: white;
color: var(--acai-purple);
border: 2px solid var(--acai-purple);
/* Same padding/radius as primary */
```

**Icon Button**:
- 40px × 40px circular
- Icon centered, 20px
- Cream background, charcoal icon
- Hover: Purple background, white icon

### Data Table

**Header**:
- Background: Light gray
- Text: Charcoal, `--font-weight-semibold`
- Sticky on scroll
- Sort indicators (▲▼)

**Rows**:
- Alternate backgrounds: White/Cream (subtle)
- Hover: Light purple tint
- Border: None (use background alternation)
- Padding: 16px 12px
- Text: `--text-sm`

**Mobile Transformation**:
- Convert to stacked cards below 768px
- Each row becomes a card with labels
- Actions become full-width buttons at bottom

### Chart Cards

```
┌─────────────────────────────────────────┐
│  📈 Daily Sales Trend                   │
│  ─────────────────────────────────────  │
│                                         │
│  [Chart Area]                          │
│                                         │
│  Legend: Revenue ● Orders              │
└─────────────────────────────────────────┘
```

**Specifications**:
- White background with `--shadow-md`
- Title area with icon and optional filter dropdown
- Chart uses brand colors (purple for revenue, berry red for orders)
- Minimal grid lines (light gray, dashed)
- Smooth curves, no harsh angles
- Interactive tooltips on hover
- Height: 400px on desktop, 300px on mobile

### Modal

```
┌─────────────────────────────────────────┐
│  Create New Delivery Session      ✕    │
│  ─────────────────────────────────────  │
│                                         │
│  Location: [_________________]         │
│  Delivery Date: [__________]           │
│  Cutoff Time: [___________]            │
│                                         │
│  [Cancel]  [Create Session]            │
└─────────────────────────────────────────┘
```

**Specifications**:
- Background: White
- Backdrop: Dark overlay (rgba(0,0,0,0.5))
- Border-radius: `--radius-xl`
- Padding: 32px
- Max-width: 560px
- Slide-up animation (300ms ease-out)
- Close button: Top-right corner, icon-only

### Toast Notification

```
┌─────────────────────────────────────────┐
│  ✓ Order verified successfully!        │
└─────────────────────────────────────────┘
```

**Specifications**:
- Position: Top-right corner, fixed
- Background: Success (green), Error (red), Info (purple)
- Text: White, `--font-weight-medium`
- Icon: 20px, left-aligned
- Padding: 16px 20px
- Border-radius: `--radius-md`
- Shadow: `--shadow-lg`
- Auto-dismiss: 3 seconds
- Slide-in from right animation

---

## 📄 Page Designs

### 1. Analytics (Landing Page)

**Layout Grid**:
```
Row 1: 6 Metric Cards (2 columns on mobile)
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ Orders  │ Revenue │ Avg $   │ Delivery│ Pickup  │Customers│
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘

Row 2: Chart (Full Width)
┌─────────────────────────────────────────────────────────┐
│  Daily Sales Trend (Last 30 Days)                      │
└─────────────────────────────────────────────────────────┘

Row 3: Two Tables (2 columns, stack on mobile)
┌────────────────────────┬────────────────────────────────┐
│ Top Customers          │ Top Delivery Sessions          │
└────────────────────────┴────────────────────────────────┘

Row 4: Two Tables (2 columns, stack on mobile)
┌────────────────────────┬────────────────────────────────┐
│ Popular Items          │ Store Performance              │
└────────────────────────┴────────────────────────────────┘
```

**Enhancements**:
- Add "Date Range Picker" in top-right (default: Last 30 Days)
- Add "Export Report" button (PDF/Excel)
- Insight cards with auto-generated messages:
  - "Best selling day: Monday with 47 orders"
  - "Top customer: Sarah Chen - $345.50 this month"
  - "Fastest growing location: NTU Hall 4 (+23%)"

### 2. Delivery Orders

**Header Section**:
```
┌─────────────────────────────────────────────────────────┐
│  Session: [Dropdown ▼]                    [Actions...]  │
│                                                         │
│  📍 NTU Hall 4  |  🕒 Dec 15, 6:00 PM  |  Status: OPEN │
└─────────────────────────────────────────────────────────┘
```

**Session Info Card**:
- Display selected session details in colored card (purple accent)
- Show: Location, Delivery Time, Cutoff Time, Status, Order Count, Total Revenue
- Quick actions: Refresh, Export, Cut Off, Close

**Orders Table**:
- Columns: Order ID, Customer, Items, Total, Payment (with thumbnail), Status, Actions
- Filter bar: Search, Payment Status filter, Sort by
- Empty state: Illustration with message "No orders yet for this session"
- Payment screenshot: Click to open lightbox preview

**Actions**:
- "Verify" button: Changes to "Verified ✓" with animation
- Bulk actions: "Verify All" for multiple orders
- Session actions in dropdown menu with icons

### 3. Pickup Orders

**Three Accordion Sections**:

```
▼ TODAY'S ORDERS (12)                    [Export CSV ▼]
┌─────────────────────────────────────────────────────────┐
│  [Table with collapsible details]                      │
└─────────────────────────────────────────────────────────┘

▶ UPCOMING ORDERS (28)
┌─────────────────────────────────────────────────────────┐
│  [Collapsed, click to expand]                          │
└─────────────────────────────────────────────────────────┘

▶ COMPLETED (LAST 3 DAYS) (45)
┌─────────────────────────────────────────────────────────┐
│  [Collapsed, click to expand]                          │
└─────────────────────────────────────────────────────────┘
```

**Color Coding**:
- Today: Purple left border accent
- Upcoming: Yellow left border accent
- Completed: Green left border accent

**Card View (Mobile)**:
```
┌─────────────────────────────────────────┐
│  #ORD-1234  |  2:30 PM  |  [CONFIRMED] │
│  ───────────────────────────────────    │
│  📍 Jurong West Store                   │
│  👤 John Tan (+65 9123 4567)            │
│  🥥 2x Classic Acai + Honey             │
│  💰 $16.00  |  Pay Now ✓               │
│                                         │
│  [Mark Completed]  [Mark Paid]         │
└─────────────────────────────────────────┘
```

**Enhancements**:
- Highlight overdue pickups (time passed) in red
- Show "Requires Payment" badge for unpaid "Pay at Counter" orders
- Add quick filters: "All", "Unpaid", "Ready for Pickup"
- Inline edit for pickup time adjustments

### 4. Deliveries

**Two Sections**:

**Create New Session (Sticky Card)**:
```
┌─────────────────────────────────────────────────────────┐
│  ➕ Create New Delivery Session                         │
│  ─────────────────────────────────────────────────────  │
│  Location: [_____________________________]             │
│  Delivery Date & Time: [______________] [_______]      │
│  Order Cutoff Time: [______________] [_______]         │
│                                                         │
│  [Cancel]  [Create Session]                            │
└─────────────────────────────────────────────────────────┘
```

**Sessions List (Table/Card View)**:
```
┌─────────────────────────────────────────────────────────┐
│  NTU Hall 4                            🟢 OPEN          │
│  🕒 Today, 6:00 PM  |  ⏰ Cutoff: 4:00 PM              │
│  📦 12 orders  |  💰 $96.00                             │
│                                                         │
│  [View Orders]  [Cut Off Now]  [Close Session]        │
└─────────────────────────────────────────────────────────┘
```

**Enhancements**:
- Toggle between Table and Calendar view
- Calendar shows sessions as events (color-coded by status)
- Session cards show real-time order count
- Auto-close sessions after delivery time + 3 days
- Visual indicator for sessions approaching cutoff time

### 5. Settings

**Tabbed Interface**:
```
[Branding] [Pricing] [Menu Options] [Pickup Stores]

Current Tab Content Area
```

**Tab 1: Branding**
```
┌─────────────────────────────────────────────────────────┐
│  Bot Welcome Title                                      │
│  [_________________________________________________]    │
│                                                         │
│  Bot Welcome Subtitle                                   │
│  [_________________________________________________]    │
│                                                         │
│  Branding Image                                         │
│  [Current Image Preview]  [Upload New]  [Remove]       │
│                                                         │
│  [Save Changes]                                         │
└─────────────────────────────────────────────────────────┘
```

**Tab 2: Pricing**
```
┌─────────────────────────────────────────────────────────┐
│  Price per Bowl                                         │
│  $ [______]  [SGD ▼]                                   │
│                                                         │
│  [Save Changes]                                         │
└─────────────────────────────────────────────────────────┘
```

**Tab 3: Menu Options**
```
┌─────────────────────────────────────────────────────────┐
│  ▼ Flavors                                [⋮ Edit] [✕] │
│     • Classic Acai        [⋮ Drag]                     │
│     • Protein Acai        [⋮ Drag]                     │
│     • Vegan Acai          [⋮ Drag]                     │
│     [+ Add Option]                                      │
│                                                         │
│  ▼ Sauces                                 [⋮ Edit] [✕] │
│     • Honey               [⋮ Drag]                     │
│     • Peanut Butter       [⋮ Drag]                     │
│     • Nutella             [⋮ Drag]                     │
│     [+ Add Option]                                      │
│                                                         │
│  [+ Add Group]                           [Save Changes] │
└─────────────────────────────────────────────────────────┘
```

**Tab 4: Pickup Stores**
```
┌─────────────────────────────────────────────────────────┐
│  Jurong West Store                      [Edit] [Delete] │
│  📍 Blk 123 Jurong West St 45                          │
│  🕒 Mon-Fri: 10am-8pm, Sat-Sun: 10am-6pm              │
│  ───────────────────────────────────────────────────   │
│  NTU Hall 4 Store                       [Edit] [Delete] │
│  📍 NTU Hall 4, 50 Nanyang Ave                         │
│  🕒 Daily: 11am-7pm                                    │
│                                                         │
│  [+ Add New Store]                                     │
└─────────────────────────────────────────────────────────┘
```

**Enhancements**:
- Inline editing with auto-save (debounced)
- Visual feedback on save: "Saved ✓" with fade-out
- Drag-and-drop reordering for menu options
- Store hours editor with visual time picker
- "Cache refreshed" indicator after saving

---

## 🎨 Interaction Patterns

### Micro-interactions

1. **Button Hover**: Lift effect (-2px translateY), shadow increase
2. **Card Hover**: Subtle shadow increase, slight scale (1.02)
3. **Status Change**: Pulse animation when status updates
4. **Data Refresh**: Spinning icon during load, fade-in on content update
5. **Form Validation**: Shake animation on error, checkmark on success
6. **Notification Badge**: Bounce animation on new notification

### Transitions

```css
/* Standard transition */
transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);

/* Slide-in (modal, toast) */
@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

/* Fade-in (page load) */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Scale-up (modal backdrop) */
@keyframes scaleUp {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
```

### Loading States

1. **Skeleton Screens**: Use for initial page loads
   - Match layout of loaded content
   - Animated shimmer effect (left to right)
   - Gray background with lighter animated overlay

2. **Spinners**: Use for button actions
   - Circular spinner in brand purple
   - 20px diameter
   - Smooth rotation animation

3. **Progress Bars**: Use for file uploads
   - Purple gradient fill
   - Percentage indicator
   - Success animation when complete

---

## ♿ Accessibility

### Color Contrast
- All text meets WCAG AA standard (4.5:1 for normal text, 3:1 for large text)
- Status not conveyed by color alone (include icons and text labels)
- Color-blind friendly palette tested with simulators

### Keyboard Navigation
- All interactive elements accessible via Tab key
- Logical tab order (left-to-right, top-to-bottom)
- Visible focus indicators (2px purple outline)
- Escape key closes modals and dropdowns
- Enter/Space activates buttons
- Arrow keys navigate dropdown menus

### Screen Readers
- Semantic HTML (nav, main, section, article)
- ARIA labels for icon-only buttons
- ARIA live regions for dynamic content updates
- Skip navigation link
- Descriptive alt text for all images
- Table headers properly associated with data cells

### Focus Management
- Focus trapped in modals
- Focus returns to trigger element when modal closes
- Focus moves to error messages on validation failure

---

## 📱 Responsive Breakpoints

```css
/* Mobile First Approach */
--breakpoint-sm: 640px;   /* Small devices */
--breakpoint-md: 768px;   /* Tablets */
--breakpoint-lg: 1024px;  /* Desktop */
--breakpoint-xl: 1280px;  /* Large desktop */
--breakpoint-2xl: 1536px; /* Extra large */
```

### Mobile (<768px)
- Sidebar collapses to icon-only (or hamburger menu)
- Top bar: Logo + hamburger + profile
- Metric cards: 1-2 per row
- Charts: Full width, reduced height
- Tables: Convert to stacked cards
- Actions: Full-width buttons
- Modals: Full screen on very small devices

### Tablet (768px-1024px)
- Sidebar: Full width when open, overlay
- Metric cards: 2-3 per row
- Tables: Horizontal scroll if needed
- Charts: Full width

### Desktop (>1024px)
- Sidebar: Persistent, 260px
- Metric cards: 3-6 per row
- Tables: Full features, all columns visible
- Charts: Larger, more detailed

---

## 🌙 Dark Mode (Optional Enhancement)

### Color Adaptations
```css
/* Dark Mode Palette */
--dm-background: #1a1a1a;
--dm-surface: #2a2a2a;
--dm-surface-elevated: #3a3a3a;
--dm-text-primary: #f5f5f5;
--dm-text-secondary: #b3b3b3;

/* Brand colors remain but slightly desaturated */
--dm-acai-purple: #7a3d8f;
--dm-berry-red: #e25c82;
--dm-tropical-yellow: #f9d45e;
```

### Toggle Implementation
- Moon/Sun icon in sidebar footer
- Smooth transition between modes (300ms)
- Preference saved in localStorage
- Respects system preference (prefers-color-scheme)

---

## 🔧 Technical Implementation Notes

### Recommended Tech Stack Migration

**Option 1: React + Tailwind + shadcn/ui**
- Component library: shadcn/ui (customizable, accessible)
- Styling: Tailwind CSS with custom config
- Charts: Recharts or ApexCharts
- Icons: Lucide React
- State management: Zustand or React Query
- Forms: React Hook Form + Zod validation

**Option 2: Vue 3 + Quasar**
- Framework: Quasar with Material Design customization
- Charts: ECharts or Chart.js
- Icons: Material Icons or Lucide
- State management: Pinia
- Forms: VeeValidate

### Component Structure Example (React)
```jsx
// src/components/ui/MetricCard.jsx
export function MetricCard({
  icon,
  title,
  value,
  trend,
  trendDirection
}) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <div className="metric-content">
        <h3 className="metric-title">{title}</h3>
        <p className="metric-value">{value}</p>
        <div className={`metric-trend ${trendDirection}`}>
          {trendDirection === 'up' ? '↗️' : '↘️'} {trend}
        </div>
      </div>
    </div>
  );
}
```

### CSS Architecture (BEM + Tailwind)
```css
/* Custom component classes with Tailwind @apply */
.metric-card {
  @apply bg-white rounded-lg p-6 shadow-md hover:shadow-lg
         transition-all duration-200 hover:-translate-y-1;
}

.metric-icon {
  @apply w-12 h-12 rounded-full flex items-center justify-center
         bg-gradient-to-br from-acai-purple to-berry-red;
}

.metric-value {
  @apply text-3xl font-bold text-charcoal mt-2;
}
```

### Animation Library
- Framer Motion (React) for page transitions and complex animations
- CSS transitions for simple hover effects
- Lottie for loading states and success animations

---

## 📋 Design Deliverables Checklist

### Phase 1: Core System
- [ ] Color palette CSS variables
- [ ] Typography scale and font loading
- [ ] Spacing and layout grid system
- [ ] Component library (buttons, cards, badges, etc.)
- [ ] Icon set selection and implementation

### Phase 2: Layout & Navigation
- [ ] Sidebar navigation design and responsiveness
- [ ] Top app bar with search and notifications
- [ ] Page layout templates (grid, spacing)
- [ ] Mobile navigation (hamburger menu)

### Phase 3: Page Designs
- [ ] Analytics page with charts and metrics
- [ ] Delivery Orders page with session selector
- [ ] Pickup Orders page with accordions
- [ ] Deliveries page with session management
- [ ] Settings page with tabbed interface

### Phase 4: Interactive Elements
- [ ] Modals and dialogs
- [ ] Toast notifications system
- [ ] Loading states (skeletons, spinners)
- [ ] Form validation styles
- [ ] Hover and focus states

### Phase 5: Data Visualization
- [ ] Chart.js/ECharts theme customization
- [ ] Table component with sorting/filtering
- [ ] Status badges and indicators
- [ ] Empty states and error messages

### Phase 6: Accessibility & Polish
- [ ] Keyboard navigation testing
- [ ] Screen reader compatibility
- [ ] Color contrast verification
- [ ] Mobile touch targets (44px minimum)
- [ ] Dark mode implementation (optional)

### Phase 7: Documentation
- [ ] Component usage guide
- [ ] Style guide with examples
- [ ] Accessibility guidelines
- [ ] Responsive design patterns

---

## 🎯 Success Metrics

### User Experience
- **Task completion time**: 30% reduction in time to verify payments
- **Error rate**: <2% user errors in order management
- **Mobile usability**: 90% of tasks completable on mobile
- **Learning curve**: New users productive within 15 minutes

### Performance
- **Page load time**: <2 seconds on 3G
- **Time to interactive**: <3 seconds
- **Lighthouse score**: >90 (Performance, Accessibility)

### Design Quality
- **Visual consistency**: 100% components follow design system
- **Accessibility**: WCAG AA compliance
- **Responsive**: Works on 95% of devices in analytics

---

## 📞 Next Steps

1. **Stakeholder Review**: Present this spec for feedback
2. **Prototype**: Create Figma/Adobe XD mockups for key pages
3. **User Testing**: Test with 3-5 actual users before development
4. **Development**: Implement in phases (core → pages → polish)
5. **QA**: Test across browsers, devices, and accessibility tools
6. **Launch**: Gradual rollout with feedback collection

---

This specification provides a comprehensive foundation for transforming The Açaí Truck admin dashboard into a modern, brand-aligned, and user-friendly experience. The design prioritizes operational efficiency while reflecting the vibrant, healthy personality of the brand.
