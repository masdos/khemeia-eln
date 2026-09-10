# DESIGN.md

Design system reference document for the application. Its purpose is to establish visual and behavioral decisions so that any developer or agent adding a new screen does so consistently with the rest. Every rule below reflects the current implementation; anything not implemented is intentionally absent.

---

## 1. Objective

The application provides a simple and consistent interface for entity management through CRUD operations plus detail pages. Priority is given to speed of use, readability, and uniformity across modules.

---

## 2. Design Principles

* Clear interface, with no decorative elements that don't provide information.
* Default Quasar/NiceGUI theme (no custom theme): primary blue for constructive actions, negative red for destructive ones.
* Strict consistency across screens: a new section should be buildable by copying another section's structure without additional design decisions.
* Forms always maintain the same field and button layout.
* List screens and detail screens follow two fixed flows (sections 3 and 11); no third layout exists.
* Tables occupy most of the available space in the content area.

---

## 3. General Structure

The window is divided into two columns inside a single `ui.row()`:

* **Left sidebar (sticky):** white card (`w-60`, internal scroll), logo at the top, vertical navigation menu below. It stays visible while the content scrolls.
* **Content area (variable):** white card (`flex-1 min-w-0 max-w-6xl`), changes based on the selected section; occupies the rest of the width.

List screen flow, top to bottom:

```
Sidebar (sticky) → Section title → Toolbar (Search + New) → Records table
```

Detail screen flow, top to bottom:

```
Title → Meta line → Editable form → Save (right) → Extra sections → Back
```

---

## 4. Navigation

* Single-page application: one `@ui.page("/")`; the router clears and rebuilds only the content column. The sidebar is built once and never re-rendered when switching pages; only the active state of its buttons is toggled.
* The active option is highlighted with a `bg-slate-100` background; inactive options use `hover:bg-slate-100`.
* Detail views (`experiment_detail`, `project_detail`, `protocol_detail`, `reagent_detail`, `equipment_detail`) are not menu entries: when one is open, no menu option is highlighted.
* Every detail page ends with a back button (`arrow_back`, `flat round`) returning to its parent list.

---

## 5. Layout

Column distribution:

* Sidebar: `w-60` (240 px), `shrink-0`, sticky (`top-4`, `max-height: calc(100vh - 2rem)`, internal scroll).
* Content: `flex-1 min-w-0 max-w-6xl`.
* Shell row: `w-full min-h-screen gap-4 p-4 items-start flex-nowrap`.

Internal flow of the content area:

```
Page header → Action bar (Search / New) → Table or Form
```

List pages wrap content in `ui.column().classes("w-full max-w-6xl mt-8 px-4")`.

---

## 6. Components

### Buttons

| Type | Props | Placement |
|---|---|---|
| Primary (New, Save, Create, Link) | `color=primary` | Right side of toolbars; right end of forms |
| Secondary (Cancel) | `outline` (dialogs) or `flat` (delete confirmations) | After the primary button |
| Delete | `color=negative` | After Cancel in delete confirmations |
| Icon buttons (table actions, back) | `flat dense` (tables) or `flat round` (back) | Actions column / bottom-left |

Dialog button order is always primary first, secondary second, from left to right (`Create` then `Cancel`, `Save` then `Cancel`, `Delete` then `Cancel`).

### Search

* Always in the toolbar row, left of the action button: `ui.input(placeholder="Search ...").props("outlined dense").classes("flex-1")`.
* Typing re-renders the table (`on_value_change` → refresh).

### Table

* `ui.table(columns, rows, row_key="id", pagination=10).classes("w-full")`.
* Columns end with an `Actions` column (centered) rendered via a `body-cell-actions` slot with flat dense icon buttons: `visibility` (view) and `delete` (negative); reagents add `history`.
* No `edit` icon exists anywhere: rows are edited from the detail page, never from the table.
* State values (experiments) render as a colored badge (`Running` blue, `Success` green, `Fail` red) via a `body-cell-state` slot.
* Long text columns show a truncated preview (80 chars) linking to the full content on the detail page.

### Forms

