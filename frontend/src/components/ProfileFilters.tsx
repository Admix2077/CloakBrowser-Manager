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

  return (
    <div className={layout === "toolbar" ? "grid grid-cols-2 gap-2 lg:grid-cols-[minmax(220px,1fr)_repeat(6,minmax(106px,136px))]" : "space-y-2"}>
      <label className="sr-only" htmlFor={filterId(labelled("Search profiles"))}>
        {labelled("Search profiles")}
      </label>
      <div className={layout === "toolbar" ? "relative col-span-2 lg:col-span-1" : "relative"}>
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
        <input
          id={filterId(labelled("Search profiles"))}
          aria-label={labelled("Search profiles")}
          type="text"
          placeholder="Search profiles..."
          value={value.search}
          onChange={(event) => update("search", event.target.value)}
          className="input pl-8 py-1.5 text-xs"
        />
      </div>

      <div className={layout === "toolbar" ? "contents" : "grid grid-cols-2 gap-2"}>
        <FilterSelect
          label={labelled("Runtime status")}
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
          value={value.country}
          onChange={(nextValue) => update("country", nextValue)}
          options={[
            ["all", "All countries"],
            ...options.countries.map((country) => [country, country] as const),
          ]}
        />
        <FilterSelect
          label={labelled("Tag filter")}
          value={value.tag}
          onChange={(nextValue) => update("tag", nextValue)}
          options={[
            ["all", "All tags"],
            ...options.tags.map((tag) => [tag, tag] as const),
          ]}
        />
        <FilterSelect
          label={labelled("Sort profiles")}
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
  value: string;
  options: readonly (readonly [string, string])[];
  onChange: (value: string) => void;
}

function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  const id = filterId(label);

  return (
    <div>
      <label className="sr-only" htmlFor={id}>{label}</label>
      <select
        id={id}
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 w-full rounded-lg border border-border bg-surface-1 px-2.5 text-xs font-medium text-slate-700 shadow-hairline outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/15"
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

function filterId(label: string): string {
  return `profile-filter-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}
