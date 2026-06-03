import { Dices, Fingerprint, Monitor, MousePointer2, Network, Save, SlidersHorizontal, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { Profile, ProfileCreateData, ProfileTemplate } from "../lib/api";
import { publicProfileName } from "../lib/errorDisplay";
import { ConfirmDialog } from "./ConfirmDialog";

interface ProfileFormProps {
  profile: Profile | null; // null = create mode
  templates?: ProfileTemplate[];
  onSave: (data: ProfileCreateData) => Promise<void>;
  onDelete?: () => Promise<void>;
  onCancel: () => void;
}

const RESOLUTION_PRESETS: Record<string, { width: number; height: number }> = {
  "1920 × 1080 (Full HD)": { width: 1920, height: 1080 },
  "2560 × 1440 (QHD)": { width: 2560, height: 1440 },
  "1366 × 768 (HD)": { width: 1366, height: 768 },
  "1440 × 900": { width: 1440, height: 900 },
  "1536 × 864": { width: 1536, height: 864 },
  "1280 × 720 (720p)": { width: 1280, height: 720 },
};

const TAG_COLORS = [
  "#6366f1", // indigo
  "#22c55e", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#06b6d4", // cyan
  "#a855f7", // purple
  "#f97316", // orange
  "#ec4899", // pink
];

const GPU_PRESETS: Record<string, { vendor: string; renderer: string }> = {
  "NVIDIA RTX 3070": {
    vendor: "Google Inc. (NVIDIA)",
    renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 (0x00002484) Direct3D11 vs_5_0 ps_5_0, D3D11)",
  },
  "NVIDIA RTX 4070": {
    vendor: "Google Inc. (NVIDIA)",
    renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 (0x00002786) Direct3D11 vs_5_0 ps_5_0, D3D11)",
  },
  "AMD RX 6800 XT": {
    vendor: "Google Inc. (AMD)",
    renderer: "ANGLE (AMD, AMD Radeon RX 6800 XT (0x000073BF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
  },
  "Intel UHD 770": {
    vendor: "Google Inc. (Intel)",
    renderer: "ANGLE (Intel, Intel(R) UHD Graphics 770 (0x00004680) Direct3D11 vs_5_0 ps_5_0, D3D11)",
  },
  "Apple M3 (macOS)": {
    vendor: "Google Inc. (Apple)",
    renderer: "ANGLE (Apple, ANGLE Metal Renderer: Apple M3, Unspecified Version)",
  },
};

type ProfileFormSectionId = "identity" | "network" | "device" | "behavior" | "advanced";

const PROFILE_FORM_SECTIONS: Array<{
  id: ProfileFormSectionId;
  label: string;
  Icon: typeof Fingerprint;
}> = [
  { id: "identity", label: "Identity", Icon: Fingerprint },
  { id: "network", label: "Network", Icon: Network },
  { id: "device", label: "Device", Icon: Monitor },
  { id: "behavior", label: "Behavior", Icon: MousePointer2 },
  { id: "advanced", label: "Advanced", Icon: SlidersHorizontal },
];

