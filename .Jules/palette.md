## 2024-03-24 - Interactive Div Accessibility
**Learning:** React custom interactive components (such as `div` elements acting as buttons or drop zones) must include `role="button"`, `tabIndex={0}`, an `onKeyDown` handler for 'Enter' and 'Space' keys, and `:focus-visible` CSS styles to guarantee keyboard accessibility.
**Action:** When implementing custom interactive elements, always add ARIA roles, tabindex, keyboard event listeners, and visible focus indicators.
