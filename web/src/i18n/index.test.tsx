import { fireEvent, render, screen } from "@testing-library/react";
import { LanguageProvider, useLanguage } from ".";

function Consumer() {
  const { language, toggle } = useLanguage();
  return <button onClick={toggle}>{language}</button>;
}

describe("language direction", () => {
  it("persists English LTR and returns to Arabic RTL", () => {
    window.localStorage.setItem("commerce-language", "en");
    render(
      <LanguageProvider>
        <Consumer />
      </LanguageProvider>,
    );
    const button = screen.getByRole("button");
    expect(button.textContent).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
    fireEvent.click(button);
    expect(document.documentElement.lang).toBe("ar");
    expect(document.documentElement.dir).toBe("rtl");
    expect(window.localStorage.getItem("commerce-language")).toBe("ar");
  });
});
