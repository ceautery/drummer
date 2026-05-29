# CLI Reference

## drummer

Start the Drummer server and open it in the browser.

```bash
drummer [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--project PATH` | none | Register an external folder as a workspace and open it |
| `--port INTEGER` | 8000 | Port to listen on |
| `--host TEXT` | 127.0.0.1 | Host address to bind to |

**Examples:**

```bash
# Open Drummer (last workspace, or built-in Scratch on first run)
drummer

# Register and open an external project folder
drummer --project ~/projects/my-api

# Custom port
drummer --port 9000 --project ~/projects/my-api
```

## drummer serve

Hidden alias for `drummer` (start the server). Prefer `drummer` directly.

---

## drummer new

Create a new workspace under `~/.drummer/projects/`.

```bash
drummer new NAME
```

Creates a new central workspace directory under `~/.drummer/projects/<slug>` with `project.yaml` and a default `local` environment.

---

## drummer export

Export a Drummer project as a zip file for sharing.

```bash
drummer export PATH
```

---

## drummer mcp

Print MCP server connection information.

```bash
drummer mcp
```

Outputs the URL and port to configure in Claude's MCP settings, and lists all available tools.

---

## Global flags

| Flag | Description |
|---|---|
| `--version` / `-V` | Print version and exit |
| `--attribution` | Print dataset attribution (Metropolitan Museum of Art) and exit |
| `--help` | Show help for any command |
