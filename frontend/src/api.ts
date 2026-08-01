const json = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(path, {headers: {'Content-Type': 'application/json'}, ...options})
  if (!response.ok) throw new Error((await response.json()).detail ?? `Request failed: ${response.status}`)
  return response.json()
}

export const api = {
  get: <T>(path: string) => json<T>(path),
  post: <T>(path: string, body?: unknown) => json<T>(path, {method: 'POST', body: body === undefined ? undefined : JSON.stringify(body)}),
}

