import { Search } from "lucide-react";
import type { ReactNode } from "react";
import { publicProfileGeoipLabel, publicProfileTagLabel } from "../lib/errorDisplay";
import { publicProfileSearchInput, type ProfileFilterOptions, type ProfileFilterState } from "../lib/filters";

interface ProfileFiltersProps {
  value: ProfileFilterState;
  options: ProfileFilterOptions;
  onChange: (value: ProfileFilterState) => void;
  layout?: "rail" | "toolbar";
  labelPrefix?: string;
}

export function ProfileFilters({
  value,
  options,
  onChange,
  layout = "rail",
  labelPrefix = "",
}: ProfileFiltersProps) {
  const update = <K extends keyof ProfileFilterState>(key: K, nextValue: ProfileFilterState[K]) => {
    onChange({ ...value, [key]: nextValue });
  };
  const publicSearch = publicProfileSearchInput(value.search);
  const labelled = (label: string) => labelPrefix ? `${labelPrefix} ${label}` : label;
  const showVisibleLabels = layout === "toolbar";
  const isToolbar = layout === "toolbar";

  return (
    <div
      role={isToolbar ? "toolbar" : undefined}
      aria-label={isToolbar ? "Profile filters" : undefined}
      className={isToolbar ? "grid grid-cols-2 gap-2 xl:grid-cols-[minmax(260px,1.4fr)_repeat(6,minmax(104px,128px))]" : "space-y-3"}
    >
      <FilterControl
        filter="search"
        active={value.search.trim().length > 0}
        className={isToolbar ? "col-span-2 xl:col-span-1" : ""}
      >
        <FilterLabel htmlFor={filterId(labelled("Search profiles"))} visible={showVisibleLabels}>
          {showVisibleLabels ? "Search" : labelled("Search profiles")}
        </FilterLabel>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            id={filterId(labelled("Search profiles"))}
            aria-label={labelled("Search profiles")}
            type="text"
            placeholder="Search profiles..."
            value={publicSearch}
            onChange={(event) => update("search", publicProfileSearchInput(event.target.value))}
            className="input h-9 rounded-[7px] border-slate-200 bg-white pl-8 text-xs shadow-none ring-0 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:shadow-[0_0_0_3px_rgba(37,99,235,0.08)]"
          />
        </div>
      </FilterControl>

      <div className={isToolbar ? "contents" : "grid grid-cols-2 gap-2"}>
        <FilterSelect
          label={labelled("Runtime status")}
          visibleLabel="Runtime"
          showVisibleLabel={showVisibleLabels}
          value={value.status}
          active={value.status !== "all"}
          onChange={(nextValue) => update("status", nextValue as ProfileFilterState["status"])}
          options={[
            ["all", "All runtime"],
            ["running", "Running"],
            ["stopped", "Stopped"],
          ]}
        />
        <FilterSelect
          label={labelled("Health status")}
          visibleLabel="Health"
          showVisibleLabel={showVisibleLabels}
          value={value.health}
          active={value.health !== "all"}
          onChange={(nextValue) => update("health", nextValue as ProfileFilterState["health"])}
          options={[
            ["all", "All health"],
            ["error", "不可用"],
            ["warning", "需关注"],
            ["unknown", "未检测"],
            ["good", "可继续"],
          ]}
        />
        <FilterSelect
          label={labelled("Proxy filter")}
          visibleLabel="Proxy"
          showVisibleLabel={showVisibleLabels}
          value={value.proxy}
          active={value.proxy !== "all"}
          onChange={(nextValue) => update("proxy", nextValue as ProfileFilterState["proxy"])}
          options={[
            ["all", "All proxy"],
            ["with_proxy", "With proxy"],
            ["without_proxy", "No proxy"],
          ]}
        />
        <FilterSelect
          label={labelled("Country filter")}
          visibleLabel="Country"
          showVisibleLabel={showVisibleLabels}
          value={value.country}
          active={value.country !== "all"}
          onChange={(nextValue) => update("country", nextValue)}
          options={[
            ["all", "All countries"],
            ...options.countries.map((country) => {
              const label = publicProfileGeoipLabel(country);
              return [label, label] as const;
            }),
          ]}
        />
        <FilterSelect
          label={labelled("Tag filter")}
          visibleLabel="Tag"
          showVisibleLabel={showVisibleLabels}
          value={value.tag}
          active={value.tag !== "all"}
          onChange={(nextValue) => update("tag", nextValue)}
          options={[
            ["all", "All tags"],
            ...options.tags.map((tag) => {
              const label = publicProfileTagLabel(tag);
              return [label, label] as const;
            }),
          ]}
        />
        <FilterSelect
          label={labelled("Sort profiles")}
          visibleLabel="Sort"
          showVisibleLabel={showVisibleLabels}
          value={value.sortBy}
          active={value.sortBy !== "health"}
          onChange={(nextValue) => update("sortBy", nextValue as ProfileFilterState["sortBy"])}
          options={[
            ["health", "Risk first"],
            ["last_checked", "Last checked"],
            ["name", "Name"],
            ["status", "Runtime"],
            ["country", "Country"],
          ]}
        />
      </div>
    </div>
  );
}

function FilterControl({
  filter,
  active,
  className = "",
  children,
}: {
  filter: string;
  active: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      data-filter-control={filter}
      data-active={active ? "true" : "false"}
      className={`${className} rounded-[9px] transition-colors data-[active=true]:bg-blue-50/45 data-[active=true]:ring-1 data-[active=true]:ring-blue-500/10`}
    >
      {children}
    </div>
  );
}

interface FilterSelectProps {
  label: string;
  visibleLabel: string;
  showVisibleLabel: boolean;
  value: string;
  active: boolean;
  options: readonly (readonly [string, string])[];
  onChange: (value: string) => void;
}

function FilterSelect({ label, visibleLabel, showVisibleLabel, value, active, options, onChange }: FilterSelectProps) {
  const id = filterId(label);

  return (
    <FilterControl filter={visibleLabel.toLowerCase()} active={active}>
      <FilterLabel htmlFor={id} visible={showVisibleLabel}>{showVisibleLabel ? visibleLabel : label}</FilterLabel>
      <select
        id={id}
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`h-9 w-full rounded-[7px] border bg-white px-2.5 text-xs font-medium outline-none transition-[border-color,background-color,box-shadow] hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/15 ${
          active
            ? "border-blue-200 text-blue-900 shadow-[inset_3px_0_0_rgba(37,99,235,0.36)]"
            : "border-slate-200 text-slate-700"
        }`}
      >
        {options.map(([optionValue, labelText]) => (
          <option key={optionValue} value={optionValue}>
            {labelText}
          </option>
        ))}
      </select>
    </FilterControl>
  );
}

function FilterLabel({ htmlFor, visible, children }: { htmlFor: string; visible: boolean; children: string }) {
  return (
    <label
      className={visible ? "mb-1 block text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500" : "sr-only"}
      htmlFor={htmlFor}
    >
      {children}
    </label>
  );
}

function filterId(label: string): string {
  return `profile-filter-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}
