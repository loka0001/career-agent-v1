import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "../../i18n";
import { ApiError } from "../../lib/api";
import { LoginPage } from "./LoginPage";

const auth = vi.hoisted(() => ({
  user: null as object | null,
  login: vi.fn(),
}));

vi.mock("../../app/AuthContext", () => ({
  useAuth: () => auth,
}));

function renderLogin(path = "/login", language: "ar" | "en" = "en") {
  window.localStorage.setItem("commerce-language", language);
  return render(
    <MemoryRouter initialEntries={[path]}>
      <LanguageProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/app/command" element={<p>Command destination</p>} />
        </Routes>
      </LanguageProvider>
    </MemoryRouter>,
  );
}

function fillCredentials() {
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "merchant@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "correct-horse-battery" },
  });
}

describe("login session state", () => {
  beforeEach(() => {
    window.localStorage.clear();
    auth.user = null;
    auth.login.mockReset();
  });

  it("explains an expired session in English", () => {
    renderLogin("/login?reason=session-expired");

    expect(
      screen.getByText("Your session expired. Sign in again to continue."),
    ).toBeTruthy();
  });

  it("explains an expired session in Arabic", () => {
    renderLogin("/login?reason=session-expired", "ar");

    expect(
      screen.getByText("انتهت جلستك. سجّل الدخول مرة أخرى للمتابعة."),
    ).toBeTruthy();
  });

  it("signs in with a remembered email and supports password visibility", async () => {
    window.localStorage.setItem("commerce-login-email", "merchant@example.com");
    auth.login.mockResolvedValue(undefined);
    renderLogin();

    const password = screen.getByLabelText("Password");
    expect(screen.getByLabelText("Email").getAttribute("value")).toBe(
      "merchant@example.com",
    );
    fireEvent.change(password, {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(password.getAttribute("type")).toBe("text");
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Command destination")).toBeTruthy();
    expect(auth.login).toHaveBeenCalledWith(
      "merchant@example.com",
      "correct-horse-battery",
      undefined,
    );
    expect(window.localStorage.getItem("commerce-login-email")).toBe(
      "merchant@example.com",
    );
  });

  it("removes a stored email when remember is cleared", async () => {
    window.localStorage.setItem("commerce-login-email", "old@example.com");
    auth.login.mockResolvedValue(undefined);
    renderLogin();

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "merchant@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Command destination")).toBeTruthy();
    expect(window.localStorage.getItem("commerce-login-email")).toBeNull();
  });

  it("collects and submits a six-digit MFA code", async () => {
    auth.login
      .mockRejectedValueOnce(
        new ApiError(401, {
          code: "mfa_required",
          message: "MFA required",
          details: {},
          request_id: "mfa-1",
        }),
      )
      .mockResolvedValueOnce(undefined);
    renderLogin();
    fillCredentials();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(
      await screen.findByRole("heading", {
        name: "Two-factor verification",
      }),
    ).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Verification code"), {
      target: { value: "a12-3456z" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Verify and sign in" }));

    expect(await screen.findByText("Command destination")).toBeTruthy();
    expect(auth.login).toHaveBeenLastCalledWith(
      "merchant@example.com",
      "correct-horse-battery",
      "123456",
    );
  });

  it("shows the safe API error and allows returning from MFA", async () => {
    auth.login.mockRejectedValue(
      new ApiError(401, {
        code: "mfa_required",
        message: "MFA required",
        details: {},
        request_id: "mfa-2",
      }),
    );
    renderLogin();
    fillCredentials();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByRole("heading", { name: "Two-factor verification" });
    fireEvent.click(
      screen.getByRole("button", { name: "Back to credentials" }),
    );

    expect(
      screen.getByRole("heading", { name: "Sign in to workspace" }),
    ).toBeTruthy();
  });

  it("renders provider and network failures safely", async () => {
    auth.login.mockRejectedValueOnce(
      new ApiError(401, {
        code: "invalid_credentials",
        message: "Invalid email or password",
        details: {},
        request_id: "login-1",
      }),
    );
    const view = renderLogin();
    fillCredentials();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Invalid email or password")).toBeTruthy();

    view.unmount();
    auth.login.mockRejectedValueOnce(new TypeError("network down"));
    renderLogin();
    fillCredentials();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() =>
      expect(screen.getByText("Unable to connect to the server.")).toBeTruthy(),
    );
  });

  it("redirects an already authenticated user", () => {
    auth.user = {};
    renderLogin();

    expect(screen.getByText("Command destination")).toBeTruthy();
  });
});
