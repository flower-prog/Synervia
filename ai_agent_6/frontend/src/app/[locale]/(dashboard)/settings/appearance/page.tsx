"use client";

import { BrandColorPicker } from "@/components/settings/brand-color-picker";
import { SettingsRow, SettingsSection } from "@/components/settings/settings-section";
import { ThemeToggle } from "@/components/theme";

export default function AppearanceSettingsPage() {
  return (
    <div className="space-y-6">
      <SettingsSection title="Theme" description="Light, dark, or follow your system preference.">
        <SettingsRow
          label="Color scheme"
          description="Affects the entire dashboard. Marketing pages alternate sections regardless."
          control={<ThemeToggle variant="dropdown" />}
        />
      </SettingsSection>

      <SettingsSection
        title="Brand color"
        description="Pick the accent color used across the workspace. Saved per-device."
      >
        <BrandColorPicker />
        <p className="text-foreground/55 mt-4 text-xs leading-relaxed">
          Choosing a preset updates CSS custom properties at runtime —{" "}
          <code className="font-mono">--brand-h</code>, <code className="font-mono">--brand-c</code>
          , <code className="font-mono">--brand-l</code>. Forking the template lets you bake any
          color in by editing one block in <code className="font-mono">globals.css</code>.
        </p>
      </SettingsSection>
    </div>
  );
}
