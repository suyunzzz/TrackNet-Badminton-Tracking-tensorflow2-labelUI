# Change log

## Summary
- Add one-click launchers for the web label tool on Windows and macOS.
- Add PyInstaller packaging scripts so the label tool can be distributed without a separate Python install.
- Update the web label server to load bundled static assets correctly in packaged builds.

## Files changed
- `README.md`: document one-click launchers and no-Python packaging workflow
- `web_label.py`: resolve static asset path for frozen PyInstaller builds
- `打开标注工具.vbs`: delegate to the new Windows launcher
- `start_web_label.bat`: create venv, install dependencies, and start the web label tool on Windows
- `start_web_label.command`: create venv, install dependencies, and start the web label tool on macOS
- `package_web_label.bat`: build a standalone Windows executable with PyInstaller
- `package_web_label.sh`: build a standalone macOS executable with PyInstaller
- `web_label.spec`: bundle static assets and generate macOS app output

## Behavior changes
- Non-engineer users can launch the browser-based label tool with a double-click flow on Windows and macOS.
- Maintainers can build standalone label-tool distributions for end users who do not have Python installed.
- Packaged builds now serve the bundled HTML, CSS, and JS assets correctly.

## Validation
- Ran `bash -n start_web_label.command`
- Ran `bash -n package_web_label.sh`
- Ran `python3 -m py_compile web_label.py parser.py utils.py`
- Started `python3 web_label.py --host 127.0.0.1 --port 8765 --label_video_path test/test.mp4 --csv_path /tmp/tracknet_label_smoke.csv`
- Queried `http://127.0.0.1:8765/api/state` and `http://127.0.0.1:8765/api/annotation?index=0`
- Built the packaged app with `bash package_web_label.sh`
- Started `./dist/web_label --host 127.0.0.1 --port 8766 --label_video_path test/test.mp4 --csv_path /tmp/tracknet_label_binary_smoke.csv`
- Queried `http://127.0.0.1:8766/`, `http://127.0.0.1:8766/static/app.js`, and `http://127.0.0.1:8766/api/state`

## Follow-ups
- PyInstaller warns that macOS `.app` output should move from onefile to onedir mode in a future cleanup.
