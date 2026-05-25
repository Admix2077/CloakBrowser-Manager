import type { ProfileHealthResponse } from "../lib/api";
import {
  getHealthAriaLabel,
  getHealthLabel,
  getHealthTone,
  getHealthWarningSummary,
} from "../lib/health";

interface HealthBadgeProps {
  health?: ProfileHealthResponse | null;
  compact?: boolean;
}

export function HealthBadge({ health, compact = false }: HealthBadgeProps) {
  const tone = getHealthTone(health?.status);
  const label = getHealthLabel(health?.status);
  const ariaLabel = getHealthAriaLabel(health);
  const summary = getHealthWarningSummary(health);

  return (
    <span className="inline-flex max-w-full items-center gap-1.5">
      <span
        className={`inline-flex shrink-0 items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium leading-4 ${tone.badgeClassName}`}
        aria-label={ariaLabel}
        title={summary ?? ariaLabel}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${tone.dotClassName}`} />
        <span>{label}</span>
      </span>
      {!compact && summary && (
        <span className={`truncate text-xs ${tone.summaryClassName}`} title={summary}>
          {summary}
        </span>
      )}
    </span>
  );
}
