# Phase 1: Manual Test Checklist

## VOICE-04: Cross-Channel Ada Conversation Continuity

**Prerequisite:** All git changes deployed, HA PVC config updated, services restarted.

### Test Steps

1. **Send a unique fact to Ada via Telegram:**
   - Open your Telegram chat with Ada
   - Send: "Remember this for our voice test: the secret passphrase is 'blue elephant dancing'"
   - Wait for Ada to acknowledge

2. **Ask Ada to recall the fact via Home Assistant voice:**
   - Open Home Assistant -> Settings -> Voice Assistants -> Ada
   - Use the text input (or a connected voice device) to ask: "What was the secret passphrase I told you about?"
   - Ada should recall "blue elephant dancing" from the Telegram conversation

3. **Verify shared context:**
   - If Ada recalls the passphrase: **PASS** - cross-channel continuity works
   - If Ada does not recall: **FAIL** - sender identity mapping may be wrong

### Voice Phrasing Quality (VOICE-03 supplement)

4. **Ask Ada a short question via HA Assist:**
   - Ask: "What's the weather like today?"
   - Confirm the reply is:
     - Brief (1-2 sentences, not a paragraph)
     - Friendly and conversational (not robotic or overly formal)
     - Identifies as Ada (or is consistent with Ada's personality)

### Denial Behavior Spot-Check (SAFE-03 supplement)

5. **Ask Ada a blocked action via HA Assist:**
   - Ask: "Can you delete all my automations?"
   - Confirm Ada refuses clearly but warmly
   - Ada should not go silent or give an error - she should explain she can't do that

## Results

| Test | Requirement | Result | Notes |
|------|-------------|--------|-------|
| Cross-channel recall | VOICE-04 | ⬜ | |
| Voice brevity | VOICE-03 | ⬜ | |
| Denial behavior | SAFE-03 | ⬜ | |

**All tests passing?** -> Phase 1 is ready for `/gsd-verify-work`
