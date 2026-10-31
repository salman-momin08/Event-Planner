export class ApiError extends Error {
  constructor(status, body) {
    super(body?.error?.message ?? 'Request failed');
    this.status = status;
    this.code = body?.error?.code ?? 'error';
    this.details = body?.error?.details ?? null;
    this.requestId = body?.error?.requestId ?? null;
  }
}

let onUnauthenticated = () => {};
export const setUnauthenticatedHandler = (fn) => (onUnauthenticated = fn);

export async function api(method, path, body) {
  const headers = { 'X-Requested-With': 'planner' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let res;
  try {
    res = await fetch(`/api/v1${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, { error: { code: 'network', message: 'Could not reach the server. Check your connection and try again.' } });
  }
  if (res.status === 204) return null;
  let json = null;
  try {
    json = await res.json();
  } catch {
    json = null;
  }
  if (!res.ok) {
    const err = new ApiError(res.status, json);
    if (res.status === 401 && !path.startsWith('/auth/')) onUnauthenticated();
    throw err;
  }
  return json;
}

export const get = (p) => api('GET', p);
export const post = (p, b) => api('POST', p, b ?? undefined);
export const put = (p, b) => api('PUT', p, b);
export const patch = (p, b) => api('PATCH', p, b);
export const del = (p, b) => api('DELETE', p, b);
