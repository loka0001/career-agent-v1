import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EntitledRoute, OperatorRoute, ProtectedRoute } from "./ProtectedRoute";

const auth = vi.hoisted(() => ({
  loading: false,
  user: null as object | null,
  subscription: null as { plan: { features: string[] } } | null,
  isOperator: false,
  sessionExpired: false,
}));

vi.mock("./AuthContext", () => ({ useAuth: () => auth }));
vi.mock("../i18n", () => ({
  useLanguage: () => ({ language: "en" }),
}));

function LocationProbe() {
  const location = useLocation();
  return <p>{location.pathname + location.search}</p>;
}

describe("route access states", () => {
  beforeEach(() => {
    auth.loading = false;
    auth.user = null;
    auth.subscription = null;
    auth.isOperator = false;
    auth.sessionExpired = false;
  });

  it("preserves an expired-session reason when redirecting to sign in", () => {
    auth.sessionExpired = true;
    render(
      <MemoryRouter initialEntries={["/app/command"]}>
        <Routes>
          <Route
            path="/app/command"
            element={
              <ProtectedRoute>
                <p>Private</p>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("/login?reason=session-expired")).toBeTruthy();
  });

  it("shows a useful feature-denied state instead of silently redirecting", () => {
    auth.subscription = { plan: { features: [] } };
    render(
      <MemoryRouter>
        <EntitledRoute feature="catalog">
          <p>Catalog</p>
        </EntitledRoute>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Access denied" })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: "Return to Home" }).getAttribute("href"),
    ).toBe("/app/command");
    expect(screen.queryByText("Catalog")).toBeNull();
  });

  it("shows a role-denied state for non-operators", () => {
    render(
      <MemoryRouter>
        <OperatorRoute>
          <p>Operator controls</p>
        </OperatorRoute>
      </MemoryRouter>,
    );

    expect(
      screen.getByText("Your role does not include operator access."),
    ).toBeTruthy();
    expect(screen.queryByText("Operator controls")).toBeNull();
  });
});
