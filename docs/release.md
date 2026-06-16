# Release Notes

Release automation lives in `.github/workflows/release.yml` and is manually triggered with a version tag.

## Required Secrets

- `TAURI_PRIVATE_KEY` and `TAURI_KEY_PASSWORD` for signed Windows Tauri bundles.
- `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, and `ANDROID_KEY_PASSWORD` for Android release signing.

## Jobs

- `docker-build` builds the API container image for the requested version.
- `windows-desktop` installs Node/Rust dependencies, runs the Vite build, runs `tauri build`, and uploads MSI/NSIS bundle artifacts.
- `android-mobile` installs Node/Java dependencies, decodes the release keystore, runs `gradle assembleRelease`, and uploads APK/AAB outputs.

Keep signing secrets out of the repository. Use environment-specific release approvals before distributing artifacts outside the family-office environment.
