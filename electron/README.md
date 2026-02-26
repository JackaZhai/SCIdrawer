# SCIdrawer Electron wrapper

This folder provides a thin Electron desktop shell that launches the existing Flask app and opens it in a desktop window.

## Dev run

1) Install Node.js (LTS)
2) From this folder:

```bash
npm install
npm run start
```

## Notes

- The Python backend is started via `python app.py` from the project root.
- Set `PORT` to change the listening port (default `1200`).
- Set `SCIDRAWER_PYTHON` (or legacy `NANO_BANANA_PYTHON`) to point to your Python executable if needed.

Packaging (electron-builder) is not set up yet.

