## 2024-03-17 - Keyboard Navigable Drag-and-Drop Zones
**Learning:** Custom div-based upload zones (drag-and-drop areas) are inherently inaccessible to keyboard users unless explicitly made focusable and interactive.
**Action:** Always add `role="button"`, `tabIndex={0}`, and an `onKeyDown` handler (listening for 'Enter' and ' ') to trigger the hidden file input when creating custom upload areas. Pair this with `:focus-visible` styling for visual feedback.

## 2024-03-17 - Icon-only Buttons and Loading States
**Learning:** Icon-only utility buttons (like a small 'X' to remove an image) are invisible to screen readers without context, and loading buttons lack state announcements.
**Action:** Add descriptive `aria-label` attributes to icon-only buttons (e.g., "Remove image 1"). Use `aria-busy={isProcessing}` on primary action buttons that trigger async operations to announce their loading state to assistive technologies.