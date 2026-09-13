import { fireEvent, render, screen } from "@testing-library/react";
import { ThemeProvider, useTheme } from "./ThemeContext";

function Consumer() {
  const { theme, toggleTheme } = useTheme();
  return <button onClick={toggleTheme}>{theme}</button>;
}

describe("theme preference", () => {
  it("persists a user-selected light or dark theme", () => {
    window.localStorage.setItem("commerce-theme", "dark");
    render(
      <ThemeProvider>
        <Consumer />
      </ThemeProvider>,
    );
    const button = screen.getByRole("button");
    expect(button.textContent).toBe("dark");
    fireEvent.click(button);
    expect(button.textContent).toBe("light");
    expect(window.localStorage.getItem("commerce-theme")).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
