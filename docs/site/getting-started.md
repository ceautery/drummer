# Getting Started

## Requirements

- macOS or Linux
- Python 3.12+

## Install

**Homebrew (macOS):**

```bash
brew tap ceautery/drummer
brew install drummer
```

**pip:**

```bash
pip install drummer
```

## Create a project

A Drummer project is a folder with a `.drummer/` directory. Create one by hand:

```
my-api/
├── .drummer/
│   ├── project.yaml
│   └── environments/
│       └── local.yaml
└── list-users.md
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
```

**`list-users.md`**

```markdown
---
name: List Users
method: GET
url: "{{base_url}}/users"
---
```

## Start Drummer

```bash
drummer --project /path/to/my-api
```

Drummer starts on port 8000. Open `http://localhost:8000` in your browser. Select your environment in the sidebar, click **Send**, and see the response.

## Built-in tutorial

Run `drummer`, then click the **Tutorial** button in the top bar. The tutorial walks through all of Drummer's features using an offline mock API — no internet required.

## What's next

- [CLI Reference](cli-reference.md) — all commands and flags
- [Scripting API](scripting-api.md) — pre/post-request JavaScript
- [MCP Tools](mcp-tools.md) — connect Claude to Drummer
