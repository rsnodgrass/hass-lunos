# LUNOS Fan Control for Home Assistant

***NOT YET IMPLEMENTED***

The LUNOS integration provides control for LUNOS [e2](https://foursevenfive.com/lunos-e/) or [eGO](https://foursevenfive.com/lunos-ego/) heat-recovery ventilation fans using pairs of on/off smart switches. Per the design of the LUNOS low-voltage fan controller, a pair of switches are used to turn on/off the fan and control the speed settings. See the LUNOS installation manual for more information.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)

## Installation

Visit the Home Assistant community if you need [help with installation and configuration of LUNOS Fan Control]().

### Step 1: Install Custom Components

Easiest installation is by setting up [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs), and then adding the "Integration" repository: rsnodgrass/hass-lunos.

However you can also manually copy all the files in [lunos/](https://github.com/rsnodgrass/hass-lunos/custom_components/lunos) directory to `/config/custom_components/lunos` on your Home Assistant installation.

### Step 2: Configure Fans

Example configuration:

```yaml
lunos:
  - name: "Bedroom Ventilation"
    switches:
      - switch.lunos_bedrooms_1
      - switch.lunos_bedrooms_2
  - name: "Basement Ventilation"
    switches:
      - switch.lunos_basement_1
      - switch.lunos_basement_2
  - name: "Bathroom Fan"
    default_speed: high
    switches:
      - switch.lunos_bathroom_1
      - switch.lunos_bathroom_2
```

### Step 3: Add Lovelace Card

The following is a simple Lovelace card using the [fan-control-entity-row](https://community.home-assistant.io/t/lovelace-fan-control-entity-row/102952):

```yaml
- entity: fan.sunroom_fan
  type: custom:fan-control-entity-row
  name: Basement Ventilation
```

### Automation Examples

```yaml
automation:
  - alias: "Turn on LUNOS ventilation fans on when we get home"
    trigger:
      - platform: state
        entity_id: group.people
        to: "home"
    action:
      - service: fan.turn_on
        entity_id: "fan.lunos"
        data:
          speed: "high"
```

## See Also

* [LUNOS](https://www.lunos.de/en/) (official product page)
* [475 (USA distributor)](https://foursevenfive.com/lunos-e/)
* [Intro to Lunos Heat Recovery Ventilation](https://foursevenfive.com/blog/introduction-to-lunos-e-heat-recovery-ventilation/)

## Feature Requests

* service turn_on / turn_off
* service set_speed (low, medium, high)
* example of poor air quality and auto-turning up the fan (e.g. Foobot or Airwave)
