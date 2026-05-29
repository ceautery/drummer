export type HttpMethod =
  | "GET"
  | "POST"
  | "PUT"
  | "PATCH"
  | "DELETE"
  | "HEAD"
  | "OPTIONS"
  | "TRACE";

export type AuthType = "none" | "bearer" | "basic" | "api_key" | "oauth2_cc";
export type CookieMode = "session" | "disabled" | "explicit";
export type BodyMode = "raw" | "form-data" | "json" | "graphql";
export type RequestTab =
  | "params"
  | "headers"
  | "body"
  | "auth"
  | "scripts"
  | "cookies";
export type ResponseTab =
  | "body"
  | "headers"
  | "raw"
  | "script-output"
  | "history";
export type StreamingState = "idle" | "streaming" | "done" | "error";

export interface ProjectInfo {
  name: string;
  path: string;
}

export interface RequestSummary {
  path: string;
  name: string;
  method: HttpMethod;
  url: string;
}

export interface CookieConfig {
  mode: CookieMode;
  cookies: Record<string, string>;
}

export interface AuthConfig {
  type: AuthType;
  token: string;
  username: string;
  password: string;
  key: string;
  value: string;
  token_url: string;
  client_id: string;
  client_secret: string;
  scope: string;
}

export interface GraphQLConfig {
  query: string;
  variables: Record<string, unknown>;
}

export interface RequestFrontmatter {
  name: string;
  method: HttpMethod;
  url: string;
  headers: Record<string, string>;
  params: Record<string, string>;
  encoding: string;
  cookies: CookieConfig;
  auth: AuthConfig;
  graphql?: GraphQLConfig;
  pre_script: string;
  post_script: string;
  script_timeout_ms: number | null;
  tags: string[];
  skip: boolean;
}

export interface RequestDetail {
  path: string;
  frontmatter: RequestFrontmatter;
  body: string;
}

export interface EnvironmentSummary {
  name: string;
  variable_count: number;
}

export interface EnvironmentDetail {
  name: string;
  variables: Record<string, string>;
}

export interface HistoryRecord {
  id: string;
  sent_at: string;
  request_path: string;
  request_name: string;
  environment: string;
  method: string;
  url: string;
  status_code: number;
  elapsed_ms: number;
  request_headers: [string, string][];
  request_body: string;
  response_headers: [string, string][];
  response_body: string;
  encoding: string;
  warnings: string[];
}

export interface WorkspaceInfo {
  id: string;
  name: string;
  kind: "central" | "external";
  path: string;
  is_scratch: boolean;
}

export interface WorkspaceListResponse {
  workspaces: WorkspaceInfo[];
  active: string;
}
