## 2024-05-24 - Interactive Drop Zones Accessibility
**Learning:** Custom interactive components like `div` drop zones (`.upload-zone`) need explicit `role="button"`, `tabIndex={0}`, an `onKeyDown` handler (for 'Enter' and 'Space' keys), and `:focus-visible` styles to ensure full keyboard accessibility. Without these, keyboard users cannot interact with the drop zone to upload files.
**Action:** When creating custom interactive elements, always ensure they are fully navigable and activatable via keyboard, mimicking native button or input behavior.