* Labels above the field (`ui.input("Name *")`, `ui.textarea("Description")`), `outlined`, `w-full`.
* A single `ui.label().classes("text-negative mt-2")` under the form shows validation errors.
* Dialog buttons live in `ui.row().classes("w-full justify-end gap-2 mt-4")`, primary first.
* Detail pages place a lone Save in `ui.row().classes("w-full justify-end mt-4")`.

### Markdown editor

Protocols and experiment notes share `markdown_editor(label, value)` from `app/ui/components/markdown_editor.py`: a toolbar row of `flat dense` insert buttons (`H1/H2/H3`, `Bold`, `Italic`, `Table`, `List`) above a 50/50 row with an `outlined` textarea on the left and a bordered live `ui.markdown` preview on the right. It returns the textarea element.

### Meta line and hazards

* Detail pages render the Created/Modified line with `entity_meta(created_at, modified_at)` from `app/ui/components/meta.py`.
* GHS checkbox groups come from `ghs_checkboxes(fields, initial)` in `app/ui/components/ghs.py`, which renders the label, the wrapping row and returns the field-to-checkbox mapping.

### Tabs

Inventory uses `ui.tabs()` with `Reagents` and `Equipment` tab panels; each panel repeats the list flow (toolbar + table) of section 11.

---

## 7. Color Palette

No custom theme; colors come from Tailwind slate utilities and the default Quasar palette.

| Element | Style | Usage |
|---|---|---|
| Application background | `bg-slate-100` on `body` | Shell background |
| Surface (sidebar, content card) | `#FFFFFF`, 12 px radius, `1px solid #E5E7EB`, subtle shadow | Panels |
| Active menu element | `bg-slate-100` | Selected page |
| Menu hover | `hover:bg-slate-100` | Menu buttons |
| Primary action | `color=primary` (Quasar blue) | New / Save / Create / Link |
| Danger | `color=negative` (Quasar red) | Delete buttons, `text-negative` messages |
| Primary text | `text-2xl font-semibold` titles, default body | Titles and content |
| Secondary text | `text-slate-500` / `text-slate-600`, `text-sm` meta lines | Auxiliary information, empty states |

---

## 8. Typography

System font stack (no webfont configured). Sizes via Tailwind utilities:

```
Section/detail title   text-2xl font-semibold
Subsection title       text-xl font-semibold
Field group label      font-semibold
Meta / auxiliary       text-sm text-slate-500
Table actions          text-xs (icon buttons)
```

---

## 9. Spacing

Observed utilities (Tailwind):

```
Shell padding:                   p-4, gap-4
Content card padding:            p-6
Page top offset:                 mt-8 px-4
Toolbar:                         w-full items-center gap-4 (+ mt-4 on list pages)
Dialog button row:               w-full justify-end gap-2 mt-4
Detail save row / back button:   mt-4
Card widths (dialogs):           w-[28rem] deletes, w-[32rem] simple forms,
                                 w-[36rem] history, w-[40rem] wide forms
```

---

## 10. Iconography

Material Icons via Quasar `icon=` / `<q-btn icon=...>`. Only these are in use:

```
visibility   → View row (goes to detail page)
delete       → Delete row / attachment / linked resource (negative)
history      → Reagent usage history dialog
image        → Molecule structure preview
content_copy → Copy SVG
arrow_back   → Back to parent list (detail pages)
science, folder, article, shelves, contact_page → sidebar entries
```

Buttons that create or save use text labels (`New ...`, `Add ...`, `Create`, `Save`, `Link`), never icons alone.

---

## 11. CRUD Tables

Standard structure, identical across all sections (Experiments, Projects, Protocols, Reagents, Equipment):

```
Section title
Search (flex-1) + New/Add (right)
Table (entity-specific columns + Actions column)
View / Delete per row (reagents: View / History)
```

Only the table content and associated form fields change; the layout never changes. Editing always happens on the detail page.

---

## 12. Forms

* Required fields are marked with `*` in the label and validated in the service layer before saving; the error text goes to the single message label under the form.
* Mandatory confirmation before deleting any record (modal `ui.dialog`, never a browser alert).
* Notification after saving, via `ui.notify("...", type="positive")` (framework default position, no explicit placement).
* Locked fields (reagent CAS/SMILES once the reagent has experiment history) use the `disable` prop plus an explanatory note; the remaining fields stay editable.

