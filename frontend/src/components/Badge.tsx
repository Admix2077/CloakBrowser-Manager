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
      style={getAccessibleTagStyle(color)}
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

function getAccessibleTagStyle(color?: string | null): CSSProperties | undefined {
  const rgb = parseHexColor(color);
  if (!rgb) return undefined;

  const background = blend(rgb, WHITE, 0.125);
  const text = getReadableTextColor(rgb, background);

  return {
    backgroundColor: `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.125)`,
    borderColor: `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.28)`,
    color: `rgb(${text.r}, ${text.g}, ${text.b})`,
  };
}

const WHITE = { r: 255, g: 255, b: 255 };
const SLATE_950 = { r: 15, g: 23, b: 42 };

function parseHexColor(color?: string | null): { r: number; g: number; b: number } | null {
  if (!color) return null;
  const normalized = color.trim().replace(/^#/, "");
  const expanded = normalized.length === 3
    ? normalized.split("").map((char) => char + char).join("")
    : normalized;
  if (!/^[0-9a-fA-F]{6}$/.test(expanded)) return null;

  return {
    r: Number.parseInt(expanded.slice(0, 2), 16),
    g: Number.parseInt(expanded.slice(2, 4), 16),
    b: Number.parseInt(expanded.slice(4, 6), 16),
  };
}

function getReadableTextColor(
  color: { r: number; g: number; b: number },
  background: { r: number; g: number; b: number },
): { r: number; g: number; b: number } {
  if (contrastRatio(color, background) >= 4.5) return color;

  for (let amount = 0.15; amount <= 1; amount += 0.05) {
    const candidate = mix(color, SLATE_950, amount);
    if (contrastRatio(candidate, background) >= 4.5) return candidate;
  }

  return SLATE_950;
}

function blend(
  foreground: { r: number; g: number; b: number },
  background: { r: number; g: number; b: number },
  alpha: number,
): { r: number; g: number; b: number } {
  return {
    r: Math.round(foreground.r * alpha + background.r * (1 - alpha)),
    g: Math.round(foreground.g * alpha + background.g * (1 - alpha)),
    b: Math.round(foreground.b * alpha + background.b * (1 - alpha)),
  };
}

function mix(
  from: { r: number; g: number; b: number },
  to: { r: number; g: number; b: number },
  amount: number,
): { r: number; g: number; b: number } {
  return {
    r: Math.round(from.r + (to.r - from.r) * amount),
    g: Math.round(from.g + (to.g - from.g) * amount),
    b: Math.round(from.b + (to.b - from.b) * amount),
  };
}

function contrastRatio(
  foreground: { r: number; g: number; b: number },
  background: { r: number; g: number; b: number },
): number {
  const foregroundLuminance = luminance(foreground);
  const backgroundLuminance = luminance(background);
  return (Math.max(foregroundLuminance, backgroundLuminance) + 0.05)
    / (Math.min(foregroundLuminance, backgroundLuminance) + 0.05);
}

function luminance({ r, g, b }: { r: number; g: number; b: number }): number {
  return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b);
}

function srgb(value: number): number {
  const channel = value / 255;
  return channel <= 0.03928
    ? channel / 12.92
    : ((channel + 0.055) / 1.055) ** 2.4;
}
