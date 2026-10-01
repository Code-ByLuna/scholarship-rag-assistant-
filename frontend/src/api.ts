const BASE = import.meta.env.VITE_API_BASE || "";

export async function api<T>(
  path: string,
  body?: unknown,
  token?: string,
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch(BASE + "/api" + path, {
      method: body === undefined ? "GET" : "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "X-Session-Token": token } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(
        data.error?.message ||
          (data.missing_required_fields
            ? "Complete these fields: " +
              data.missing_required_fields.join(", ")
            : "The request could not be completed."),
      );
    }
    return data as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The request timed out. Please try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}