---

## 13. Interface States

| State | Definition |
|---|---|
| Hover | `hover:bg-slate-100` on menu buttons; Quasar defaults on table rows and buttons |
| Focus | Quasar default input focus ring |
| Disabled | `disable` prop on the input plus a `text-sm text-slate-500` note explaining why (e.g. CAS/SMILES locked by usage history) |
| Loading | Not required as the database is local |
| Empty | Fixed messages: `No <entities> in inventory.` / `No <entities> found.` for empty tables, `No <entities> match the search.` after a fruitless search, `No experiments use this reagent.` for empty history |
| Error | Single `text-negative` label under the form for recoverable errors; `ui.notify(..., type="negative")` when the entity is missing |
| Success | Notification via `ui.notify("... updated/created/deleted", type="positive")` |

---

## 14. Responsive (Behavior on Resizing)

Desktop-only NiceGUI app in native mode (default window 1600×900, `reload=False`):

* No breakpoint system; the shell row uses `flex-nowrap` with `items-start` so the sticky sidebar keeps working at any width.
* Minimum practical width derives from the sidebar (`w-60`) plus the content card; narrow windows scroll horizontally instead of reflowing.

---

## 15. Implementation Conventions in NiceGUI

Base components used consistently:

```
ui.column()      → sidebar, content card, page grouping
ui.row()         → shell, toolbars, button rows
ui.table()       → records tables (pagination=10, row_key="id")
ui.dialog()      → confirmations and modal forms (same button order everywhere)
ui.notify()      → success/error notifications
ui.tabs()        → inventory Reagents/Equipment panels
```

Code rules (as implemented):

* One page per file: `app/ui/pages/<entity>.py` for lists, `<entity>_detail.py` for detail pages.
* Shared component library in `app/ui/components/` — pages must use it instead of re-implementing the covered patterns:
  * `forms.py`: `form_message()`, `dialog_actions(...)`, `detail_save_row(...)`, `back_button(target_view)`.
  * `dialogs.py`: `confirm_delete_dialog(...)`; deletion errors surface by raising `ConfirmBlocked`.
  * `tables.py`: `entity_table(...)`, `add_view_delete_actions(...)`, `add_view_actions(...)`, `add_view_history_actions(...)`, `add_state_badge(...)`, `add_experiment_actions(...)`.
  * `lists.py`: `search_toolbar(...)` (`top_margin=False` for tab-embedded toolbars).
  * `markdown_editor.py`: `markdown_editor(label, value)`.
  * `meta.py`: `entity_meta(created_at, modified_at)`.
  * `ghs.py`: `ghs_checkboxes(fields, initial)`.
* No centralized style module: slate utilities and card styles are repeated inline; copy the exact classes from an existing page or component.
* Navigation only through `app.ui.router.navigate()` / `refresh()`; page builders never call `ui.navigate` (except the one-time welcome-dialog reload).
* UI tests patch the `ui` object of each module under test (`app.ui.pages.<page>.ui` and, when the page uses them, `app.ui.components.<module>.ui`).

---

## 16. Consistency Guide

| Element | Rule |
|---|---|
| Titles | Always left-aligned, `text-2xl font-semibold` |
| "New"/"Add" button | Always top right of the toolbar, `color=primary` |
| Search | `outlined dense`, `flex-1`, left of the action button, above the table |
| Actions | Last column of the table, `visibility` then `delete` (reagents: `visibility` then `history`) |
| Dialog buttons | `justify-end`, primary first (`Create`/`Save`/`Delete`, then `Cancel`) |
| Detail Save | Lone Save, `justify-end` row |
| Back | `arrow_back`, `flat round`, bottom-left, returns to parent list |
| Confirmation | Mandatory `ui.dialog` before deleting |
| Messages | Single `text-negative` label under the form; `ui.notify()` for outcomes |
| Dialog widths | `w-[28rem]` deletes, `w-[32rem]` simple forms, `w-[36rem]` history, `w-[40rem]` wide forms |
| Shared UI | `app/ui/components/` helpers, never re-implement a covered pattern inline |
| Disabled fields | `disable` prop + explanatory note, never silent |

This table should be consulted when adding a new section and there is doubt about where each element should go.
