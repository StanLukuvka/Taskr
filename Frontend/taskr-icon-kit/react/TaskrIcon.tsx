import type { SVGProps } from "react";

export type TaskrIconName =
  | "taskr"
  | "hermes"
  | "api"
  | "foreach"
  | "question"
  | "budget"
  | "result"
  | "run";

type IconProps = SVGProps<SVGSVGElement> & {
  name: TaskrIconName;
  title?: string;
};

/**
 * Uses the external SVG sprite at /taskr-icons.svg.
 * Put taskr-icons.svg in your app's public/ directory.
 */
export function TaskrIcon({
  name,
  title,
  className,
  ...props
}: IconProps) {
  const labelled = Boolean(title);

  return (
    <svg
      viewBox="0 0 64 64"
      className={className}
      role={labelled ? "img" : undefined}
      aria-hidden={labelled ? undefined : true}
      aria-label={title}
      {...props}
    >
      {title ? <title>{title}</title> : null}
      <use href={`/taskr-icons.svg#icon-${name}`} />
    </svg>
  );
}

type BadgeProps = {
  name: TaskrIconName;
  size?: "small" | "normal" | "large";
  title?: string;
  className?: string;
};

export function TaskrIconBadge({
  name,
  size = "normal",
  title,
  className = "",
}: BadgeProps) {
  const sizeClass =
    size === "small"
      ? " taskr-icon--small"
      : size === "large"
        ? " taskr-icon--large"
        : "";

  return (
    <span
      className={`taskr-icon taskr-icon--${name}${sizeClass} ${className}`.trim()}
      title={title}
    >
      <TaskrIcon name={name} />
    </span>
  );
}
