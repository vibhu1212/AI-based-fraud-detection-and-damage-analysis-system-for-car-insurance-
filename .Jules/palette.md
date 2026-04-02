## 2024-03-22 - Keyboard Accessibility for Custom Interactive Components
**Learning:** Custom interactive elements (like `div` elements acting as buttons or drop zones) without native semantic meaning lack built-in keyboard accessibility support by default.
**Action:** When creating custom interactive elements, always include `role="button"`, `tabIndex={0}`, an `onKeyDown` handler for 'Enter' and 'Space' keys, and `:focus-visible` CSS styles to ensure complete keyboard navigation and usability.
