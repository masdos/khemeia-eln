---
name: khemeia-next-feature
description: >
  Skill for the Khemeia ELN project. Use this whenever the user says
  "implement the next feature", "continue with the next feature",
  "next task", or any variant that implies moving on to the project's next
  pending item. This skill automatically locates the first feature with
  `status: "pending"` in `feature_list.json`, loads the required architectural
  context, and guides the complete implementation until the feature is marked
  as `done`. The user does not need to specify which feature or where the
  context files are located.
---

# Khemeia ELN — Implement Next Feature

## 1. Locate the next pending feature

Read the project's `feature_list.json` file. Find the **first** object whose
`status` field is `"pending"`. That is the feature to implement.

If there are no `"pending"` features, inform the user that all features are
completed or blocked and stop.

**File location:**
```
/docs/feature_list.json
```

## 2. Mark as in_progress

Before writing code, update the selected feature's `status` field to
`"in_progress"` in `feature_list.json`.

If `feature_list.json` is located in `/docs/` (read-only), tell the
user they must update it manually or copy it into the working directory. In
either case, proceed using the content you read.

## 3. Load architectural context

Read the following project reference files:

| File | When to read |
|---|---|
| `/docs/plan-v2.md` | Always. Contains layered architecture, data model, and technical strategy. |
| `/docs/spec.md` | If the feature implements a User Story (UI, business services). |
| `/docs/feature_list.json` | Already read in step 1. Contains all acceptance criteria. |

## 4. Build the implementation context

Before generating code, extract the following from the selected feature:

- `id` and `name` → to name files and tests correctly
- `description` → the module's purpose
- `acceptance` → list of criteria the code must satisfy (functional and test requirements)

Cross-reference the `acceptance` items with `plan-v2.md` to identify:
- Which layer it implements (Repository / Service / UI)
- Which other modules it depends on
- Which patterns apply (Repository Pattern, `AIProvider` interface, `FileService`, etc.)

## 5. Implement the feature

### Implementation rules

1. **One file per entity** — Follow the folder structure described in `plan-v2.md` section 4.
2. **No service executes SQL directly** — Services must only call repositories.
3. **Tests are mandatory** — Every feature includes its test file. A feature is not `done` without tests.
4. **Repository tests** use SQLite `:memory:` with the real schema (`schema.sql`).
5. **Service tests** use in-memory repositories (no SQLite).
6. **Graceful degradation** — If an external component (AI, RDKit) is unavailable, the system must not raise an unhandled exception.
7. **FileService** is the only component aware of the filesystem. Never store absolute paths in the database.
8. **is_locked** — A locked experiment cannot be modified. Raise an exception if modification is attempted.

### Generation order

```
1. Production code  →  src/{layer}/{module}.py
2. Tests            →  tests/{layer}/test_{module}.py
3. Verify acceptance →  check each acceptance criterion in the list
```

### Acceptance checklist

When implementation is complete, show a table with each `acceptance` criterion and
whether it is covered (✅ / ❌). Do not mark the feature as `done` if any criterion is ❌.

```
| Criterion | Status |
|---|---|
| src/repositories/experiment_repository.py exists | ✅ |
| lock() is atomic | ✅ |
| ... | ... |
```

## 6. Mark as done

When all acceptance criteria are ✅, update the feature's `status` to `"done"`
in `feature_list.json`.

Inform the user:
- Feature completed
- Files created
- Next pending feature (name and id), so they know what's next

---

## Quick architecture reference

```
UI (NiceGUI)
    └── Services          ← Business logic (never SQL)
         └── Repositories ← Data access (raw SQL)
              └── SQLite
```

**Key patterns:**
- `AIProvider` is an abstract interface; never instantiate a concrete provider
  outside `AIService`.
- `FileService` resolves paths by combining `BASE_DIR` (from config.json)
  with relative paths.
- `SecurityService.calculate_hash()` is a pure function (same input → same output).
- User configuration lives in `config.json`, not in the database.
- There is no `users` table; the author is read from `config.json` at runtime.