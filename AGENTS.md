# Agent Instructions

## Release Process

To release a new version:

1. **Update version in manifest.json**
   ```bash
   # Edit custom_components/lunos/manifest.json
   # Change "version": "X.Y.Z" to new version
   ```

2. **Update CHANGELOG.md**
   - Add new version section at the top
   - Include date in format `## X.Y.Z (YYYY-MM-DD)`
   - List all changes as bullet points

3. **Update RELEASE_NOTES**
   - Edit `custom_components/lunos/RELEASE_NOTES`
   - Brief summary of changes for this release

4. **Commit version bump**
   ```bash
   git add custom_components/lunos/manifest.json CHANGELOG.md custom_components/lunos/RELEASE_NOTES
   git commit -m "Bump version to X.Y.Z"
   ```

5. **Create GitHub release**
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes-file CHANGELOG.md
   ```
   Or create with inline notes:
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes "Release notes here"
   ```

### Notes

- **hacs.json** does not require version updates (uses `render_readme: true`)
- HACS pulls version from `manifest.json`
- Tag format: `vX.Y.Z` (with `v` prefix)
