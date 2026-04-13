---
phase: 02
slug: satellite-1-voice-launch
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-13
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | shell smoke tests + manual physical Satellite 1 verification |
| **Config file** | none |
| **Quick run command** | `bash scripts/voice/check-wakeword-rollout.sh` |
| **Full suite command** | `bash scripts/voice/smoke-satellite1-e2e.sh && bash scripts/voice/check-manual-fallback.sh && bash scripts/voice/check-pipeline-failure-response.sh` |
| **Estimated runtime** | ~60 seconds for shell checks plus live Satellite 1 verification |

---

## Sampling Rate

- **After every task commit:** run the narrowest shell check for the touched surface (`render-wakeword-configmap.sh`, `smoke-satellite1-runtime.sh`, `check-wakeword-rollout.sh`, or the full Phase 2 suite once Satellite 1 is bound)
- **After every plan wave:** run the full shell suite plus the current manual checklist for wake word / routing / fallback / failure behavior
- **Before `/gsd-verify-work`:** full shell suite must be green and the physical-device approval steps in `MANUAL-TEST.md` must be signed off
- **Max feedback latency:** 60 seconds for shell checks; <5 minutes for physical-device confirmation

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | WAKE-02 | T-02-01 / T-02-02 / T-02-03 | Wake-word runtime is isolated from Home Assistant, Whisper, and Piper and exposes the fixed model mount contract on `10400` | static | `grep -q "rhasspy/wyoming-openwakeword" cluster/apps/house/wyoming-openwakeword/wyoming-openwakeword.yaml && grep -q "10400" cluster/apps/house/wyoming-openwakeword/wyoming-openwakeword.yaml && grep -q "wakeword-models" cluster/apps/house/wyoming-openwakeword/wyoming-openwakeword.yaml && ! grep -q "wyoming-openwakeword" cluster/apps/house/kustomization.yaml` | ✅ | ⬜ pending |
| 02-01-02 | 01 | 1 | WAKE-02 | T-02-01 / T-02-02 | Model render and rollout tooling exist before activation | smoke | `bash -n scripts/voice/render-wakeword-configmap.sh && bash -n scripts/voice/smoke-satellite1-runtime.sh && bash -n scripts/voice/check-wakeword-rollout.sh` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | WAKE-02 | T-02-04 | External wake-word artifacts are present, named correctly, and have recorded provenance before activation | checkpoint + static | `test -s cluster/apps/house/wyoming-openwakeword/models/ada.tflite && test -s cluster/apps/house/wyoming-openwakeword/models/hey_ada.tflite && shasum -a 256 cluster/apps/house/wyoming-openwakeword/models/ada.tflite cluster/apps/house/wyoming-openwakeword/models/hey_ada.tflite && grep -q "source_workflow_run" cluster/apps/house/wyoming-openwakeword/models/MODEL.md` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | WAKE-02 | T-02-05 / T-02-06 | Rendering and rollout prove model refreshes only touch the wake-word release | smoke | `bash scripts/voice/render-wakeword-configmap.sh && bash scripts/voice/smoke-satellite1-runtime.sh && bash scripts/voice/check-wakeword-rollout.sh` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | VOICE-01 / VOICE-02 / WAKE-01 / WAKE-03 / SAFE-01 | T-02-07 / T-02-08 / T-02-09 / T-02-10 | Cutover docs and scripts name the exact Satellite 1 bind, wake-word selection, manual fallback, and bridge-health failure-announce path | static | `bash -n scripts/voice/smoke-satellite1-e2e.sh && bash -n scripts/voice/check-manual-fallback.sh && bash -n scripts/voice/check-pipeline-failure-response.sh && grep -q "wyoming-openwakeword.house:10400" cluster/apps/openclaw/instance/ha-config-snippet.yaml && grep -q "openclaw-bridge.openclaw.svc.cluster.local:4000/healthz" .planning/phases/02-satellite-1-voice-launch/CUTOVER-CHECKLIST.md && grep -q "assist_satellite.announce" .planning/phases/02-satellite-1-voice-launch/CUTOVER-CHECKLIST.md` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 3 | VOICE-01 / VOICE-02 / WAKE-01 / WAKE-03 / SAFE-01 | T-02-07 / T-02-08 / T-02-09 / T-02-10 | The live Home Assistant config binds one Satellite 1 entity, keeps manual Assist, and installs the bridge-health failure announce package | smoke + checkpoint | `grep -q "!include_dir_named packages" /config/configuration.yaml && grep -q "ada_voice_bridge_healthy" /config/packages/ada_voice_failure.yaml && grep -q "openclaw-bridge.openclaw.svc.cluster.local:4000/healthz" /config/packages/ada_voice_failure.yaml && grep -q "assist_satellite.announce" /config/packages/ada_voice_failure.yaml && bash scripts/voice/smoke-satellite1-e2e.sh && bash scripts/voice/check-manual-fallback.sh && bash scripts/voice/check-pipeline-failure-response.sh` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 3 | VOICE-01 / VOICE-02 / WAKE-01 / WAKE-03 / SAFE-01 | T-02-07 / T-02-08 / T-02-09 | The physical device proves `Ada` / `Hey Ada`, same-device playback, manual fallback, and spoken failure behavior | manual + smoke | `bash scripts/voice/smoke-satellite1-e2e.sh && bash scripts/voice/check-manual-fallback.sh && bash scripts/voice/check-pipeline-failure-response.sh` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/voice/render-wakeword-configmap.sh` — deterministic `binaryData` render for `wakeword-models.yaml`
- [ ] `scripts/voice/smoke-satellite1-runtime.sh` — wake-word service health and model-mount smoke check
- [ ] `scripts/voice/check-wakeword-rollout.sh` — verify model refresh blast radius stays inside the wake-word release
- [ ] `.planning/phases/02-satellite-1-voice-launch/CUTOVER-CHECKLIST.md` — exact Satellite 1 binding + HA package steps
- [ ] `.planning/phases/02-satellite-1-voice-launch/MANUAL-TEST.md` — physical-device approval checklist for wake word, routing, fallback, and failure behavior
- [ ] `scripts/voice/smoke-satellite1-e2e.sh` — same-device round-trip smoke script for the live Satellite 1 path
- [ ] `scripts/voice/check-manual-fallback.sh` — wake-word outage fallback check
- [ ] `scripts/voice/check-pipeline-failure-response.sh` — bridge-health failure announce verification

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `Ada` and `Hey Ada` both wake the bound Satellite 1 device | WAKE-01 | Physical mic pickup and wake-word quality are device- and room-dependent | Stand near Satellite 1, say `Ada`, then `Hey Ada`, and confirm the device wakes and routes the request through the configured Ada assistant both times |
| Reply audio stays on the initiating Satellite 1 speaker | VOICE-02 | Wrong-target playback is a room-level UX outcome | Ask a short question after a successful wake and confirm the spoken reply comes from the same device, not another room |
| Failure announcement is audible and explicit | SAFE-01 | The final user-facing outcome is spoken audio, not only state changes | Trigger the bridge-health failure scenario and confirm Satellite 1 audibly says `Ada isn't available right now. Hold the Assist button and try again in a moment.` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify commands or Wave 0 coverage
- [ ] Sampling continuity: no 3 consecutive tasks without automated feedback
- [ ] Wave 0 covers all missing scripts/docs referenced above
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s for shell checks
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
