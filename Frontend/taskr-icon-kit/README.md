# Taskr Frontend Icon Kit

A small framework-agnostic SVG icon set for decorating the Taskr frontend.

## Included

```text
icons/
  taskr.svg
  hermes.svg
  api.svg
  foreach.svg
  question.svg
  budget.svg
  result.svg
  run.svg

favicon.svg
taskr-icons.svg       SVG sprite containing every icon
taskr-icons.css       badge and semantic colour classes
preview.html          visual inspection page
usage-snippet.html    plain HTML example
react/TaskrIcon.tsx   optional React helper
```

## Recommended usage

- Use `taskr.svg` as the custom Taskr brand/application mark.
- Use `favicon.svg` as the browser favicon.
- Use `hermes.svg` for Hermes. It is a fixed geometric rendering of the `☤` symbol, so it does not vary between operating systems.
- Use the remaining SVGs for generic frontend concepts.
- Keep product images, generated diagrams and agent portraits as raster imagery. These interface icons should remain SVG.

## Fastest integration

Copy these files into the frontend:

```text
public/taskr-icons.svg
public/favicon.svg
src/styles/taskr-icons.css
src/components/TaskrIcon.tsx
```

In `index.html`:

```html
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
```

In the application stylesheet:

```css
@import "./styles/taskr-icons.css";
```

React:

```tsx
import { TaskrIconBadge } from "./components/TaskrIcon";

<TaskrIconBadge name="hermes" title="Hermes task" />
<TaskrIconBadge name="api" title="API execution" />
<TaskrIconBadge name="foreach" title="Foreach loop" />
```

Plain HTML:

```html
<span class="taskr-icon taskr-icon--api" aria-label="API execution">
  <svg viewBox="0 0 64 64" aria-hidden="true">
    <use href="/taskr-icons.svg#icon-api"></use>
  </svg>
</span>
```

## Semantic colours

| Icon | Meaning | Default colour |
|---|---|---|
| Taskr | Taskr-owned state / application mark | amber |
| Hermes | Hermes agent work | purple |
| API | deterministic external execution | blue |
| Foreach | list iteration | yellow |
| Question | human decision | amber |
| Budget | spending or credit policy | green |
| Result | resolved output | green |
| Run | active execution | cyan |

The icons use `currentColor`, so the colours are easy to override.

## Accessibility

Decorative icons should use `aria-hidden="true"`.

Meaningful standalone icons should receive an accessible label or visible text. Do not use colour alone to communicate state.

## Notes

The set deliberately avoids neon glow and raster backgrounds. The generated icon board is a visual reference, while these SVGs are the actual implementation assets.
