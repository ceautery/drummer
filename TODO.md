# TODO

Current sprint: **Phase 10 — Distribution**

Plan: `docs/superpowers/plans/` (not yet written)

## Deferred from Phase 9

- **Expired cookie row cleanup** — `persistence.save()` is called even for expired cookies (max-age=0, past expires), writing rows that are filtered on load but never deleted. Add a single-row `DELETE WHERE (hostname, name) = (?, ?)` path to `CookiePersistenceProtocol` and call it instead of `save()` when a cookie is expired. A periodic vacuum would also help.

- **OAuth credential variable substitution** — `token_url`, `client_id`, `client_secret`, and `scope` in `AuthConfig` are passed through `resolve()` unchanged and do not support `{{variable}}` syntax. Committing a `client_secret` in a request file is a security smell. Add substitution for OAuth fields in `variables.py` (same path as bearer/basic auth), or add a dedicated secrets/environment mechanism.
