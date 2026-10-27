// Error messages of the market_data routes. The backend sends {"detail": "<message>"} for 502 and 503.
// A proxy sends no JSON, and 422 has a list as detail: then the message names the HTTP status.
export async function readErrorMessage(response: Response, failedAction: string): Promise<string> {
  const statusMessage = `${failedAction} failed with HTTP status ${String(response.status)}.`;
  let errorBody: unknown;
  try {
    errorBody = await response.json();
  } catch {
    return statusMessage;
  }
  if (typeof errorBody === 'object' && errorBody !== null && 'detail' in errorBody && typeof errorBody.detail === 'string') {
    return errorBody.detail;
  }
  return statusMessage;
}
