import { Search } from "lucide-react";
import type { ProfileFilterOptions, ProfileFilterState } from "../lib/filters";

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
  const labelled = (label: string) => labelPrefix ? `${labelPrefix} ${label}` : label;
  const showVisibleLabels = layout === "toolbar";

  return (
    <div
      role={layout === "toolbar" ? "toolbar" : undefined}
      aria-label={layout === "toolbar" ? "Profile filters" : undefined}
      className={layout === "toolbar" ? "grid grid-cols-2 gap-2 xl:grid-cols-[minmax(260px,1.4fr)_repeat(6,minmax(104px,128px))]" : "space-y-3"}
    >
      <div className={layout === "toolbar" ? "col-span-2 xl:col-span-1" : ""}>
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
            value={value.search}
            onChange={(event) => update("search", event.target.value)}
            className="input h-9 rounded-[6px] border-slate-200 bg-white/95 pl-8 text-xs shadow-[0_1px_1px_rgba(15,23,42,0.035),inset_0_1px_0_rgba(255,255,255,0.9)] ring-1 ring-slate-900/[0.02] hover:border-slate-300 focus:shadow-[0_0_0_3px_rgba(37,99,235,0.08)]"
          />
        </div>
      </div>

      <div className={layout === "toolbar" ? "contents" : "grid grid-cols-2 gap-2"}>
        <FilterSelect
          label={labelled("Runtime status")}
          visibleLabel="Runtime"
          showVisibleLabel={showVisibleLabels}
          value={value.status}
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
          onChange={(nextValue) => update("country", nextValue)}
          options={[
            ["all", "All countries"],
            ...options.countries.map((country) => [country, country] as const),
          ]}
        />
        <FilterSelect
          label={labelled("Tag filter")}
          visibleLabel="Tag"
          showVisibleLabel={showVisibleLabels}
          value={value.tag}
          onChange={(nextValue) => update("tag", nextValue)}
          options={[
            ["all", "All tags"],
            ...options.tags.map((tag) => [tag, tag] as const),
          ]}
        />
        <FilterSelect
          label={labelled("Sort profiles")}
          visibleLabel="Sort"
          showVisibleLabel={showVisibleLabels}
          value={value.sortBy}
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

interface FilterSelectProps {
  label: string;
  visibleLabel: string;
  showVisibleLabel: boolean;
  value: string;
  options: readonly (readonly [string, string])[];
  onChange: (value: string) => void;
}

function FilterSelect({ label, visibleLabel, showVisibleLabel, value, options, onChange }: FilterSelectProps) {
  const id = filterId(label);

  return (
    <div>
      <FilterLabel htmlFor={id} visible={showVisibleLabel}>{showVisibleLabel ? visibleLabel : label}</FilterLabel>
      <select
        id={id}
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 w-full rounded-[6px] border border-slate-200 bg-white/95 px-2.5 text-xs font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.035),inset_0_1px_0_rgba(255,255,255,0.9)] ring-1 ring-slate-900/[0.02] outline-none transition-colors hover:border-slate-300 focus:border-blue-500 focus:shadow-[0_0_0_3px_rgba(37,99,235,0.08)] focus:ring-2 focus:ring-blue-500/15"
      >
        {options.map(([optionValue, labelText]) => (
          <option key={optionValue} value={optionValue}>
            {labelText}
          </option>
        ))}
      </select>
    </div>
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
