import { BadgeDot } from "./Badge";

interface StatusIndicatorProps {
  status: "running" | "stopped";
  size?: "sm" | "md";
}

export function StatusIndicator({ status, size = "sm" }: StatusIndicatorProps) {
  const sizeClass = size === "sm" ? "h-2 w-2" : "h-2.5 w-2.5";
  const isRunning = status === "running";

  return (
    <BadgeDot
      tone={isRunning ? "success" : "muted"}
      pulse={isRunning}
      className={sizeClass}
      aria-label={`Runtime ${status}`}
    />
  );
}
