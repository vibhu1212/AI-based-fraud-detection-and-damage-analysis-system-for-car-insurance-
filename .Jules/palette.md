## 2024-03-27 - [a11y: Interactive div patterns]
**Learning:** This codebase heavily relies on `div` elements for interactive zones (like drag-and-drop upload areas and pipeline nodes) without proper semantic button roles or keyboard accessibility built-in. This pattern locks out keyboard users entirely from core interactions.
**Action:** Always check `onClick` handlers attached to `div` elements. Convert them to semantic `<button>` elements when possible, or ensure they have `role="button"`, `tabIndex={0}`, an `onKeyDown` handler for 'Enter' and 'Space', and `:focus-visible` styles.