export function ProfileForm({ profile, templates = [], onSave, onDelete, onCancel }: ProfileFormProps) {
  const isEdit = profile !== null;

  const [form, setForm] = useState<ProfileCreateData>({
    name: "",
    platform: "windows",
    screen_width: 1920,
    screen_height: 1080,
    humanize: false,
    human_preset: "default",
    headless: false,
    geoip: true,
    clipboard_sync: true,
    auto_launch: false,
    launch_args: [],
    tags: [],
  });

  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [tagInput, setTagInput] = useState("");
  const [tagColor, setTagColor] = useState<string | null>("#6366f1");
  const [launchArgInput, setLaunchArgInput] = useState("");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<ProfileFormSectionId>("identity");

  const applyTemplate = (templateId: string) => {
    if (!templateId) {
      set("template_id", null);
      return;
    }

    const template = templates.find((item) => item.id === templateId);
    if (!template) return;

    setForm((prev) => ({
      ...prev,
      template_id: template.id,
      platform: template.platform,
      screen_width: template.screen_width,
      screen_height: template.screen_height,
      gpu_vendor: template.gpu_vendor,
      gpu_renderer: template.gpu_renderer,
      hardware_concurrency: template.hardware_concurrency,
      color_scheme: template.color_scheme,
      humanize: template.humanize,
      human_preset: template.human_preset,
      launch_args: [...template.launch_args],
      geoip: template.geoip,
    }));
  };

  useEffect(() => {
    if (profile) {
      setForm({
        name: profile.name,
        fingerprint_seed: profile.fingerprint_seed,
        proxy: profile.proxy,
        timezone: profile.timezone,
        locale: profile.locale,
        platform: profile.platform,
        user_agent: profile.user_agent,
        screen_width: profile.screen_width,
        screen_height: profile.screen_height,
        gpu_vendor: profile.gpu_vendor,
        gpu_renderer: profile.gpu_renderer,
        hardware_concurrency: profile.hardware_concurrency,
        humanize: profile.humanize,
        human_preset: profile.human_preset,
        headless: profile.headless,
        geoip: profile.geoip,
        clipboard_sync: profile.clipboard_sync,
        auto_launch: profile.auto_launch,
        color_scheme: profile.color_scheme,
        launch_args: profile.launch_args ?? [],
        notes: profile.notes,
        tags: profile.tags ?? [],
        template_id: null,
      });
    }
    setActiveSection("identity");
  }, [profile?.id]);

  const set = <K extends keyof ProfileCreateData>(key: K, value: ProfileCreateData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    setDeleting(true);
    try {
      await onDelete();
      setDeleteConfirmOpen(false);
    } finally {
      setDeleting(false);
    }
  };

  const applyGpuPreset = (name: string) => {
    const preset = GPU_PRESETS[name];
    if (preset) {
      set("gpu_vendor", preset.vendor);
      set("gpu_renderer", preset.renderer);
    }
  };

  const randomizeSeed = () => {
    set("fingerprint_seed", Math.floor(Math.random() * 90000) + 10000);
  };

  const currentResolution = Object.entries(RESOLUTION_PRESETS).find(
    ([, v]) => v.width === form.screen_width && v.height === form.screen_height,
  )?.[0] ?? "custom";

  const addTag = () => {
    const tag = tagInput.trim();
    if (!tag) return;
    if (form.tags?.some((t) => t.tag === tag)) return;
    set("tags", [...(form.tags ?? []), { tag, color: tagColor }]);
    setTagInput("");
  };

  const removeTag = (tag: string) => {
    set("tags", (form.tags ?? []).filter((t) => t.tag !== tag));
  };

  const addLaunchArg = () => {
    const arg = launchArgInput.trim();
    if (!arg) return;
    if ((form.launch_args ?? []).includes(arg)) return;
    set("launch_args", [...(form.launch_args ?? []), arg]);
    setLaunchArgInput("");
  };

  const removeLaunchArg = (idx: number) => {
    set("launch_args", (form.launch_args ?? []).filter((_, i) => i !== idx));
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-4xl p-4 sm:p-6">
      <div className="mb-5 rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-hairline ring-1 ring-slate-900/[0.02] sm:flex sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="truncate text-lg font-semibold text-slate-950">
            {isEdit ? "Edit Profile" : "New Profile"}
          </h2>
          {isEdit && onDelete && (
            <button
              type="button"
              onClick={() => setDeleteConfirmOpen(true)}
              disabled={deleting}
              className="btn-danger flex items-center gap-1.5"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>{deleting ? "Deleting..." : "Delete"}</span>
            </button>
          )}
        </div>
        <div className="mt-3 flex items-center gap-2 sm:mt-0">
          <button type="button" onClick={onCancel} className="btn-secondary">
            Cancel
          </button>
          <button type="submit" disabled={saving} className="btn-primary flex items-center gap-1.5">
            <Save className="h-3.5 w-3.5" />
            <span>{saving ? "Saving..." : isEdit ? "Save" : "Create"}</span>
          </button>
        </div>
      </div>

      <div
        role="tablist"
        aria-label="Profile settings sections"
        className="mb-5 flex gap-1 overflow-x-auto rounded-lg border border-slate-200 bg-white p-1 shadow-hairline"
      >
        {PROFILE_FORM_SECTIONS.map(({ id, label, Icon }) => {
          const selected = activeSection === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              id={`profile-form-tab-${id}`}
              aria-selected={selected}
              aria-controls={`profile-form-panel-${id}`}
              onClick={() => setActiveSection(id)}
              className={`inline-flex h-9 min-w-max items-center gap-1.5 rounded-[7px] px-3 text-xs font-semibold transition-[background-color,color,box-shadow,transform] duration-150 ease-out active:translate-y-px focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/20 ${
                selected
                  ? "bg-slate-950 text-white shadow-[0_1px_2px_rgba(15,23,42,0.16)]"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-950"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      <div className="space-y-4">
        {activeSection === "identity" && (
        <section
          id="profile-form-panel-identity"
          role="tabpanel"
          aria-labelledby="profile-form-tab-identity"
          className="form-section animate-console-section-in"
        >
          <h3 className="section-title">Identity</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {!isEdit && templates.length > 0 && (
              <div className="sm:col-span-2">
                <label className="label" htmlFor="profile-template">Profile template</label>
                <select
                  id="profile-template"
                  className="input"
                  value={form.template_id ?? ""}
                  onChange={(e) => applyTemplate(e.target.value)}
                >
                  <option value="">Blank profile</option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {publicProfileName(template.name)}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div className="sm:col-span-2">
              <label className="label" htmlFor="profile-name">Profile Name</label>
              <input
                id="profile-name"
                className="input"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="e.g. Amazon Seller #1"
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="profile-fingerprint-seed">Fingerprint Seed</label>
              <div className="flex gap-2">
                <input
                  id="profile-fingerprint-seed"
                  className="input flex-1 no-spin"
                  type="number"
                  value={form.fingerprint_seed ?? ""}
                  onChange={(e) => set("fingerprint_seed", e.target.value ? Number(e.target.value) : null)}
                  placeholder="Auto (random)"
                />
                <button
                  type="button"
                  onClick={randomizeSeed}
                  className="btn-secondary px-2.5"
                  title="Randomize seed"
                >
                  <Dices className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </section>
        )}

        {activeSection === "network" && (
        <section
          id="profile-form-panel-network"
          role="tabpanel"
          aria-labelledby="profile-form-tab-network"
          className="form-section animate-console-section-in"
        >
          <h3 className="section-title">Network</h3>
          <div className="space-y-3">
            <div>
              <label className="label" htmlFor="profile-proxy">Proxy</label>
              <input
                id="profile-proxy"
                className="input"
                value={form.proxy ?? ""}
                onChange={(e) => set("proxy", e.target.value || null)}
                placeholder="http://user:pass@host:port"
              />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="profile-timezone">Timezone</label>
                <input
                  id="profile-timezone"
                  className="input"
                  value={form.timezone ?? ""}
                  onChange={(e) => set("timezone", e.target.value || null)}
                  placeholder="America/New_York"
                />
              </div>
              <div>
                <label className="label" htmlFor="profile-locale">Locale</label>
                <input
                  id="profile-locale"
                  className="input"
                  value={form.locale ?? ""}
                  onChange={(e) => set("locale", e.target.value || null)}
                  placeholder="en-US"
                />
              </div>
            </div>
          </div>
        </section>
        )}

        {activeSection === "device" && (
        <section
          id="profile-form-panel-device"
          role="tabpanel"
          aria-labelledby="profile-form-tab-device"
          className="form-section animate-console-section-in"
        >
          <h3 className="section-title">Device</h3>
          <div className="space-y-3">
            <div>
              <label className="label" htmlFor="profile-screen-resolution">Screen Resolution</label>
              <select
                id="profile-screen-resolution"
                className="input"
                value={currentResolution}
                onChange={(e) => {
                  const preset = RESOLUTION_PRESETS[e.target.value];
                  if (preset) {
                    set("screen_width", preset.width);
                    set("screen_height", preset.height);
                  }
                }}
              >
                {Object.keys(RESOLUTION_PRESETS).map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
                <option value="custom">Custom</option>
              </select>
            </div>
            {currentResolution === "custom" && (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="label" htmlFor="profile-screen-width">Width</label>
                  <input
                    id="profile-screen-width"
                    className="input"
                    type="number"
                    value={form.screen_width ?? 1920}
                    onChange={(e) => set("screen_width", Number(e.target.value))}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="profile-screen-height">Height</label>
                  <input
                    id="profile-screen-height"
                    className="input"
                    type="number"
                    value={form.screen_height ?? 1080}
                    onChange={(e) => set("screen_height", Number(e.target.value))}
                  />
                </div>
              </div>
            )}
            <div>
              <label className="label" htmlFor="profile-hardware-concurrency">Hardware Concurrency</label>
              <input
                id="profile-hardware-concurrency"
                className="input"
                type="number"
                value={form.hardware_concurrency ?? ""}
                onChange={(e) => set("hardware_concurrency", e.target.value ? Number(e.target.value) : null)}
                placeholder="Auto (from seed)"
              />
            </div>
            <div>
              <label className="label" htmlFor="profile-gpu-preset">GPU Preset</label>
              <select
                id="profile-gpu-preset"
                className="input"
                value=""
                onChange={(e) => {
                  if (e.target.value) applyGpuPreset(e.target.value);
                }}
              >
                <option value="">Select preset...</option>
                {Object.keys(GPU_PRESETS).map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="profile-gpu-vendor">GPU Vendor</label>
              <input
                id="profile-gpu-vendor"
                className="input"
                value={form.gpu_vendor ?? ""}
                onChange={(e) => set("gpu_vendor", e.target.value || null)}
                placeholder="Auto (from seed)"
              />
            </div>
            <div>
              <label className="label" htmlFor="profile-gpu-renderer">GPU Renderer</label>
              <input
                id="profile-gpu-renderer"
                className="input"
                value={form.gpu_renderer ?? ""}
                onChange={(e) => set("gpu_renderer", e.target.value || null)}
                placeholder="Auto (from seed)"
              />
            </div>
          </div>
        </section>
        )}

        {activeSection === "behavior" && (
        <section
          id="profile-form-panel-behavior"
          role="tabpanel"
          aria-labelledby="profile-form-tab-behavior"
          className="form-section animate-console-section-in"
        >
          <h3 className="section-title">Behavior</h3>
          <div className="space-y-3">
            <label className="choice-card">
              <input
                type="checkbox"
                checked={form.humanize ?? false}
                onChange={(e) => set("humanize", e.target.checked)}
                className="choice-checkbox"
              />
              <span className="leading-5">Human-like mouse, keyboard, and scroll behavior</span>
            </label>
            <label className="choice-card">
              <input
                type="checkbox"
                checked={form.clipboard_sync ?? true}
                onChange={(e) => set("clipboard_sync", e.target.checked)}
                className="choice-checkbox"
              />
              <span className="leading-5">Enable clipboard sync by default in VNC viewer</span>
            </label>
            <label className="choice-card">
              <input
                type="checkbox"
                checked={form.auto_launch ?? false}
                onChange={(e) => set("auto_launch", e.target.checked)}
                className="choice-checkbox"
              />
              <span className="leading-5">Launch automatically when container starts</span>
            </label>
            <div>
              <label className="label" htmlFor="profile-color-scheme">Color Scheme</label>
              <select
                id="profile-color-scheme"
                className="input"
                value={form.color_scheme ?? ""}
                onChange={(e) => set("color_scheme", e.target.value || null)}
              >
                <option value="">System default</option>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="no-preference">No preference</option>
              </select>
            </div>
          </div>
        </section>
        )}

        {activeSection === "advanced" && (
        <section
          id="profile-form-panel-advanced"
          role="tabpanel"
          aria-labelledby="profile-form-tab-advanced"
          className="form-section animate-console-section-in"
        >
          <h3 className="section-title">Advanced</h3>
          <div className="border-b border-slate-200 pb-4">
          <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Tags</h4>
          {(form.tags ?? []).length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {(form.tags ?? []).map((t) => (
                <span
                  key={t.tag}
                  className="token-chip"
                  style={t.color ? { backgroundColor: `${t.color}20`, color: t.color } : undefined}
                >
                  {t.tag}
                  <button
                    type="button"
                    onClick={() => removeTag(t.tag)}
                    className="icon-action"
                    aria-label={`Remove tag ${t.tag}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="flex gap-1">
              {TAG_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setTagColor(c)}
                  className="h-5 w-5 rounded-full border-2 shadow-hairline transition-colors focus:outline-none focus:ring-2 focus:ring-accent/20"
                  style={{
                    backgroundColor: c,
                    borderColor: tagColor === c ? "#0f172a" : "rgba(255,255,255,0.9)",
                  }}
                  aria-label={`Use tag color ${c}`}
                  aria-pressed={tagColor === c}
                />
              ))}
            </div>
            <input
              id="profile-tag-input"
              aria-label="Tag name"
              className="input flex-1"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
              placeholder="Add tag..."
            />
            <button type="button" onClick={addTag} className="btn-secondary text-xs" aria-label="Add tag">
              Add
            </button>
          </div>
          </div>

          <div className="border-b border-slate-200 py-4">
          <h4 className="section-title">Firefox Launch Args</h4>
          <p className="text-xs text-slate-500 mb-2">
            Custom Firefox arguments passed to the browser engine at launch. Only Firefox-compatible launch arguments are applied.
          </p>
          {(form.launch_args ?? []).length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {(form.launch_args ?? []).map((arg, idx) => (
                <span
                  key={idx}
                  className="token-chip font-mono"
                >
                  {arg}
                  <button
                    type="button"
                    onClick={() => removeLaunchArg(idx)}
                    className="icon-action"
                    aria-label={`Remove launch argument ${arg}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              id="profile-launch-arg-input"
              aria-label="Firefox launch argument"
              className="input flex-1 font-mono"
              value={launchArgInput}
              onChange={(e) => setLaunchArgInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addLaunchArg(); } }}
              placeholder="--private-window"
            />
            <button type="button" onClick={addLaunchArg} className="btn-secondary text-xs" aria-label="Add launch argument">
              Add
            </button>
          </div>
          </div>

          <div className="pt-4">
          <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Notes</h4>
          <label className="sr-only" htmlFor="profile-notes">Notes</label>
          <textarea
            id="profile-notes"
            className="input min-h-[80px] resize-y"
            value={form.notes ?? ""}
            onChange={(e) => set("notes", e.target.value || null)}
            placeholder="Optional notes about this profile..."
          />
          </div>
        </section>
        )}
      </div>

      {deleteConfirmOpen && isEdit && profile && (
        <ConfirmDialog
          title="Delete profile"
          description="Browser data will be permanently removed. This action cannot be undone."
          subject={publicProfileName(profile.name)}
          confirmLabel="Confirm delete profile"
          cancelLabel="Cancel"
          loading={deleting}
          tone="danger"
          onConfirm={() => void handleDelete()}
          onCancel={() => setDeleteConfirmOpen(false)}
        />
      )}

    </form>
  );
}
