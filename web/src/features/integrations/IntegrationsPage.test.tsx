import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { LanguageProvider } from "../../i18n";
import { api } from "../../lib/api";
import type { WhatsAppSettings } from "../../lib/types";
import { integrationSectionFromSearch } from "./IntegrationsPage";
import { IntegrationsPage } from "./IntegrationsPage";
import { integrationReadinessPresentation } from "./integrationStatus";

const whatsappSettings: WhatsAppSettings = {
  channel_id: null,
  mode: "demo",
  demo_available: true,
  display_name: "WhatsApp Business",
  configured: false,
  is_active: true,
  masked_phone_number_id: null,
  masked_waba_id: null,
  webhook_path: "/api/v1/webhooks/whatsapp",
  embedded_signup_available: false,
  connection_status: "disconnected",
};

function renderPage(query = "") {
  return render(
    <MemoryRouter initialEntries={[`/app/integrations${query}`]}>
      <LanguageProvider>
        <IntegrationsPage />
      </LanguageProvider>
    </MemoryRouter>,
  );
}

describe("integrationSectionFromSearch", () => {
  it("keeps supported focused sections and falls back to the overview", () => {
    expect(
      integrationSectionFromSearch(new URLSearchParams("section=store")),
    ).toBe("store");
    expect(
      integrationSectionFromSearch(new URLSearchParams("section=meta")),
    ).toBe("meta");
    expect(
      integrationSectionFromSearch(new URLSearchParams("section=whatsapp")),
    ).toBe("whatsapp");
    expect(
      integrationSectionFromSearch(new URLSearchParams("section=unknown")),
    ).toBe("overview");
    expect(integrationSectionFromSearch(new URLSearchParams())).toBe(
      "overview",
    );
  });

  it("routes provider OAuth callbacks to the component that completes them", () => {
    expect(
      integrationSectionFromSearch(
        new URLSearchParams("meta_code=code&meta_state=state"),
      ),
    ).toBe("meta");
    expect(
      integrationSectionFromSearch(
        new URLSearchParams("shopify_code=code&shopify_state=state"),
      ),
    ).toBe("store");
  });
});

describe("integrationReadinessPresentation", () => {
  it("labels disconnected or unconfigured providers in both languages", () => {
    expect(
      integrationReadinessPresentation(false, "disconnected", "en"),
    ).toEqual({
      label: "Disconnected",
      tone: "error",
    });
    expect(
      integrationReadinessPresentation(false, "disconnected", "ar"),
    ).toEqual({
      label: "مفصول",
      tone: "error",
    });
  });

  it("distinguishes configured, degraded, and generic unconfigured states", () => {
    expect(
      integrationReadinessPresentation(true, "connected", "en").label,
    ).toBe("Ready");
    expect(
      integrationReadinessPresentation(false, "action_required", "en"),
    ).toEqual({ label: "Action required", tone: "error" });
    expect(
      integrationReadinessPresentation(false, "disabled", "en").label,
    ).toBe("Not configured");
  });
});

describe("IntegrationsPage sections", () => {
  beforeEach(() => {
    localStorage.setItem("commerce-language", "en");
    vi.spyOn(api, "integrations").mockResolvedValue({
      integrations: [
        {
          name: "facebook",
          configured: false,
          mode: "disconnected",
          masked_identifier: null,
          last_check: null,
        },
      ],
    });
    vi.spyOn(api, "providerConnections").mockResolvedValue([]);
    vi.spyOn(api, "whatsappSettings").mockResolvedValue(whatsappSettings);
    vi.spyOn(api, "whatsappTemplates").mockResolvedValue([]);
  });

  afterEach(() => vi.restoreAllMocks());

  it("opens with status overview and reveals only the selected setup workspace", async () => {
    renderPage();
    await screen.findByText("Connected accounts");
    expect(screen.getByText("Disconnected")).toBeTruthy();
    expect(screen.queryByText("Store and website")).toBeNull();
    expect(screen.queryByText("Follow-up templates")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Store" }));
    expect(await screen.findByText("Store and website")).toBeTruthy();
    expect(screen.queryByText("Connected accounts")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "WhatsApp" }));
    expect(await screen.findByText("Follow-up templates")).toBeTruthy();
    expect(screen.queryByText("Store and website")).toBeNull();
  });
});
