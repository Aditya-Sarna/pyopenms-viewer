# Publishing Native Installers to GitHub Releases

When a new version tag (e.g., v1.2.3) is pushed to the repository, the GitHub Actions workflow in `.github/workflows/build-native.yml` will:

1. Build native installers for Windows, macOS, and Linux using PyInstaller.
2. Upload the resulting artifacts to the GitHub Release for that tag.

## How it works
- On tag push, the workflow builds the app for each OS and uploads the contents of the `dist/` directory as release assets.
- Users can download the appropriate installer from the "Releases" page on GitHub.

## Manual Release Steps (if needed)
If you need to manually upload an installer:
1. Build the app locally using PyInstaller.
   ```bash
   python -m PyInstaller --noconfirm --onedir --windowed --name pyopenms-viewer \
	   --collect-all pyopenms --collect-all plotly --additional-hooks-dir=. \
	   pyopenms_viewer/__main__.py
   ```
2. Go to the GitHub Releases page for your repo.
3. Click "Edit" on the relevant release, and upload the installer file(s).

## Notes
- Artifacts are unsigned by default. See TROUBLESHOOTING.md for platform-specific notes on unsigned apps.
- For code signing and notarization, see the next section.
