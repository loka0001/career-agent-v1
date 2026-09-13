import { profileCopy } from "./profileCopy";

describe("profileCopy", () => {
  it("provides complete English copy for the store and brand profile forms", () => {
    const copy = profileCopy("en");

    expect(copy.store).toMatchObject({
      storeName: "Store name",
      businessType: "Business type",
      defaultLanguage: "Language",
      aiBudget: "Monthly AI budget in USD",
      logoUrl: "Logo URL",
      primaryColor: "Primary color",
      accentColor: "Accent color",
      shippingPolicy: "Shipping policy",
      returnPolicy: "Return policy",
      save: "Save settings",
      saved: "Store settings and policies saved.",
    });
    expect(copy.brand).toEqual({
      tone: "Brand tone",
      primaryColor: "Primary color",
      audience: "Audience",
      guidelines: "Writing guidelines",
      save: "Save brand voice",
      saved: "Brand voice saved.",
    });
    expect(copy.agent).toMatchObject({
      title: "Sales assistant settings",
      savedStatus: "All changes saved",
      unsavedStatus: "Unsaved changes",
      discard: "Discard changes",
      personaTitle: "Assistant persona",
      assistantName: "Assistant name",
      tone: "Reply tone",
      instructions: "Special instructions",
      save: "Save assistant persona",
      saved: "Assistant persona saved.",
      testTitle: "Test assistant",
      realCatalogData: "Real catalog data",
      runTest: "Run test",
      runningTest: "Testing…",
    });
  });

  it("keeps complete Arabic copy for the store and brand profile forms", () => {
    const copy = profileCopy("ar");

    expect(copy.store.storeName).toBe("اسم المتجر");
    expect(copy.store.save).toBe("حفظ الإعدادات");
    expect(copy.store.saved).toBe("تم حفظ إعدادات المتجر والسياسات.");
    expect(copy.brand.tone).toBe("نبرة البراند");
    expect(copy.brand.save).toBe("حفظ صوت البراند");
    expect(copy.brand.saved).toBe("تم حفظ صوت البراند.");
    expect(copy.agent.assistantName).toBe("اسم المساعد");
    expect(copy.agent.title).toBe("إعدادات مساعد المبيعات");
    expect(copy.agent.unsavedStatus).toBe("تغييرات غير محفوظة");
    expect(copy.agent.discard).toBe("تجاهل التغييرات");
    expect(copy.agent.runTest).toBe("تشغيل الاختبار");
    expect(copy.agent.saved).toBe("تم حفظ شخصية المساعد.");
  });
});
