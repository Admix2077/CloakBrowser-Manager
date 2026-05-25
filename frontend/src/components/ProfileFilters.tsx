import { Search } from "lucide-react";
import type { ProfileFilterOptions, ProfileFilterState } from "../lib/filters";

interface ProfileFiltersProps {
  value: ProfileFilterState;
  options: ProfileFilterOptions;
  onChange: (value: ProfileFilterState) => void;
}

export function ProfileFilters({ value, options, onChange }: ProfileFiltersProps) {
  const update = <K extends keyof ProfileFilterState>(key: K, nextValue: ProfileFilterState[K]) => {
    onChange({ ...value, [key]: nextValue });
  };

  return (
    <div className="space-y-2">
      <label className="sr-only" htmlFor="profile-search">Search profiles</label>
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-500" />
        <input
          id="profile-search"
          type="text"
          placeholder="Search profiles..."
          value={value.search}
          onChange={(event) => update("search", event.target.value)}
          className="input pl-8 py-1.5 text-xs"
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <FilterSelect
          label="Runtime status"
          value={value.status}
          onChange={(nextValue) => update("status", nextValue as ProfileFilterState["status"])}
          options={[
            ["all", "All runtime"],
            ["running", "Running"],
            ["stopped", "Stopped"],
          ]}
        />
        <FilterSelect
          label="Health status"
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
          label="Proxy filter"
          value={value.proxy}
          onChange={(nextValue) => update("proxy", nextValue as ProfileFilterState["proxy"])}
          options={[
            ["all", "All proxy"],
            ["with_proxy", "With proxy"],
            ["without_proxy", "No proxy"],
          ]}
        />
        <FilterSelect
          label="Country filter"
          value={value.country}
          onChange={(nextValue) => update("country", nextValue)}
          options={[
            ["all", "All countries"],
            ...options.countries.map((country) => [country, country] as const),
          ]}
        />
        <FilterSelect
          label="Tag filter"
          value={value.tag}
          onChange={(nextValue) => update("tag", nextValue)}
          options={[
            ["all", "All tags"],
            ...options.tags.map((tag) => [tag, tag] as const),
          ]}
        />
        <FilterSelect
          label="Sort profiles"
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
  const id = `profile-filter-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

  return (
    <div>
      <label className="sr-only" htmlFor={id}>{label}</label>
      <select
        id={id}
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-8 w-full rounded-md border border-border bg-surface-2 px-2 text-xs text-gray-200 outline-none transition-colors focus:border-accent focus:ring-1 focus:ring-accent/50"
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
