import { useRequestStore } from "../../store/requestStore";
import type { AuthType } from "../../types";

export function AuthTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const auth = current?.frontmatter.auth ?? {
    type: "none" as AuthType,
    token: "",
    username: "",
    password: "",
    key: "",
    value: "",
    token_url: "",
    client_id: "",
    client_secret: "",
    scope: "",
  };

  const update = (changes: Partial<typeof auth>) =>
    patch({ auth: { ...auth, ...changes } });

  return (
    <div className="p-3 flex flex-col gap-3">
      <div>
        <label htmlFor="auth-type" className="text-xs text-gray-500">
          Auth type
        </label>
        <select
          id="auth-type"
          className="mt-1 w-48 rounded border px-2 py-1 text-sm"
          value={auth.type}
          onChange={(e) => update({ type: e.target.value as AuthType })}
        >
          <option value="none">None</option>
          <option value="bearer">Bearer Token</option>
          <option value="basic">Basic Auth</option>
          <option value="oauth2_cc">OAuth 2.0 Client Credentials</option>
          <option value="api_key" disabled>
            API Key
          </option>
        </select>
      </div>

      {auth.type === "bearer" && (
        <div>
          <label htmlFor="bearer-token" className="text-xs text-gray-500">
            Token
          </label>
          <input
            id="bearer-token"
            type="text"
            className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
            value={auth.token}
            placeholder="Bearer token"
            onChange={(e) => update({ token: e.target.value })}
          />
        </div>
      )}

      {auth.type === "basic" && (
        <>
          <div>
            <label htmlFor="basic-username" className="text-xs text-gray-500">
              Username
            </label>
            <input
              id="basic-username"
              type="text"
              className="mt-1 w-full rounded border px-2 py-1 text-sm"
              value={auth.username}
              onChange={(e) => update({ username: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="basic-password" className="text-xs text-gray-500">
              Password
            </label>
            <input
              id="basic-password"
              type="password"
              className="mt-1 w-full rounded border px-2 py-1 text-sm"
              value={auth.password}
              onChange={(e) => update({ password: e.target.value })}
            />
          </div>
        </>
      )}

      {auth.type === "oauth2_cc" && (
        <>
          <div>
            <label htmlFor="oauth-token-url" className="text-xs text-gray-500">
              Token URL
            </label>
            <input
              id="oauth-token-url"
              type="text"
              className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
              value={auth.token_url}
              placeholder="https://auth.example.com/token"
              onChange={(e) => update({ token_url: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="oauth-client-id" className="text-xs text-gray-500">
              Client ID
            </label>
            <input
              id="oauth-client-id"
              type="text"
              className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
              value={auth.client_id}
              onChange={(e) => update({ client_id: e.target.value })}
            />
          </div>
          <div>
            <label
              htmlFor="oauth-client-secret"
              className="text-xs text-gray-500"
            >
              Client Secret
            </label>
            <input
              id="oauth-client-secret"
              type="password"
              className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
              value={auth.client_secret}
              onChange={(e) => update({ client_secret: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="oauth-scope" className="text-xs text-gray-500">
              Scope
            </label>
            <input
              id="oauth-scope"
              type="text"
              className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
              value={auth.scope}
              placeholder="optional"
              onChange={(e) => update({ scope: e.target.value })}
            />
          </div>
        </>
      )}
    </div>
  );
}
