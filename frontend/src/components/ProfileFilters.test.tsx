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
});
