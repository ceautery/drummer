import { useClearCookies, useCookies } from "../../api/cookies";
import { useRequestStore } from "../../store/requestStore";
import type { CookieMode } from "../../types";
import { KeyValueTable } from "./KeyValueTable";

export function CookiesTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const cookieConfig = current?.frontmatter.cookies ?? {
    mode: "session" as CookieMode,
    cookies: {},
  };

  const { data: allCookies } = useCookies();
  const clearMutation = useClearCookies();

  const hostname = (() => {
    try {
      return new URL(current?.frontmatter.url ?? "").hostname;
    } catch {
      return "";
    }
  })();

  const sessionCookies: Record<string, string> =
    hostname && allCookies ? (allCookies[hostname] ?? {}) : {};

  return (
    <div className="p-3 flex flex-col gap-4">
      <div>
        <label htmlFor="cookie-mode" className="text-xs text-muted-foreground">
          Cookie mode
        </label>
        <select
          id="cookie-mode"
          className="mt-1 w-48 rounded border px-2 py-1 text-sm"
          value={cookieConfig.mode}
          onChange={(e) =>
            patch({
              cookies: { ...cookieConfig, mode: e.target.value as CookieMode },
            })
          }
        >
          <option value="session">Session (auto)</option>
          <option value="disabled">Disabled</option>
          <option value="explicit">Explicit</option>
        </select>
      </div>

      {cookieConfig.mode === "explicit" && (
        <div>
          <p className="text-xs text-muted-foreground mb-1">Cookies to send</p>
          <KeyValueTable
            entries={cookieConfig.cookies}
            onChange={(cookies) =>
              patch({ cookies: { ...cookieConfig, cookies } })
            }
            keyPlaceholder="Cookie name"
            valuePlaceholder="Value"
          />
        </div>
      )}

      {cookieConfig.mode === "session" && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-muted-foreground">
              Session cookies for {hostname || "this host"}
            </p>
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-destructive"
              onClick={() => clearMutation.mutate()}
            >
              Clear all
            </button>
          </div>
          {Object.keys(sessionCookies).length === 0 ? (
            <p className="text-xs text-muted-foreground italic">
              {hostname
                ? `No session cookies for ${hostname}`
                : "Enter a URL to see session cookies"}
            </p>
          ) : (
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-muted-foreground text-left">
                  <th className="pr-4 pb-1 font-normal">Name</th>
                  <th className="pb-1 font-normal">Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(sessionCookies).map(([name, value]) => (
                  <tr key={name} className="border-t">
                    <td className="pr-4 py-1 text-foreground">{name}</td>
                    <td className="py-1 text-muted-foreground truncate max-w-0">
                      {value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
