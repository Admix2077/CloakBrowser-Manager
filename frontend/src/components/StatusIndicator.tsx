import { BadgeDot } from "./Badge";
import { publicRuntimeStatus } from "../lib/profileDisplay";

interface StatusIndicatorProps {
  status: unknown;
  size?: "sm" | "md";
}

export function StatusIndicator({ status, size = "sm" }: StatusIndicatorProps) {
  const sizeClass = size === "sm" ? "h-2 w-2" : "h-2.5 w-2.5";
  const publicStatus = publicRuntimeStatus(status);
  const isRunning = publicStatus === "running";

  return (
    <BadgeDot
      tone={isRunning ? "success" : "muted"}
      pulse={isRunning}
      className={sizeClass}
      aria-label={`Runtime ${publicStatus}`}
    />
  );
}
