import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge, BadgeDot, CountryBadge, TagBadge } from "./Badge";

describe("Badge system", () => {
  it("renders typed badges for runtime proxy and country metadata", () => {
    render(
      <div>
        <Badge type="runtime" tone="success">running</Badge>
        <Badge type="proxy" tone="info">Proxy</Badge>
        <Badge type="country" tone="neutral">US</Badge>
      </div>,
    );

    expect(screen.getByText("running").getAttribute("data-badge-type")).toBe("runtime");
    expect(screen.getByText("Proxy").getAttribute("data-badge-type")).toBe("proxy");
    expect(screen.getByText("US").getAttribute("data-badge-type")).toBe("country");
  });

  it("keeps custom tag tint while using readable text contrast", () => {
    render(<TagBadge tag="ready" color="#22c55e" />);

    const tag = screen.getByText("ready");
    expect(tag.getAttribute("data-badge-type")).toBe("tag");
    expect(tag.style.backgroundColor).toBe("rgba(34, 197, 94, 0.125)");
    expect(tag.style.borderColor).toBe("rgba(34, 197, 94, 0.28)");
    expect(tag.style.color).toBe("rgb(26, 127, 73)");
  });

  it("folds non-public country badge labels before rendering text or title evidence", () => {
    const leakMarker = "country-token-secret";
    render(
      <CountryBadge
        country={`US Authorization=Bearer ${leakMarker} token=${leakMarker} /data/country 203.0.113.88`}
      />,
    );

    const badge = screen.getByText("unknown");
    expect(badge.getAttribute("data-badge-type")).toBe("country");
    expect(badge.getAttribute("title")).toBe("unknown");
    expect(document.body.textContent).not.toContain(leakMarker);
    expect(document.body.textContent).not.toContain("Authorization");
    expect(document.body.textContent).not.toContain("Bearer");
    expect(document.body.textContent).not.toContain("token=");
    expect(document.body.textContent).not.toContain("/data/country");
    expect(document.body.textContent).not.toContain("203.0.113.88");
  });

  it("renders accessible dots for status-style badges", () => {
    const { container } = render(<BadgeDot tone="success" aria-label="Runtime running" pulse />);

    const dot = screen.getByLabelText("Runtime running");
    expect(dot.getAttribute("data-badge-dot")).toBe("success");
    expect(dot.getAttribute("data-pulse")).toBe("true");
    expect(container.querySelector(".animate-ping")).toBeTruthy();
  });
});
