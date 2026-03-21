# Change log

## Summary
- Add a browser-based labeling tool for video frame annotation with csv-compatible output.
- Show the active label file, per-frame status, and overall review progress in the UI.
- Improve usability with Mac-friendly shortcuts, autosave, and quick navigation to unchecked frames.

## Files changed
- `.gitignore`: ignore Python cache files and generated web label progress files.
- `web_label.py`: add a lightweight HTTP labeling server backed by OpenCV frame access and csv persistence.
- `web_label_static/index.html`: add the web labeling layout and controls.
- `web_label_static/styles.css`: style the labeling UI for readability and responsive use.
- `web_label_static/app.js`: implement frame loading, annotation actions, autosave, progress display, and keyboard shortcuts.
- `README.md`: document how to launch and use the web label workflow.

## Behavior changes
- Users can annotate labels in a local browser instead of relying only on the OpenCV desktop window.
- The web UI distinguishes checked no-ball frames from unchecked frames using a `.weblabel.json` sidecar file.
- On Mac, users can jump to the first or last frame with `⌘ + ←` and `⌘ + →`, with `[` and `]` as fallback shortcuts.

## Validation
- Ran `python3 -m py_compile web_label.py imgLabel.py parser.py utils.py`.
- Instantiated `LabelSession` against `test/test.mp4` and verified annotation, no-ball marking, frame retrieval, csv save, and sidecar save behavior.
