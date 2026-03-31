# Runtime Environment

You run in a hardened Kubernetes pod. The root filesystem is read-only.

## Writable paths

| Path | Backed by | Persists across restarts |
|------|-----------|------------------------|
| ~/.openclaw/ | PVC | Yes |
| ~/.local/ | PVC | Yes |
| ~/.cache/ | PVC | Yes |
| /tmp | emptyDir | No |

Everything else is read-only. Do NOT attempt writing to system paths.

## Installing packages

uv is pre-installed at ~/.local/bin/uv and already in your PATH.
~/.local/bin is in your PATH. All user-level installs persist across restarts.

### Python packages

```bash
# Install a Python package
pip install <package-name>
```

### Python CLI tools (isolated)

```bash
# Install a CLI tool (creates an isolated env, adds binary to PATH)
uv tool install <tool-name>
```

### Node.js (npm / npx)

npm global installs and npx are pre-configured to use writable paths.

```bash
# Install a global package
npm install -g <package-name>

# Run a one-off package
npx <package-name>
```

### Static binaries

```bash
curl -L <url> -o ~/.local/bin/<tool> && chmod +x ~/.local/bin/<tool>
```

## What does NOT work

- **apt-get / sudo / su** - no root access, the root filesystem is read-only
- **Writing to /usr, /etc, /var** - read-only system directories
- **HTTP downloads (port 80)** - blocked by network policy; use HTTPS (port 443) instead

If you need system-level packages (e.g. C libraries for compilation), ask the administrator
to provide a custom container image with those dependencies pre-installed.
