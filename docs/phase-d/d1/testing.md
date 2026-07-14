# Testing Guidelines — Phase D, Sub-Phase D1: Consolidated Zone Configuration

This document describes the testing requirements, unit tests, and verification procedures for **Phase D, Sub-Phase D1 (Consolidated Zone Configuration)** of the IGNIS system.

---

## Testing Prerequisites

Sub-Phase D1 consolidates the zone configurations into a unified configuration schema (`config/zones_config.json`) and implements configuration merging.
- **Python Version**: Python 3.10+.
- **Test Path**: Run commands from the project root (`d:\projects\IGNIS`).

---

## Automated Unit Testing

We developed a unit test `test_config_merge_defaults` inside `tests/test_lateral_coordination.py` specifically to validate config loading and default merging behavior.

### Test Cases and Coverage

1. **Config Merge & Overrides Validation (`test_config_merge_defaults`)**:
   - Mocks the structure of `config/zones_config.json` containing a `defaults` block and a `zones` block.
   - Configures `self.zone_id` to `"4C"`.
   - Calls `load_config` on the mock configuration layout.
   - Asserts that the default dictionary keys (such as custom sensor weights or timeouts) are parsed and retained.
   - Asserts that zone-specific parameters (such as `zone_name`, `neighbors`, and overrides) successfully overwrite default values.
   - Asserts that `zone_id` is properly appended to the resulting config object.

### Running the Unit Test

To run this specific unit test, execute the following command:
```bash
python -m unittest tests/test_lateral_coordination.py -k test_config_merge_defaults
```

Expected output:
```text
.
----------------------------------------------------------------------
Ran 1 test in 0.003s

OK
```
