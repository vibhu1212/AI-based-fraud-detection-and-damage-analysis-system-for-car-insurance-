## 2026-03-29 - [Upload Zone Keyboard Accessibility]
**Learning:** Upload zones implemented as `div`s with click handlers lack native keyboard accessibility, requiring explicit `role="button"`, `tabIndex={0}`, `onKeyDown` handlers, and `:focus-visible` styles.
**Action:** When encountering interactive `div` elements (like drop zones or cards), always ensure they are fully keyboard accessible by adding necessary ARIA roles, tabindex, keyboard event handlers, and focus styles.
