import { contentStatusPresentation } from "./contentStatus";

describe("contentStatusPresentation", () => {
  it("turns failed and ambiguous publication states into actionable English", () => {
    expect(contentStatusPresentation("failed", "en")).toEqual({
      label: "Publish failed",
      tone: "error",
      guidance:
        "Publishing failed. Review the channel connection before trying again.",
    });
    expect(contentStatusPresentation("publish_retrying", "en")).toEqual({
      label: "Publish retry scheduled",
      tone: "warning",
      guidance:
        "Publishing failed temporarily. The worker will retry automatically.",
    });
    expect(contentStatusPresentation("publish_unknown", "en")).toEqual({
      label: "Publish status unknown",
      tone: "error",
      guidance:
        "Review the social channel before publishing again to avoid a duplicate post.",
    });
  });

  it("localizes actionable publication states in Arabic", () => {
    expect(contentStatusPresentation("failed", "ar").label).toBe("فشل النشر");
    expect(
      contentStatusPresentation("publish_retrying", "ar").guidance,
    ).toContain("إعادة المحاولة");
    expect(
      contentStatusPresentation("publish_unknown", "ar").guidance,
    ).toContain("منع تكرار");
  });

  it("maps normal lifecycle states without warning guidance", () => {
    expect(contentStatusPresentation("draft", "en")).toEqual({
      label: "Draft",
      tone: "warning",
      guidance: null,
    });
    expect(contentStatusPresentation("published", "ar")).toEqual({
      label: "منشور",
      tone: "success",
      guidance: null,
    });
  });
});
