---
name: web-design-guidelines
description: Vercel Web Interface Guidelines audit tool reporting WCAG issues, responsive breakpoints, and the 34 Production-Grade Pages in file:line format.
---

# Web Design Guidelines & Production-Grade Audit Protocol

*(Adapted from vercel-labs/agent-skills/skills/web-design-guidelines)*

This skill executes rigorous design audits against modern web standards, WCAG 2.1 accessibility guidelines, Vercel design principles, and the 34 Production-Grade Pages checklist.

## Interactive Audit Trigger
Similar to security testing, when a frontend feature or page implementation is completed, prompt the user:
> *"Would you like to run the Web Design Guidelines & Accessibility Audit now?"*

## Audit Checklist & Metrics

### 1. Visual & Contrast Rigor (WCAG 2.1 AA/AAA)
- Contrast ratio between text and background: minimum **4.5:1** for regular text, **3:1** for large text (18pt / 24px bold).
- Interactive element boundaries (buttons, inputs) must maintain **3:1** contrast against adjacent backgrounds.
- Avoid color as the sole indicator of state (e.g., pair error reds with an explicit warning icon and descriptive helper text).

### 2. Ergonomics & Touch Targets
- Minimum touch target dimension: **44px × 44px** on mobile viewports.
- Adequate spacing between clickable links to prevent accidental taps.
- Explicit `:focus-visible` styling on all interactive controls (buttons, links, inputs, tabs) with high-contrast outlines and offsets.

### 3. Typography & Responsive Geometry
- Scalable typography using `rem` units; body copy minimum **16px** to prevent iOS Safari auto-zooming.
- Proper line length: 45–75 characters per line for body paragraphs.
- Zero horizontal overflow at any viewport (375px, 768px, 1024px, 1440px).

### 4. The 34 Production-Grade Pages Verification
Audit whether the application includes necessary production pages:
- **Legal (15 Pages)**: Privacy Policy (GDPR & DPDP Act 2023 compliant), Terms of Service, Cookie Policy, Cookie Preferences (Active toggle modal), Refund Policy, Cancellation Policy, Shipping Policy, Return/Exchange Policy, Disclaimer, Accessibility Statement, DPA, Acceptable Use Policy, Security Policy, Responsible Disclosure, Community Guidelines.
- **Customer Lifecycle (16 Pages)**: Login, Register / Sign Up, Email Verification, Forgot Password, Reset Password, Onboarding Wizard / Stepper, Account Settings & Profile, Billing Dashboard & Invoices, Upgrade Tier, Downgrade Tier, Cancel Subscription (Retention flow), Payment Success, Payment Failed, Payment Pending, Support Desk, Help Center / Knowledge Base.
- **UX States & Resilience (10 States)**: 404 Not Found (with search and home link), 403 Forbidden / Unauthorized, 500 Internal Server Error, Maintenance Mode, Offline Mode (PWA Background Sync), Empty State (No data with CTA), No Search Results, Skeleton Loading States, Error Toast / Modal States, Session Expired (preserving unsaved form inputs).

### 5. Output Format
Report all discovered issues strictly in `file:line` format:
```text
[VIOLATION] path/to/file.tsx:42
Issue: Insufficient contrast ratio (2.8:1) on muted helper text.
Required: Increase color contrast to at least 4.5:1 (e.g. change text-zinc-400 to text-zinc-200).
Diff:
- <span className="text-zinc-400 text-xs">Optional</span>
+ <span className="text-zinc-300 text-xs">Optional</span>
```

