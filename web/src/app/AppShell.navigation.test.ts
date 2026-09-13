import { describe, expect, it } from "vitest";
import {
  primaryNavigationItems,
  secondaryNavigationGroups,
} from "./navigation";

describe("AppShell navigation model", () => {
  it("keeps the primary navigation limited to the six P0 merchant jobs", () => {
    expect(primaryNavigationItems.map((item) => item.to)).toEqual([
      "/app/command",
      "/app/inbox",
      "/app/studio",
      "/app/products",
      "/app/integrations",
      "/app/settings",
    ]);
  });

  it("preserves non-P0 modules in secondary navigation without duplicates", () => {
    const secondaryPaths = secondaryNavigationGroups.flatMap((group) =>
      group.items.map((item) => item.to),
    );

    expect(new Set(secondaryPaths).size).toBe(secondaryPaths.length);
    expect(secondaryPaths).toEqual(
      expect.arrayContaining([
        "/app/opportunities",
        "/app/customers",
        "/app/orders",
        "/app/calendar",
        "/app/analytics",
        "/app/automations",
        "/app/agent-settings",
        "/app/team",
        "/app/billing",
        "/app/security",
        "/app/api-keys",
        "/app/privacy",
      ]),
    );
    expect(
      secondaryPaths.some((path) =>
        primaryNavigationItems.some((item) => item.to === path),
      ),
    ).toBe(false);
  });
});
