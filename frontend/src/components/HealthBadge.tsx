import type { ProfileHealthResponse } from "../lib/api";
import {
  getHealthAriaLabel,
  getHealthLabel,
  getHealthTone,
  getHealthWarningSummary,
} from "../lib/health";
import { Badge, BadgeDot } from "./Badge";

interface HealthBadgeProps {
  health?: ProfileHealthResponse | null;
  compact?: boolean;
}

export function HealthBadge({ health, compact = false }: HealthBadgeProps) {
  const tone = getHealthTone(health?.status);
  const label = getHealthLabel(health?.status);
  const ariaLabel = getHealthAriaLabel(health);
  const summary = getHealthWarningSummary(health);
  const badgeTone = health?.status === "good"
    ? "success"
    : health?.status === "warning"
      ? "warning"
      : health?.status === "error"
        ? "danger"
        : "muted";

  return (
    <span className="inline-flex max-w-full items-center gap-1.5">
      <Badge
        type="health"
        tone={badgeTone}
        className={tone.badgeClassName}
        aria-label={ariaLabel}
        title={summary ?? ariaLabel}
      >
        <BadgeDot tone={badgeTone} className={tone.dotClassName} />
        <span>{label}</span>
      </Badge>
      {!compact && summary && (
        <span className={`truncate text-xs ${tone.summaryClassName}`} title={summary}>
          {summary}
        </span>
      )}
    </span>
  );
}
