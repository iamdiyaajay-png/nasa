---
name: playwright-cli
description: End-to-end browser automation, visual regression testing, multi-viewport snapshots, and console error auditing.
---

# Playwright Browser Automation & E2E Testing

This skill provides testing patterns for headless browser automation, multi-viewport validation, and runtime error auditing.

## Testing Matrix & Viewports

Every web application and feature must be verified against three standard viewports:
- **Mobile**: 375x667 (iPhone SE) or 390x844 (iPhone 14)
- **Tablet**: 768x1024 (iPad Portrait)
- **Desktop**: 1440x900 / 1920x1080 (Standard HD)

## Core Auditing Responsibilities

1. **Multi-Viewport Visual Checks**
   - Verify layout responsiveness, avoiding horizontal scrollbars on mobile.
   - Ensure burger menus, drawers, and modal backdrops render and dismiss properly on touch viewports.

2. **Unhappy Path & Resilience Verification**
   - Test error states: invalid login inputs, expired session tokens, offline network state, 404 navigation.
   - Confirm form error messages display inline next to corresponding fields.

3. **Console & Network Auditing**
   - Assert zero unhandled JavaScript exceptions or console errors.
   - Assert zero 400/500 API failures on standard user journeys.
   - Check that CORS and security headers are properly handled.

