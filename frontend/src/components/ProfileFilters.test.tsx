import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfileFilters } from "./ProfileFilters";
import type { ProfileFilterState, ProfileFilterOptions } from "../lib/filters";

const value: ProfileFilterState = {
  search: "",
  status: "all",
  health: "all",
  proxy: "all",
  country: "all",
  tag: "all",
  sortBy: "health",
};

const options: ProfileFilterOptions = {
  countries: ["JP", "US"],
  tags: ["client-a", "warmup"],
};

describe("ProfileFilters", () => {
  it("emits filter changes from compact operations controls", () => {
    const onChange = vi.fn();

    render(
      <ProfileFilters
        value={value}
        options={options}
        onChange={onChange}
      />,
    );

    fireEvent.change(screen.getByLabelText("Search profiles"), {
      target: { value: "seller" },
    });
    expect(onChange).toHaveBeenLastCalledWith({ ...value, search: "seller" });

    fireEvent.change(screen.getByLabelText("Runtime status"), {
      target: { value: "running" },
    });
    expect(onChange).toHaveBeenLastCalledWith({ ...value, status: "running" });

    fireEvent.change(screen.getByLabelText("Health status"), {
      target: { value: "warning" },
    });
    expect(onChange).toHaveBeenLastCalledWith({ ...value, health: "warning" });

    fireEvent.change(screen.getByLabelText("Proxy filter"), {
      target: { value: "with_proxy" },
    });
    expect(onChange).toHaveBeenLastCalledWith({ ...value, proxy: "with_proxy" });

    fireEvent.change(screen.getByLabelText("Country filter"), {
      target: { value: "JP" },
    });
    expect(onChange).toHaveBeenLastCalledWith({ ...value, country: "JP" });

    fireEvent.change(screen.getByLabelText("Tag filter"), {
      target: { value: "warmup" },
    });
    expect(onChange).toHaveBeenLastCalledWith({ ...value, tag: "warmup" });

    fireEvent.change(screen.getByLabelText("Sort profiles"), {
      target: { value: "last_checked" },
    });
    expect(onChange).toHaveBeenLastCalledWith({ ...value, sortBy: "last_checked" });
  });

  it("exposes the main filter strip as a toolbar in operations layout", () => {
    render(
      <ProfileFilters
        value={value}
        options={options}
        onChange={vi.fn()}
        layout="toolbar"
      />,
    );

    expect(screen.getByRole("toolbar", { name: "Profile filters" })).toBeTruthy();
  });

  it("marks active toolbar controls for faster operations scanning", () => {
    render(
      <ProfileFilters
        value={{
          ...value,
          search: "seller",
          status: "running",
          tag: "warmup",
        }}
        options={options}
        onChange={vi.fn()}
        layout="toolbar"
      />,
    );

    expect(screen.getByLabelText("Search profiles").closest("[data-filter-control]")?.getAttribute("data-active")).toBe("true");
    expect(screen.getByLabelText("Runtime status").closest("[data-filter-control]")?.getAttribute("data-active")).toBe("true");
    expect(screen.getByLabelText("Tag filter").closest("[data-filter-control]")?.getAttribute("data-active")).toBe("true");
    expect(screen.getByLabelText("Country filter").closest("[data-filter-control]")?.getAttribute("data-active")).toBe("false");
  });

  it("redacts tag option labels without changing submitted filter values", () => {
    const leakMarker = "profile-filter-tag-secret";
    const rawTag =
      "warm Authorization=Bearer " +
      `${leakMarker} token=${leakMarker} /data/filter-tag-secret 203.0.113.90`;
    const safeTag = "warm [redacted] [redacted] [redacted-path] [redacted-ip]";
    const onChange = vi.fn();

    render(
      <ProfileFilters
        value={value}
        options={{ countries: [], tags: [rawTag] }}
        onChange={onChange}
      />,
    );

    const option = screen.getByRole("option", { name: safeTag }) as HTMLOptionElement;
    expect(option.value).toBe(rawTag);
    expect(document.body.textContent).not.toContain(leakMarker);
    expect(document.body.textContent).not.toContain("Authorization");
    expect(document.body.textContent).not.toContain("Bearer");
    expect(document.body.textContent).not.toContain("token=");
    expect(document.body.textContent).not.toContain("/data/filter-tag-secret");
    expect(document.body.textContent).not.toContain("203.0.113.90");

    fireEvent.change(screen.getByLabelText("Tag filter"), {
      target: { value: rawTag },
    });
    expect(onChange).toHaveBeenLastCalledWith({ ...value, tag: rawTag });
  });
});
