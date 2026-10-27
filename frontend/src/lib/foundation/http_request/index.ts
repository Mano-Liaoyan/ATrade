// Public entry of foundation/http_request: sends a request to the backend and reads the error message of a failed answer.
export {
  BACKEND_NOT_REACHABLE,
  describeErrorBody,
  readErrorMessage,
  readJsonBody,
  requestJson,
  sendRequest,
} from './http_request';
export type { RequestResult } from './http_request';
