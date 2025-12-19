# Native Installer Troubleshooting

## Windows
- If the app fails to launch, ensure Microsoft Edge WebView2 runtime is installed (required for pywebview).
- If you see missing DLL errors, install the Visual C++ Redistributable.

## macOS
- If you see a warning about unsigned apps, right-click the .app and choose "Open" to bypass Gatekeeper.
- If the app fails to launch, check for missing .dylib dependencies in the Console log.
- For full notarization, see Apple documentation (optional).

## Linux
- If the AppImage does not launch, ensure you have GTK and WebKit2 runtime libraries installed.
- Run `ldd` on the binary to check for missing shared libraries.

## General
- If native file dialogs do not appear, ensure pywebview is bundled and working.
- For browser fallback, run with `--browser` instead of `--native`.
- If you encounter issues, please open an issue on GitHub with your OS and error details.
