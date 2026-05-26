import type { CSSProperties, ReactNode } from "react";

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger" | "muted";
type BadgeType = "health" | "runtime" | "proxy" | "country" | "tag";

const toneClassNames: Record<BadgeTone, string> = {
  neutral: "border-slate-200 bg-white text-slate-600",
  info: "border-blue-200 bg-blue-50 text-blue-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  danger: "border-red-200 bg-red-50 text-red-700",
  muted: "border-slate-200 bg-slate-50 text-slate-500",
};

const dotClassNames: Record<BadgeTone, string> = {
  neutral: "bg-slate-400",
  info: "bg-blue-500",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
  muted: "bg-slate-400",
};

interface BadgeProps {
  type: BadgeType;
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  title?: string;
  "aria-label"?: string;
}

export function Badge({
  type,
  tone = "neutral",
  children,
  className = "",
  style,
  title,
  "aria-label": ariaLabel,
}: BadgeProps) {
  return (
    <span
      data-badge-type={type}
      className={`inline-flex shrink-0 items-center gap-1 rounded-[6px] border px-1.5 py-0.5 text-[11px] font-medium leading-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] transition-[background-color,border-color,color,box-shadow,transform] duration-150 ${toneClassNames[tone]} ${className}`}
      style={style}
      title={title}
      aria-label={ariaLabel}
    >
      {children}
    </span>
  );
}

interface BadgeDotProps {
  tone: BadgeTone;
  pulse?: boolean;
  className?: string;
  "aria-label"?: string;
}

export function BadgeDot({
  tone,
  pulse = false,
  className = "",
  "aria-label": ariaLabel,
}: BadgeDotProps) {
  return (
    <span className="relative inline-flex">
      {pulse && (
        <span
          aria-hidden="true"
          className={`absolute inline-flex h-1.5 w-1.5 rounded-full ${dotClassNames[tone]} ${className} opacity-75 animate-ping`}
        />
      )}
      <span
        data-badge-dot={tone}
        data-pulse={pulse ? "true" : undefined}
        aria-label={ariaLabel}
        className={`relative inline-flex h-1.5 w-1.5 rounded-full ${dotClassNames[tone]} ${className}`}
      />
    </span>
  );
}

export function TagBadge({ tag, color }: { tag: string; color?: string | null }) {
  return (
    <Badge
      type="tag"
      tone="muted"
      className="max-w-full truncate"
      style={color ? { backgroundColor: `${color}20`, color } : undefined}
      title={tag}
    >
      {tag}
    </Badge>
  );
}

export function CountryBadge({ country }: { country: string }) {
  return (
    <Badge type="country" tone="neutral" className="font-semibold uppercase" title={country}>
      {country}
    </Badge>
  );
}

export function ProxyBadge() {
  return (
    <Badge type="proxy" tone="info">
      Proxy
    </Badge>
  );
}
