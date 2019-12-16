# LUNOS Fan Control for Home Assistant

***NOT YET IMPLEMENTED***

The LUNOS integration provides control for LUNOS [e2](https://foursevenfive.com/lunos-e/) or [eGO](https://foursevenfive.com/lunos-ego/) heat-recovery fans using two on/off smart switches.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)

## Installation

Visit the Home Assistant community if you need [help with installation and configuration of LUNOS Fan Control]().

### Step 1: Install Custom Components

Easiest installation is by setting up [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs), and then adding the "Integration" repository: rsnodgrass/hass-lunos.

However you can also manually copy all the files in [lunos/](https://github.com/rsnodgrass/hass-lunos/custom_components/lunos) directory to `/config/custom_components/flo` on your Home Assistant installation.

### Step 2: Configure Sensors

Example configuration:

```yaml
switches:
  - platform: lunos
    switch_1: switch.lunos_1
    switch_2: switch.lunos_2
```

### Step 3: Add Lovelace Card

The following is a simplest Lovelace card which shows data from the Flo sensors:

```yaml
type: entities
entities:
  - entity: fan.lunos_fan_1
```

## See Also

# [475: Intro to Lunos Heat Recovery Ventilation](https://foursevenfive.com/blog/introduction-to-lunos-e-heat-recovery-ventilation/)
* [LUNOS](https://www.lunos.de/en/) (official product page)

## Feature Requests

* service turn_on / turn_off
* service set_speed (low, medium, high)
