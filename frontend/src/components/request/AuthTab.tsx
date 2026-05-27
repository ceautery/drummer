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
    </div>
  );
}
