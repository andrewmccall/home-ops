# Ada Proxy — Home Assistant Voice Pipeline

OpenAI-compatible proxy that connects Home Assistant's voice pipeline to OpenClaw's model (via OpenRouter), giving you "Ada" as a voice assistant.

## Architecture

```
Satellite 1 → HA → Whisper (STT) → OpenAI conv. agent → ada-proxy → OpenRouter
                                                                              ↓
Satellite 1 ← HA ← Piper (TTS) ←────────────────────────────────────────────┘
```

## Files

- `server.py` — Python/FastAPI proxy server
- `Dockerfile` — Container build
- `ada-proxy.yaml` — HelmRelease for k3s
- `secrets-template.yaml` — Secret template (encrypt with SOPS)
- `ha-config-snippet.yaml` — HA config additions
- `kustomization.yaml` — Kustomize resource list

## Setup

### 1. Build the image

Push to `main` and the GitHub Actions workflow (`.github/workflows/ada-proxy-build.yaml`) will build and push to `ghcr.io/andrewmccall/ada-proxy:latest`.

Or build manually:
```bash
docker build -t ghcr.io/andrewmccall/ada-proxy:latest cluster/apps/house/ada-proxy/
docker push ghcr.io/andrewmccall/ada-proxy:latest
```

### 2. Create the encrypted secret

```bash
# Create the SOPS-encrypted secret
cp cluster/apps/house/ada-proxy/secrets-template.yaml cluster/apps/house/ada-proxy/secrets.enc.yaml

# Edit and add your OpenRouter API key
# Then encrypt with SOPS (same key as your other secrets)
sops --encrypt --in-place cluster/apps/house/ada-proxy/secrets.enc.yaml
```

### 3. Update the HelmRelease image tag

After CI builds the image, update `ada-proxy.yaml` with the SHA tag, or keep `latest` with `pullPolicy: Always` for dev.

### 4. Configure Home Assistant

Add to `configuration.yaml` (via code-server or config PVC):

```yaml
openai_conversation:
  - api_base: http://ada-proxy.house.svc.cluster.local:8000/v1
    api_key: "unused"
    model: openrouter/hunter-alpha
    name: Ada
```

Then in **Settings > Voice Assistants**:
1. Create new assistant → Name: "Ada"
2. Conversation agent: "Ada" (OpenAI integration)
3. STT: "Whisper" (wyoming, already configured)
4. TTS: "Piper" with voice `en_GB-alan-medium`
5. Assign to your Satellite 1

### 5. Test

Say your wake word and try:
- "What's the weather?"
- "Turn on the living room lights"
- "Tell me a joke"

## Customization

Edit `SYSTEM_PROMPT` in the HelmRelease `env` block or in `server.py` to change Ada's personality.

## API Endpoints

- `GET /v1/models` — List available models
- `POST /v1/chat/completions` — Chat completions (OpenAI-compatible)
- `GET /health` — Health check
