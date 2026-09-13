import { render, screen } from "@testing-library/react";
import { AccessStatus, DemoStatus } from "./domain/AccessStatus";
import { errorText } from "./operations";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  Skeleton,
  Spinner,
  StatCard,
} from "./ui";

describe("shared UI", () => {
  it("exposes an accessible error alert", () => {
    render(<Alert tone="error">حدث خطأ</Alert>);
    expect(screen.getByRole("alert").textContent).toContain("حدث خطأ");
  });

  it("keeps a disabled primary action disabled", () => {
    render(<Button disabled>حفظ</Button>);
    expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  it("renders a useful empty state", () => {
    render(<EmptyState title="لا توجد نتائج" body="جرّب بحثًا آخر" />);
    expect(screen.getByRole("heading").textContent).toBe("لا توجد نتائج");
  });

  it("labels free access and isolated demo data explicitly", () => {
    render(
      <>
        <AccessStatus language="en" />
        <DemoStatus language="en" />
      </>,
    );
    expect(screen.getByText("Free access · no card")).toBeTruthy();
    expect(screen.getByText("Demo · isolated data")).toBeTruthy();
  });

  it("renders data-display and loading variants", () => {
    render(
      <>
        <Badge tone="success">Ready</Badge>
        <StatCard icon="↑" label="Revenue" value="$42" foot="Today" />
        <Spinner label="Syncing" />
        <Skeleton height="2rem" className="preview" />
      </>,
    );
    expect(screen.getByText("Ready").className).toContain("success");
    expect(screen.getByText("Today")).toBeTruthy();
    expect(screen.getByText("Syncing")).toBeTruthy();
  });

  it("localizes unknown operation failures", () => {
    expect(errorText(new Error("offline"), "en")).toBe(
      "Data could not be loaded. Try again.",
    );
    expect(errorText(new Error("offline"), "ar")).toBe(
      "تعذر تحميل البيانات. حاول مرة أخرى.",
    );
  });
});
