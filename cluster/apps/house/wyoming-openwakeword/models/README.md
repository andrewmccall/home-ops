# Wake-word model training

Train one `.tflite` file per phrase with the Home Assistant wake-word training flow:

1. Open the training guide: <https://www.home-assistant.io/voice_control/create_wake_word/>
2. Launch the linked Colab notebook.
3. Set `target_word` to `Ada`, preview and tweak pronunciation, then run **Runtime -> Run all**.
4. Keep the generated `.tflite` output and ignore the `.onnx` file.
5. Repeat the same flow for `Hey Ada`.

Place the outputs here with these exact names:

- `ada.tflite`
- `hey_ada.tflite`

Then update `MODEL.md` with:

- `source_workflow_run`
- `generated_at`
- `phrases`
- `approved_by`
- `notes`

After both files exist, run:

```bash
bash scripts/voice/render-wakeword-configmap.sh
```

That command rewrites `../wakeword-models.yaml` with the model payloads and checksum annotations.
