## 2024-03-25 - Initial Entry
**Learning:** React custom interactive components (such as `div` elements acting as buttons or drop zones) must include `role="button"`, `tabIndex={0}`, an `onKeyDown` handler for 'Enter' and 'Space' keys, and `:focus-visible` CSS styles to guarantee keyboard accessibility.
**Action:** Add these attributes to `div` elements that have `onClick` handlers, especially in sidebars and clickable cards.
