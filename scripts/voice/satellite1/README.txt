Satellite1 local wake-word workflow
==================================

This workflow keeps custom Ada / Hey Ada microWakeWord work local to this repo
while cloning the upstream firmware and training repositories on demand.

Main entry point:
  bash scripts/voice/satellite1-local-wakeword.sh help

Typical flow:
  1. Copy scripts/voice/satellite1-wakeword.env.example to
     scripts/voice/satellite1-wakeword.env and adjust values if needed.
  2. Run:
       bash scripts/voice/satellite1-local-wakeword.sh setup
  3. Prepare a local notebook copy and sample/model directories:
       bash scripts/voice/satellite1-local-wakeword.sh prepare-training
  4. Train Ada and Hey Ada locally with the copied notebook and/or upstream
     micro-wake-word tooling.
  5. Put the resulting TFLite files here:
       scripts/voice/satellite1/models/ada.tflite
       scripts/voice/satellite1/models/hey_ada.tflite
  6. Optionally add your own recordings here for local experimentation:
       scripts/voice/satellite1/samples/ada/
       scripts/voice/satellite1/samples/hey_ada/
       scripts/voice/satellite1/samples/negative/
       scripts/voice/satellite1/samples/background/
  7. Generate manifests:
       bash scripts/voice/satellite1-local-wakeword.sh manifest \
         --name ada --wake-word "Ada" --input scripts/voice/satellite1/models/ada.tflite
       bash scripts/voice/satellite1-local-wakeword.sh manifest \
         --name hey_ada --wake-word "Hey Ada" --input scripts/voice/satellite1/models/hey_ada.tflite
  8. Patch the checked-out Satellite1 firmware and compile:
       bash scripts/voice/satellite1-local-wakeword.sh compile
  9. Flash over USB (preferred) or OTA:
       bash scripts/voice/satellite1-local-wakeword.sh upload

Notes:
  - The upstream notebook already includes background-noise, ambient-negative,
    and reverb augmentation paths.
  - The sample directories above are repo-local staging points for any extra
    recorded positives or negatives you want to fold into your own local
    training experiments.
  - The helper patches FutureProofHomes/Satellite1-ESPHome/config/common/
    voice_assistant.yaml in the local checkout only. It does not modify this
    repo's tracked firmware manifests.
