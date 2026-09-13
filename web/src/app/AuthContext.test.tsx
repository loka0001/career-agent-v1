import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthContext";

const mocks = vi.hoisted(() => ({
  me: vi.fn(),
  subscription: vi.fn(),
  billingCapabilities: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  AUTH_SESSION_EXPIRED_EVENT: "commerce:auth-session-expired",
  api: {
    me: mocks.me,
    subscription: mocks.subscription,
    billingCapabilities: mocks.billingCapabilities,
  },
}));

function SessionState() {
  const { user, sessionExpired } = useAuth();
  return (
    <p>
      {user?.email ?? "anonymous"}|{sessionExpired ? "expired" : "active"}
    </p>
  );
}

describe("authentication session lifecycle", () => {
  beforeEach(() => {
    mocks.me.mockReset();
    mocks.subscription.mockReset();
    mocks.billingCapabilities.mockReset();
    mocks.me.mockResolvedValue({
      user: { email: "merchant@example.com" },
      is_operator: false,
      demo_mode: false,
    });
    mocks.subscription.mockResolvedValue({
      plan: { features: ["catalog"] },
    });
    mocks.billingCapabilities.mockResolvedValue({ free_access: true });
  });

  it("clears authenticated state when the API announces expiration", async () => {
    render(
      <AuthProvider>
        <SessionState />
      </AuthProvider>,
    );
    expect(await screen.findByText("merchant@example.com|active")).toBeTruthy();

    act(() => {
      window.dispatchEvent(new Event("commerce:auth-session-expired"));
    });

    expect(screen.getByText("anonymous|expired")).toBeTruthy();
  });
});
