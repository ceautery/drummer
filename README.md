# Drummer

A local, standalone REST client — free and open-source alternative to Postman, Insomnia, and Bruno.

- **No account** — runs entirely on your machine
- **No subscription** — free forever
- **No phone-home** — your data stays local
- **Git-friendly** — request files are plain Markdown with YAML frontmatter, fully diffable

---

## Install

Requires Python 3.12+.

```bash
git clone https://github.com/ceautery/drummer
cd drummer
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
make build-frontend
```

Requires Node.js (for the frontend build step). Homebrew and PyPI packages are planned for a future release.

---

## Quick start

```bash
# Launch Drummer (opens your last workspace, or the built-in Scratch space on first run)
drummer

# Open an external project folder (registers it as a workspace)
drummer --project /path/to/my-api
```

Workspaces live under `~/.drummer/projects/`. The built-in **Scratch** workspace is always available for quick, throwaway requests. Use the workspace switcher in the top bar to create new workspaces, register existing folders, and cycle between them during a session.

Drummer starts on port 8000. Open `http://localhost:8000` in your browser.

---

## Creating a project

A Drummer project is a folder with a `.drummer/` directory and Markdown request files anywhere inside it.

```
my-api/
├── .drummer/
│   ├── project.yaml
│   └── environments/
│       └── local.yaml
├── users/
│   ├── list-users.md
│   └── get-user.md
└── auth/
    └── login.md
```

**`.drummer/project.yaml`**

```yaml
name: My API
version: "1"
default_environment: local
```

**`.drummer/environments/local.yaml`**

```yaml
name: local
variables:
  base_url: https://jsonplaceholder.typicode.com
  user_id: "1"
```

**`users/list-users.md`**

```markdown
---
name: List Users
method: GET
url: "{{base_url}}/users"
---
```

**`users/get-user.md`**

```markdown
---
name: Get User
method: GET
url: "{{base_url}}/users/{{user_id}}"
---
```

Select an environment in the sidebar, pick a request, click **Send**.

---

## Tutorial

Run `drummer`, then click the **Tutorial** button in the top bar. The tutorial walks through all of Drummer's features using offline mock APIs backed by Metropolitan Museum of Art Open Access data and a snapshot of Wikidata — no internet required.

---

## Theming

Drummer supports light, dark, and system-auto themes. Use the theme toggle in the
top app bar (or the tutorial's nav). Your choice is saved to `~/.drummer/config.yaml`
and applies across the app and the tutorial.

---

## Scripting

Every request can have a **pre-request** and **post-request** JavaScript script. Scripts run in an embedded QuickJS sandbox and access the `dm` global.

### Read and write environment variables

```javascript
// pre-request: stamp the current time
dm.request.headers["X-Timestamp"] = Date.now().toString();
```

```javascript
// post-request: pull a token from the response and save it
const body = dm.response.json();
dm.env.set("access_token", body.token);
```

### Chain requests

```javascript
// post-request on "Create User" — saves the new ID for later requests
const body = dm.response.json();
dm.env.set("user_id", body.id.toString());
```

### `dm` API summary

| Object | Available in | Description |
|---|---|---|
| `dm.env.get(key)` | both | Read an environment variable |
| `dm.env.set(key, value)` | both | Write an environment variable (session-scoped) |
| `dm.request.url` | pre-request | Outgoing URL (mutable) |
| `dm.request.headers` | pre-request | Outgoing headers (mutable object) |
| `dm.request.params` | pre-request | Query parameters (mutable object) |
| `dm.request.body` | pre-request | Outgoing body (mutable string) |
| `dm.response.status` | post-request | HTTP status code |
| `dm.response.json()` | post-request | Parsed JSON body |
| `dm.response.text()` | post-request | Raw response body |
| `dm.response.headers` | post-request | Response headers object |
| `dm.console.log(...)` | both | Output to Script Output panel |

Scripts have a 5-second timeout and no network or filesystem access.

---

## MCP integration

Drummer exposes an MCP server so Claude can send requests, inspect responses, and manage environments without leaving a conversation.

**Setup:**

1. Start Drummer: `drummer --project /path/to/my-api`
2. Add to your Claude MCP config:

```json
{
  "mcpServers": {
    "drummer": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

3. Run `drummer mcp` to confirm the URL and see all available tools.

Claude can then call tools like `send_request`, `set_variable`, `switch_environment`, and `get_history` to work with your API alongside you.

---

## CLI reference

| Command | Description |
|---|---|
| `drummer [--project PATH] [--port N]` | Start the server |
| `drummer new NAME` | Create a new workspace named NAME under ~/.drummer/projects/ |
| `drummer export PATH` | Export a project as a zip |
| `drummer mcp` | Show MCP server URL and available tools |
| `drummer --version` | Print version |

---

## Development

After cloning and creating a venv (see Install above), install the dev extras:

```bash
pip install -e ".[dev]"
make check        # ruff + pyright + pytest
make dist         # build a distributable wheel
```

### Dev server (hot reload)

`drummer/api/static/` is gitignored — the compiled frontend is not in the repo. During development, use the Vite dev server instead of rebuilding on every change:

```bash
# Tutorial (no project)
make dev

# With a project
make dev PROJECT=/path/to/your/project
```

This starts two processes: the FastAPI backend on `http://localhost:8000` and the Vite dev server on `http://localhost:5173`. Open **port 5173** in your browser. The frontend hot-reloads on save; Python changes take effect after restarting the backend (`Ctrl-C` and re-run).

To do a one-off production build after changes:

```bash
make build-frontend
```

---

## License

MIT. Tutorial data from the [Metropolitan Museum of Art Open Access](https://metmuseum.org/about-the-met/policies-and-documents/open-access) collection (CC0) and [Wikidata](https://www.wikidata.org) (CC0).
