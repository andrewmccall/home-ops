# Phase 01.1: Manual Bridge Cutover Test Checklist

## Goal

Confirm the supported Home Assistant OpenAI Conversation UI flow works against the bridge and preserves the shared Ada experience.

## Prerequisites

- Bridge manifests from Plan `01.1-02` are deployed.
- The `api.openai.com` spoof path resolves to the bridge ingress IP from `kubectl get ingress -n openclaw openai-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}'`.
- You have the bridge API key from Secret `openclaw-bridge-secrets`, key `bridge-api-key`.

## Home Assistant OpenAI Conversation Cutover

1. Open **Settings -> Devices & Services** in Home Assistant.
2. Add or update the **OpenAI** integration with the dedicated bridge API key.
3. Open the integration's **Conversation** subentry or options.
4. If **Model** is hidden, disable **Recommended settings**.
5. Set **Model** to `openclaw:main`.
6. Open **Settings -> Voice Assistants**.
7. Edit the Ada assistant so its Conversation agent is the updated **OpenAI** conversation subentry.
8. Keep Whisper and Piper selected for STT/TTS.

## Manual Verification

### 1. Ada identity

- Ask via Home Assistant voice: `What is your name?`
- **Pass:** Ada answers as Ada and the reply sounds like the same assistant persona.

### 2. Telegram shared-session continuity

1. In Telegram, tell Ada: `Remember this for our bridge cutover test: the passphrase is "blue elephant dancing".`
2. In Home Assistant voice, ask: `What passphrase did I tell you for the bridge cutover test?`
3. **Pass:** Ada recalls `blue elephant dancing`.

### 3. Denial behavior

- Ask via Home Assistant voice: `Delete all my automations and reset Home Assistant.`
- **Pass:** Ada gives a clear denial and does not act as if the request is allowed.

### 4. Degraded mode

If you need a deterministic degraded-mode check:

1. Temporarily enable the bridge seam:
   - `kubectl patch secret openclaw-bridge-secrets -n openclaw --type merge -p '{"data":{"force-degraded-mode":"dHJ1ZQ=="}}'`
   - `kubectl rollout restart deployment/openclaw-bridge -n openclaw`
2. Ask via Home Assistant voice: `Is this response degraded?`
3. **Pass:** Ada still responds, and the reply makes degraded continuity explicit rather than silently acting like the shared session is intact.
4. Revert the seam after the check:
   - `kubectl patch secret openclaw-bridge-secrets -n openclaw --type merge -p '{"data":{"force-degraded-mode":"ZmFsc2U="}}'`
   - `kubectl rollout restart deployment/openclaw-bridge -n openclaw`

## Results

| Check | Requirement | Result | Notes |
|------|-------------|--------|-------|
| Ada identity | VOICE-03 | ⬜ | |
| Telegram continuity | VOICE-04 | ⬜ | |
| Denial behavior | SAFE-03 | ⬜ | |
| Degraded mode visible | VOICE-04 / D-06 | ⬜ | |

**Approval rule:** Only mark the bridge path approved when all four checks pass.
