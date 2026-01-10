## 1.0.0 (2026-01-10)

Major modernization release for Home Assistant 2024.12+ standards.

### Breaking Changes
- Minimum Home Assistant version is now 2024.12.0
- YAML configuration is deprecated; please migrate to UI-based configuration
- Service names changed from `lunos_*` to `lunos.*` format

### New Features
- UI-based configuration via config flow with modern Selectors
- Options flow for reconfiguring existing entries
- Diagnostics support for troubleshooting
- DataUpdateCoordinator pattern for centralized state management
- Proper device registry integration with device info

### Improvements
- Full type hints throughout codebase
- Modern entity patterns with `has_entity_name` and translation keys
- Push-based updates via relay state change listeners
- Entity services registered via platform service registration
- Comprehensive test suite for config flow, coordinator, and entities
- Updated manifest.json with `integration_type`, `iot_class: local_push`
- Structured translations in `strings.json` and `translations/en.json`

### Code Quality
- Replaced `os.path` with `pathlib`
- Using `yaml.safe_load` instead of `yaml.full_load`
- Proper logging with `LOG = logging.getLogger(__name__)`
- Clean imports and PEP 8 compliance
- Added ruff, mypy configuration in pyproject.toml

## 0.4.0 (2026-01-10)

- Fixed bug where switching to low speed incorrectly shows medium in UI
- Fixed percentage scale (was showing off as 25%, low as 50%; now shows off without percentage, low at 33%)
- Modernized code according to Home Assistant fan spec (deprecated speed property)

## 0.3.1 (2025)

- Added type hints and improved `_update_speed`
- Updated issue tracker URL and cleaned up code formatting

## 0.3.0 (2022-06)

- Updates to meet fan requirements for Home Assistant 2022.06
- Added new presets for summer, eco (normal mode), and each of the fan speeds by name

## 0.0.1 - BETA (2019-12-23)

Initial release of two-switch controller for LUNOS e2 and EGO fans
