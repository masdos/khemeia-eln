# DESIGN.md

Design system reference document for the application. Its purpose is to establish visual and behavioral decisions so that any developer or agent adding a new screen does so consistently with the rest.

---

## 1. Objective

The application provides a simple and consistent interface for entity management through CRUD operations. Priority is given to speed of use, readability, and uniformity across modules.

---

## 2. Design Principles

* Clear interface, with no decorative elements that don't provide information.
* Minimal color palette; the logo's green is reserved for actions and relevant states, not for fill.
* Strict consistency across screens: a new section should be buildable by copying another section's structure without additional design decisions.
* Forms always maintain the same field and button layout.
* Primary actions (New, Save) are identifiable without reading text, solely by position and color.
* Tables occupy most of the available space in the content area.

---

## 3. General Structure

The window is divided into two columns:

* **Left sidebar (fixed):** logo at the top, vertical navigation menu below.
* **Content area (variable):** changes based on the selected section; occupies the rest of the width.

CRUD screen flow, top to bottom:

```
Sidebar (fixed) → Section title → Toolbar (Search + New) → Records table
```

---

## 4. Navigation

* The menu remains fixed throughout execution; it doesn't hide or collapse unless section 14 explicitly defines it for small windows.
* The active option is highlighted with `#B1CC33` background and a 4 px left bar in `#5C9E31`.
* Each menu option loads a different page in the content area; the sidebar doesn't re-render when switching pages.

---

## 5. Layout

Column distribution:

* Sidebar: 240 px, fixed width.
* Content: rest of the window width.

Internal flow of the content area:

```
Page header → Action bar (Search / New) → Table or Form
```

---

## 6. Components

### Buttons

| Type | Background | Text | Border |
|---|---|---|---|
| Primary (New, Save) | `#5C9E31` | `#FFFFFF` | — |
| Secondary (Cancel) | `#FFFFFF` | `#5C9E31` | `#5C9E31` |
| Delete | `#D9534F` | `#FFFFFF` | — |
| Primary hover | `#4D8529` | `#FFFFFF` | — |

The logo's green is not used for the Delete button: mixing them would break color semantics (green = constructive action, red = destructive action).

### Search

* Always positioned above the table, never beside the title.
* Occupies approximately 40–50% of the toolbar width.
* The "New" button occupies the right side of the same toolbar.

### Table

* Header: `#F3F5F3` background.
* Rows: white background, hover `#F1F7EB`.
* Row selection: `#E6F1D5`.
* Borders: `#D9E3D4`.
* Actions column (Edit / Delete) always in the last position.
* Classic pagination.

### Forms

* Labels above the field, never beside it.
* Save / Cancel buttons always at the end of the form, in that order from left to right, Save as primary.

---

## 7. Color Palette

| Element | Color | Usage |
|---|---|---|
| Main background | `#F7F9F7` | Application background |
| Surface (cards, tables) | `#FFFFFF` | Panels and tables |
| Sidebar | `#EEF4E6` | Side menu |
| Active menu element | `#B1CC33` | Selected page |
| Primary button | `#5C9E31` | "New" button, Save |
| Button hover | `#4D8529` | Hover state |
| Primary text | `#1F1F1F` | Titles and content |
| Secondary text | `#666666` | Auxiliary information |
| Borders | `#D9E3D4` | Separators and tables |
| Input background | `#FFFFFF` | Text boxes |
| Row hover | `#F1F7EB` | Table |
| Table selection | `#E6F1D5` | Selected row |
| Danger (Delete) | `#D9534F` | Delete button |

---

## 8. Typography

```
Font: Inter

Application title     32 px
Section title         24 px
Normal text           16 px
Table                 14 px
```

---

## 9. Spacing

```
Outer margin:                  24 px
Separation between components: 16 px
Separation between groups:     32 px
Button padding:                12 x 20 px
```

---

## 10. Iconography

Single family: Material Icons (or Material Symbols, don't mix both).

```
add     → New
edit    → Edit
delete  → Delete
search  → Search
save    → Save
cancel  → Cancel
```

---

## 11. CRUD Tables

Standard structure, identical across all sections (Projects, Protocols, Experiments...):

```
Section title
Search + New
Table (entity-specific columns + Actions column)
Edit / Delete per row
```

Only the table content and associated form fields change; the layout never changes.

---

## 12. Forms

* Validation of required fields before allowing Save.
* Error messages next to the corresponding field, not in a separate block.
* Mandatory confirmation before deleting any record (modal dialog, not a simple browser alert).
* Notification after saving, via `ui.notify()`.

---

## 13. Interface States

| State | Definition |
|---|---|
| Hover | `#F1F7EB` on table rows; `#4D8529` on primary button |
| Focus | `#5C9E31` border + subtle shadow of the same color on inputs |
| Disabled | Pending definition (not yet set in current decisions) |
| Loading | Not required as the database is local |
| Empty | Requires "No records" message for empty tables and "No results" after search with no matches |
| Error | Non-blocking banner at the top of the content area for recoverable errors (e.g. "Could not save, please retry") |
| Success | Notification via `ui.notify()` |

---

## 14. Responsive (Behavior on Resizing)

Being a desktop application, it doesn't apply a web-style breakpoint system, but minimum behavior must be defined:

* Minimum window width: 950-1000 px total width.
* Sidebar and table behavior in narrow windows: native window configuration.

---

## 15. Implementation Conventions in NiceGUI

Base components to use consistently:

```
ui.left_drawer()   → fixed sidebar
ui.header()        → page header
ui.column()        → vertical grouping
ui.row()           → horizontal grouping
ui.table()         → records tables
ui.dialog()        → confirmations and modal forms
ui.notify()        → success/error notifications
```

Code rules:

* One page per file.
* Reusable components for section header, toolbar (search + New), and table, instead of re-implementing them on each page.
* Styles (colors, typography, spacing) centralized at a single point (e.g. constants or global CSS via `ui.add_css`), never hardcoded per screen.

---

## 16. Consistency Guide

| Element | Rule |
|---|---|
| Titles | Always left-aligned |
| "New" button | Always top right |
| Search | Always above the table |
| Actions | Last column of the table |
| Confirmation | Mandatory before deleting |
| Messages | `ui.notify()` in the top-right corner |
| Dialogs | Same width and same buttons across all entities |

This table should be consulted when adding a new section and there is doubt about where each element should go.
