# CLI Reference

## drummer serve

Start the Drummer server and open it in the browser.

```bash
drummer serve [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--project PATH` | none | Path to a Drummer project folder |
| `--port INTEGER` | 8000 | Port to listen on |
| `--host TEXT` | 127.0.0.1 | Host address to bind to |

**Examples:**

```bash
# Open with no project (shows built-in tutorial)
drummer serve

# Open a specific project
drummer serve --project ~/projects/my-api

# Custom port
drummer serve --port 9000 --project ~/projects/my-api
```

---

## drummer new

Create a new Drummer project at the given path.

```bash
drummer new PATH
```

Creates a `.drummer/` directory with `project.yaml` and a default `local` environment at `PATH`.

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
