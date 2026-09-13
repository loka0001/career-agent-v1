import { AUTH_SESSION_EXPIRED_EVENT, request } from "./api";

describe("API wrapper", () => {
  afterEach(() => vi.restoreAllMocks());

  it("adds credentials and CSRF to state-changing requests", async () => {
    Object.defineProperty(document, "cookie", {
      value: "commerce_csrf=test-token",
      writable: true,
    });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await request<{ ok: boolean }>("/api/example", {
      method: "POST",
      body: JSON.stringify({ value: 1 }),
    });
    const init = fetchMock.mock.calls[0]?.[1];
    const headers = new Headers(init?.headers);
    expect(init?.credentials).toBe("include");
    expect(headers.get("X-CSRF-Token")).toBe("test-token");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("turns the safe server envelope into ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "not_found",
            message: "غير موجود",
            details: {},
            request_id: "r1",
          },
        }),
        { status: 404 },
      ),
    );
    await expect(request("/api/missing")).rejects.toEqual(
      expect.objectContaining({ status: 404, message: "غير موجود" }),
    );
  });

  it("announces an expired authenticated session after a 401 response", async () => {
    const onExpired = vi.fn();
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, onExpired);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "authentication_required",
            message: "Sign in again",
            details: {},
            request_id: "r2",
          },
        }),
        { status: 401 },
      ),
    );

    await expect(request("/api/v1/products")).rejects.toEqual(
      expect.objectContaining({ status: 401 }),
    );
    expect(onExpired).toHaveBeenCalledOnce();
    window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, onExpired);
  });

  it("does not label a rejected sign-in as an expired session", async () => {
    const onExpired = vi.fn();
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, onExpired);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "invalid_credentials",
            message: "Invalid credentials",
            details: {},
            request_id: "r3",
          },
        }),
        { status: 401 },
      ),
    );

    await expect(request("/api/v1/auth/login")).rejects.toEqual(
      expect.objectContaining({ status: 401 }),
    );
    expect(onExpired).not.toHaveBeenCalled();
    window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, onExpired);
  });
});
