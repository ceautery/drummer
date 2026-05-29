# MCP Tools

Drummer exposes a Model Context Protocol (MCP) server so Claude can send requests, inspect responses, and manage environments directly.

## Setup

1. Start Drummer: `drummer`
2. Add to your Claude MCP configuration:

```json
{
  "mcpServers": {
    "drummer": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Run `drummer mcp` to confirm the URL and list available tools.

## Available tools

| Tool | Description |
|---|---|
| `list_projects` | List all known projects with metadata |
| `list_requests` | Get the request tree for a project |
| `get_request` | Get the parsed definition of a request |
| `create_request` | Create a new request file |
| `update_request` | Update fields in an existing request |
| `send_request` | Fire a request; returns status, headers, body, timing, script output |
| `get_history` | Recent response history for a request |
| `list_environments` | List environments for a project |
| `get_variables` | Get variables for a named environment |
| `set_variable` | Set a variable in the active environment |
| `switch_environment` | Change the active environment |
| `clear_cookies` | Clear the session cookie store |

## Example workflow

```
list_projects
→ [{ "name": "My API", "id": "my-api" }]

list_requests { "project_id": "my-api" }
→ [{ "path": "users/list-users.md", "name": "List Users" }]

send_request { "project_id": "my-api", "path": "users/list-users.md" }
→ { "status_code": 200, "elapsed_ms": 142, "body": "[{\"id\":1,...}]" }

set_variable { "project_id": "my-api", "env": "local", "key": "base_url", "value": "https://staging.example.com" }

send_request { "project_id": "my-api", "path": "users/list-users.md" }
→ { "status_code": 200, "elapsed_ms": 98, "body": "[...]" }
```
