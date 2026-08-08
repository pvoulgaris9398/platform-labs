Good instinct to verify. My training data has a cutoff, so a few things are worth spot-checking against current releases — particularly the fast-moving ones in this stack.

Let me check the current versions of the key libraries and tools referenced in the steering files.


1 tool call
Available Kiro powers
Result:
No powers installed

You have no powers installed yet.

To get started:

Use action="configure" to open the powers UI

Browse and install available powers

Or ask me to help you find and install a power

Let me check the current state of the key libraries directly from PyPI and npm.


1 tool call
Sub-agent: spec-task-execution

23 tool calls
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
web_search
Here's the full rundown. Note that I'm writing this as of mid-2026, so several of these have moved significantly beyond what you might have in your steering files.

1. Python Current stable: 3.14 (released October 2025). Python 3.13 remains supported but 3.14 is the latest. Python 3.12 is still in security-only maintenance. Recommend targeting 3.13 or 3.14 for new projects. Notable in 3.13: experimental free-threaded mode (PEP 703) and JIT compiler (PEP 744). 3.14 continues the performance improvements.

2. FastAPI Current stable: ~0.140.x (still versioned sub-1.0 by design — the author has stated this reflects API stability policy, not maturity). No major breaking API changes recently; the framework continues to evolve with Pydantic v2 as the default and Starlette underneath. Annotated dependencies and lifespan handlers are the current idiomatic patterns.

3. Pydantic v2 Current stable: 2.13.4. Still on the v2 line. Key patterns since v2.0: use model_validator, field_validator with @classmethod, prefer model_config = ConfigDict(...) over class Config, and use model_dump() / model_validate() over the old v1 names. v2.13 added polymorphic serialization and exclude_if for computed fields.

4. SQLAlchemy Current stable: 2.0.51 (2.0 line is current and recommended). SQLAlchemy 2.1 is in beta (0b3 as of late June 2026) but not yet stable. Stick with 2.0.x. The 2.x ORM style (select(), session.execute(), mapped classes with Mapped[T] annotations) is the standard — the legacy Query API is deprecated.

5. Ruff Current stable: ~0.16.x (0.16.0 released late May 2026, with patch releases ongoing). This has moved fast from the 0.3–0.4 range. Key change in 0.15: new formatter style guide and range suppressions. 0.16 continues adding rules. Still the recommended replacement for Flake8 + Black + isort. Rule set recommendations remain the same: start with E, F, W, add I (isort), UP (pyupgrade), B (bugbear) as needed.

6. TypeScript Current stable: 7.0 (reached GA July 2026). This is a major shift — TS 7.0 is a native Go port of the compiler (~10x faster builds). TypeScript 6.0 was the last JS-based release and serves as the migration bridge. For new projects, 7.0 is now the target. Semantics are identical to 6.0; it's a performance/tooling change, not a type system change. If your steering file says "5.x", it's significantly out of date.

7. React Current stable: 19.2 (React 19 released December 2024). Major changes from 18: new use() hook, useOptimistic, useActionState, useFormStatus, Actions for data mutations, ref as a regular prop (no more forwardRef), React Compiler reached stable. The React Compiler handles memoization automatically, making manual useMemo/useCallback largely unnecessary in new code. Update steering files if they still reference React 18 patterns.

8. TanStack Query (React Query) Current stable: 5.100.x (v5 is current, well into its patch series). v5 is stable and the recommended version. Key v5 changes from v4: callbacks removed from useQuery, object-only API for useQuery/useMutation, status: 'pending' replaced status: 'loading', isPending replaces isLoading in most cases.

9. MUI (Material UI) Current stable: v7 (released March 2026 per their blog). v8 is in prerelease (the GitHub releases show v9.2.x in progress — MUI moves fast). v6 introduced Pigment CSS (zero-runtime CSS-in-JS); v7 standardized the slot pattern across components and improved ESM/CJS package exports. If your steering file says v5, it's two major versions behind.

10. React Router Current stable: v8 (released ~mid-2025). v7 was released late 2024 (merged with Remix), and v8 followed in 2025. The react-router-dom package is now just a re-export for v6 compatibility — new projects use react-router directly. If your steering file says v6, it's two major versions behind.

11. Vite Current stable: 8.2.x (Vite 8 released March 2026, 8.1 in June 2026). Vite 8's headline change: unified bundler powered by Rolldown (replaces the esbuild-dev/Rollup-prod split). Node.js 20.19+ or 22.12+ required. If your steering file references Vite 5 or 6, it's behind.

12. Vitest Current stable: ~5.0 (Vitest 4 released early 2025, v5 in mid-2026). Vitest 4 requires Vite ≥6.4 and Node ≥22. Fast-moving project. If your steering file references v1 or v2, it's significantly behind.

13. Terraform Current stable: 1.15.x (still on the 1.x series, 1.15 is the latest). The 1.x series maintains strong backward compatibility per HashiCorp's compatibility promise. No breaking changes to the language. 1.6+ is fine but 1.15 is current.

14. Hypothesis Current stable: 6.156.x (6.156.6 as of July 2026). Still on the 6.x series. Core usage patterns unchanged: @given, st.* strategies, @settings. No major API breaks. The library now requires a Rust toolchain to build from source (native wheels handle this for most users). Compatible with Python 3.14.

15. react-hook-form Current stable: 7.75.x (still on the 7.x major). The API has been stable for a long time. Patterns: useForm, Controller, FormProvider/useFormContext. Use @hookform/resolvers with Zod for schema validation — this is the dominant pattern.

16. Zod Current stable: v4 (Zod 4 reached stable in 2025). This is a significant change — Zod 3 is now functionally EOL (security fixes only, no new features). Zod 4 is faster (7x on array parsing), slimmer, and has breaking API changes. Key changes: new z.string().min() error message API, z.object() strict mode changes, new ZodError format. If your steering file targets Zod 3, flag this for migration.

Summary of items most likely to need steering file updates:

TypeScript: 5.x → 7.0 (or at minimum 6.0 as migration step)
React: 18 → 19.2 (new hooks, Compiler, ref-as-prop)
MUI: v5 → v7
React Router: v6 → v8
Vite: 5/6 → 8.x
Vitest: 1/2 → 5.x
Zod: v3 → v4 (breaking changes)
Python: 3.12 → 3.14 as latest (3.13 also fine)
Ruff: 0.3/0.4 → 0.16.x
Several things need updating — notably TypeScript (now 7.0, a Go-based rewrite), React 19, React Router v8, MUI v7, Vite 8, Vitest 5, and Zod v4. Let me update all four steering files now.


1 tool call
Read Files

python.md

typescript.md

design-principles.md

aws-infrastructure.md
Now I'll update all four files with the current versions. The biggest changes are in typescript.md (React 19, TypeScript 7, React Router v8, MUI v7, Vite 8, Vitest 5, Zod v4) and python.md (Python 3.13/3.14, Ruff 0.16.x). The design principles and AWS files are largely timeless and need only minor touches.


1 tool call
Sub-agent: spec-task-execution

4 tool calls
Replace in File

python.md


Replace in File

python.md


Replace in File

python.md


Replace in File

python.md


Now for the TypeScript file — the largest set of changes:


4 tool calls
Replace in File

typescript.md


Replace in File

typescript.md


Replace in File

typescript.md


Replace in File

typescript.md


You've reached your monthly usage limit. Please return next month to continue building. (Request ID: 214a4f66-444b-4a13-bd8c-ebbf58871f96)You've reached your monthly usage limit. Please return next month to continue building. (Request ID: dd2ecd24-f513-4bf2-829e-2d21575b8e15)