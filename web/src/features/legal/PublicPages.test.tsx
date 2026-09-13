import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { ErrorPage, NotFoundPage, TermsPage } from "./PublicPages";

function renderPage(page: React.ReactNode) {
  return render(<MemoryRouter>{page}</MemoryRouter>);
}

describe("public status and legal pages", () => {
  it("offers a safe return path from the not-found page", () => {
    renderPage(<NotFoundPage />);
    expect(screen.getByRole("heading", { name: /off the map/i })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /return home/i }).getAttribute("href"),
    ).toBe("/");
  });

  it("invokes recovery from the error page", () => {
    const retry = vi.fn();
    renderPage(<ErrorPage retry={retry} />);
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("renders the public terms and acceptable-use commitment", () => {
    renderPage(<TermsPage />);
    expect(
      screen.getByRole("heading", { name: "Terms & Conditions" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Acceptable use" }),
    ).toBeTruthy();
  });
});
