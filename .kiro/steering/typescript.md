# TypeScript and React Best Practices

## Language
- Target TypeScript 7.0+ (the native Go-based compiler, ~10x faster builds; type semantics are identical to 6.x — no breaking type system changes from 5.x). Use TypeScript 6.0 as the migration bridge if upgrading from 5.x. Enable `"strict": true` in `tsconfig.json`. Enable `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`.
- No `any`. Use `unknown` when the type is genuinely unknown and narrow with type guards. Use `never` to exhaustively check discriminated unions.
- Prefer `interface` over `type` for object shapes that may be extended. Use `type` for unions, intersections, and mapped types.
- All function parameters and return types must be explicitly typed. Do not rely on inference for public API surfaces.
- Use `readonly` on all object properties and array types that should not be mutated.

## React Conventions (React 19)
- All components are function components. No class components.
- Component files are PascalCase (`ResourceRequestWizard.tsx`). Utility and hook files are camelCase (`useSessionTimer.ts`).
- One component per file. Barrel `index.ts` files are allowed for re-exporting but must not contain logic.
- Props interfaces are defined in the same file as the component and named `{ComponentName}Props`.
- Use `React.FC<Props>` only when the component explicitly uses `children`. Otherwise, type the function directly: `function MyComponent(props: MyComponentProps): JSX.Element`.
- Keep components focused: a component should do one thing. Extract sub-components when a render function exceeds ~80 lines.
- In React 19, `ref` is a regular prop — do not use `forwardRef()` for new components. Pass `ref` directly in the props interface.
- Use the React Compiler (stable in React 19) for automatic memoization. Do not add `useMemo` or `useCallback` to new code — the compiler handles this. Only add manual memoization when profiling proves it necessary.
- Use the new `use()` hook to read promises and context inside components. Use `useActionState` and `useFormStatus` for form action state.
- Use `useOptimistic` for optimistic UI updates on mutations (e.g., status changes in the approval queue).

## State Management
- Use **TanStack Query v5** for all server state (API data, mutations, invalidation). Do not store server data in Zustand or local state.
- Use **Zustand** for global UI state (session context, form wizard step, idle timer). Keep stores small and single-purpose.
- Use `useState` and `useReducer` for local component state that does not need to be shared.
- Never store derived data in state. Compute it from existing state or query data.

## API Calls
- All API calls go through a centralised `src/api/client.ts` module that wraps `fetch` with base URL, credential handling, and error normalisation.
- Define typed API response interfaces in `src/api/types.ts` mirroring the backend Pydantic schemas.
- Use TanStack Query `useQuery` and `useMutation` hooks. Never call `fetch` directly from a component.
- Handle loading, error, and empty states explicitly in every component that fetches data. Do not render `undefined` silently.

## MUI v7 Conventions
- Use the `sx` prop for one-off style overrides on MUI v7 components. Use `styled()` from `@mui/material/styles` for reusable styled components. Do not use inline `style={}` objects.
- Prefer MUI theme tokens (`theme.spacing`, `theme.palette`) over hardcoded pixel values or hex colours.
- Always use MUI `Typography` component for text rendering. Do not use raw `<p>`, `<h1>` etc. except in markdown rendering contexts.
- Form fields use MUI `TextField` with `controller` from `react-hook-form`. Do not manage form state manually.
- MUI v7 uses the slot pattern for component customisation — use `slotProps` and `slots` instead of the deprecated `components` and `componentsProps` props.
- MUI v7 ships proper ESM — no special bundler config needed for tree-shaking.

## Forms
- All forms use **react-hook-form** with **Zod v4** schemas for validation. Define the Zod schema first; derive the TypeScript type with `z.infer<typeof schema>`.
- Validate on submit and on blur (not on every keystroke for performance). Show field-level error messages using `formState.errors`.
- Multi-step wizard state: store form values in Zustand across steps. Validate each step independently before advancing.
- Zod v4 has breaking changes to error message formats and strict mode behaviour from v3. Use `z.string().min(1)` (not `.nonempty()` which is removed in v4). Use `error.issues` instead of `error.errors` when handling `ZodError`.

## Routing
- Use React Router v6 with `createBrowserRouter` and `RouterProvider` (not the legacy `BrowserRouter` wrapper).
- Define all routes in a single `src/router.tsx` file. Use `lazy()` for page-level code splitting.
- Use `useNavigate()` for programmatic navigation. Never mutate `window.location` directly.
- Protected routes check session state from Zustand and redirect to `/login` if unauthenticated.

## Code Style
- Format with **Prettier** (default config, `"singleQuote": true`, `"trailingComma": "all"`).
- Lint with **ESLint** using `@typescript-eslint/recommended`, `react-hooks/recommended`, `jsx-a11y/recommended`.
- No `console.log` in committed code. Use a structured logger or remove debug statements before committing.
- Maximum line length: 100 characters (enforced via Prettier `printWidth`).
- Imports: React imports first, then third-party, then local. Use absolute imports from `src/` (configured in `tsconfig.json` `paths`).

## Accessibility
- All interactive elements must be keyboard accessible and have visible focus indicators.
- Use semantic HTML within MUI components. Set `aria-label` on icon buttons and controls without visible text labels.
- Form fields must have associated `<label>` elements (MUI `TextField` handles this automatically; verify for custom inputs).
- Colour is never the sole means of conveying information (e.g., status chips must have both colour and text/icon).

## Testing
- Use **Vitest** with `@testing-library/react` and `@testing-library/user-event`.
- Test behaviour, not implementation: query by role, label, or accessible name — not by CSS class or component internals.
- Mock API calls using **MSW (Mock Service Worker)** in integration tests.
- Aim for ≥70% branch coverage on all `src/pages/` and `src/components/` modules.
