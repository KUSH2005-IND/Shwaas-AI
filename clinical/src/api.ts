export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("X-Requested-With", "ShwaasClinical");
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch("/clinical" + path, {
    ...options,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const data = await response.json();
      detail =
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail);
    } catch {}
    throw new ApiError(response.status, detail);
  }
  return response.json();
}
