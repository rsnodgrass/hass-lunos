# LUNOS Heat Recovery Ventilation for Home Assistant

![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png)
![release_badge](https://img.shields.io/github/v/release/rsnodgrass/hass-lunos.svg)
![release_date](https://img.shields.io/github/release-date/rsnodgrass/hass-lunos.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[![Support on Patreon][patreon-shield]][patreon]
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/DYks67r)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)
[🥈](https://www.home-assistant.io/docs/quality_scale/)

[Community Support](https://community.home-assistant.io/t/lunos-heat-recovery-ventilation-hrv-fan-control/157287)



Provides control of decentralized [LUNOS Heat Recovery Ventilation fans](https://foursevenfive.com/blog/lunos-faq/) using any [Home Assistant](https://www.home-assistant.io/) compatible smart relays.
The design of the LUNOS low-voltage fan controller uses a pair of physical switches (W1/W2) to turn on/off
ventilation, set fan speeds, and to toggle various additional modes such as summertime ventilation, exhaust only modes, etc. See the LUNOS installation details for more information on [how the LUNOS wall switches are installed](https://youtu.be/wQxiYQebs10?t=418).

While this LUNOS integration allows control of the fan modes through Home Assistant apps, web consoles, and connected voice assistants
such as Alexa, the real power comes in supporting a wide variety of automation opportunities when paired with other third-party sensors:

* set LUNOS speeds to maximum when high humidity, CO2, VOCs, or radon is detected

* keeping LUNOS running at lower speeds, EXCEPT when air quality issues are detected, could provide a balance between LUNOS fan noise (which is already a very quiet fan) and maintaining optimal fresh indoor air quality

* increase LUNOS fan speeds to high when kitchen smoke alarm detects smoke

* if outside temperature is closer to target temperature on thermostats, engage exhaust only modes in LUNOS devices to expel indoor air (drawing in temperature that is closer to target from leaks in the building envelope or open windows/doors)

* turn off LUNOS air circulation when house vacation mode is set, and re-activate LUNOS air circulation whenever motion is detected (or someone arrives at the house)

* turn off LUNOS air circulation if outside air quality is detected as being very poor (e.g. nearby forest fires or pollution)

* automatically turn on summer ventilation mode when house is set to sleep mode (and return to normal operating mode upon wakeup or specific time during the day)

## Support

There is no official support for this add-on and is community supported within the **[Home Assistant LUNOS discussion thread](https://community.home-assistant.io/t/lunos-heat-recovery-ventilation-hrv-fan-control/157287)**.
If you have any proposed changes or bug fixes, please code them and create pull requests for your patches to the [hass-lunos GitHub repository](https://github.com/rsnodgrass/hass-lunos).

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)

## Installation

Visit the Home Assistant community if you need [help with installation and configuration of LUNOS Fan Control]().

### Step 1: Install Custom Components

The easiest way to install (and ensure you are always running the latest version), first setup
[Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs), and then add the "Integration" repository: rsnodgrass/hass-lunos

### Step 2: Configure Home Assistant

LUNOS Controllers require a pair of switches (W1 and W2) to control the speed of the fans (as well as other features).
Configuration is required to assign the Home Assistant accessible W1 and W2 switches for the fan controller to use in
operating the LUNOS fan controller.

#### Configuration Variables

- **name** (*Optional*): Friendly name for this fan controller
- **relay_w1** (*Required*): HASS entity id for the relay switch that is connected as W1 to the LUNOS controller
- **relay_w2** (*Required*): HASS entity id for the relay switch that is connected as W2 to the LUNOS controller
- **controller_coding** (*Optional*): Indicates the manual coding the LUNOS controller is set to (default=e2-usa; see [lunos-codings.yaml](custom_components/lunos/lunos-codings.yaml))
- **fan_count** (*Optional*): Number of fans connected to this LUNOS controller
- **default_speed** (*Optional*): Default speed when this LUNOS fan is turned on without any speed indicated

#### Configuration Example

This example configuration assumes that the relay switches are already setup in Home Assistant, since that setup differs
substantially depending on the type of relay hardware being used (e.g. Tasmota MQTT vs WeMo Maker).

```yaml
fan:
  - platform: lunos
    name: Basement Ventilation
    relay_w1: switch.lunos_basement_1
    relay_w2: switch.lunos_basement_2

  - platform: lunos
    name: Bathroom Fan
    default_speed: high
    controller_coding: ego
    relay_w1: switch.lunos_bathroom_1
    relay_w2: switch.lunos_bathroom_2
```

### Step 3: Add Lovelace Card

The following is a basic Lovelace card using the [fan-control-entity-row](https://community.home-assistant.io/t/lovelace-fan-control-entity-row/102952) customization:

![LUNOS Simple Example](https://github.com/rsnodgrass/hass-lunos/blob/master/img/single-fan-control-example.png?raw=true)

```yaml
- entity: fan.lunos_bathroom
  type: custom:fan-control-entity-row
```

And another example with multiple LUNOS ventilation fans and ability to turn on/off the entire house:

![LUNOS Simple Example](https://github.com/rsnodgrass/hass-lunos/blob/master/img/lunos-fan-control-example.png?raw=true)

```yaml
type: entities
title: LUNOS Ventilation
entities:
  - entity: fan.lunos_basement
    name: Basement
    type: 'custom:fan-control-entity-row'
  - entity: fan.lunos_bedrooms
    name: Bedrooms
    type: 'custom:fan-control-entity-row'
  - entity: fan.lunos_bathroom
    name: Master Bathroom
    type: 'custom:fan-control-entity-row'
```

## Automation

### Supported Services

* **lunos_turn_summer_ventilation_on** (only for supported LUNOS e2 models)
* **lunos_turn_summer_ventilation_off**
* **lunos_clear_filter_change_reminder**

### Examples

While using NodeRED can be used to easily create sophisticated (and often easier to understand) ventilation
automation, the following examples showcase a few automations that adjust LUNOS fan speeds based on occupancy
or air quality issues:

Turn on fans when someone arrives:

```yaml
automation:
  - alias: "Turn on LUNOS ventilation fans on when anyone arrives home"
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

Turn LUNOS ventilation fan to highest speed when high humidity is detected:

```yaml
automation:
  - alias: "Turn basement LUNOS ventilation on maximum speed if high humidity is detected"
    trigger:
      - platform: foobot
        entity_id: sensor.basement_humidity
    condition:
      condition: numeric_state
      entity_id: sensor.basement_humidity
      above: 55
    action:
      - service: fan.turn_on
        entity_id: "fan.basement_lunos"
        data:
          speed: "high"

# similar automation required to turn LUNOS to lower speed setting once humidity is within tolerance
```

These same strategies can be used with any Home Assistant compatible devices that track humidity ([ecobee](https://smile.amazon.com/ecobee3-lite-Smart-Thermostat-Black/dp/B06W56TBLN?tag=rynoshark-20), [Nest thermostat](https://amazon.com/Nest-T3007ES-Thermostat-Temperature-Generation/dp/B0131RG6VK/?tag=rynoshark-20)) or,
even better, using air quality measuring devices ([Airthings](https://amazon.com/Airthings-2930-Quality-Detection-Dashboard/dp/B07JB8QWH6/?tag=rynoshark-20), [AirVisual IQAir](https://amazon.com/IQAir-AirVisual-Temperature-Real-Time-Forecasting/dp/B0784TZFRW/?tag=rynoshark-20), [Foobot](https://amazon.com/Foobot-Quality-Monitor-Homeowners-Renters/dp/B06Y8VLCH8?tag=rynoshark-20)) that measure CO2, VOCs, etc.

## Hardware Requirements

* LUNOS e2 HRV fan pairs or [LUNOS eGO HRV fan](https://foursevenfive.com/blog/introducing-the-lunos-ego/)
* LUNOS Universal Controller
* Home Assistant compatible relay

The LUNOS Universal Controller (5/UNI-FT) is powered by a 12V transformer (e.g. the Mean Well #RS-15-12 12V/1.3A/15.6W).
To power more than one LUNOS Controllers and fan sets (plus powering a ESP8266 based WiFi relay) from a single transformer,
it is recommended the LUNOS included 12V transformer be upgraded to a larger unit. For example, the
[Mean Well #RS-50-12](https://amazon.com/MEAN-WELL-RS-50-12-Supply-Single/dp/B005T8WCHC?tag=rynoshark-20) transformer produces up to 50W at 12V.

#### LUNOS Controller Models

| Model    | Number | DIPS | Power          | Notes |
|----------|:------:|:----:|----------------|-------|
| [5/UNI](https://www.youtube.com/watch?v=wQxiYQebs10) | 39975 | None | 60W max load, 12VDC, 5A | Thru April 2022 |
| [5/UNI-FT](https://www.lueftung-shop.de/WebRoot/Store10/Shops/62067764/5665/7B9D/A50F/5108/9D00/C0A8/2ABA/F36B/UNI-FT.pdf) | 40089 |  4   | 60W max load, 12VDC, 5A | European?|
| [5/UNI-FR](https://www.youtube.com/watch?v=JqGWZRYL3q0) | 40269 |  4   | 60W, 12VDC, 5A | April 2022 onwards; released to support e2-60 |

#### WiFi Smart Relays

IMPORTANT: The pair of smart switches CANNOT be 120V switches as they MUST NOT be connected to any power source. For non-smart
installations, the LUNOS Universal Controller typically has non-electrified rocker switches connected as switche W1 and W2. These
are relay switches only and not powered. Any smart switches connected the LUNOS Universal Controller must be relay switches only
with no chance that the LUNOS Controller would be electrified.

While single-channel WiFi relays can be purchased, for centralized control of several LUNOS zones (using several LUNOS Controllers),
purchasing multi-relay modules typically costs less than separate single-channel relays.

Example relays compatible with Home Assistant:

| Model | Relays | Communication | Manual Buttons | Power |
|-------|:------:|:-----------------:|:--------------:|-------|
| [WiFi Relay Switch Module](https://amazon.com/Channel-Momentary-Inching-Self-Locking-Control/dp/B08211H51X/?tag=rynoshark-20) | 4 | Tasmota | Y | 5V USB |
| [Denkovi 8 Relay Ethernet Module](http://denkovi.com/snmp-eight-relay-board-for-temperature-measurement-lm35dz-v2) | 8 | SNMP | N | 12VDC |
| [MHCOZY 4CH-CS01 4-channel WiFI wireless switch](https://amazon.com/Channel-Momentary-Inching-Self-lock-Controller/dp/B071KFX63R/?tag=rynoshark-20) | 4 | Tasmota | N | 5-32V |
| [LC Technology 4X WiFi Relay (12V ESP8266)](https://www.banggood.com/DC12V-ESP8266-Four-Channel-Wifi-Relay-IOT-Smart-Home-Phone-APP-Remote-Control-Switch-p-1317255.html) | 4 | Tasmota | N | 12V |

#### Tasmota Setup

After flashing your multi-channel WiFi relay with Sonoff, you must connect to it via the Sonoff WiFi to access the Sonoff
web configuration interface.

* configure the Sonoff relay device to connect to your WiFi network
* enable auto-discovery (for automatic Home Assistant integration)
* configure the MQTT broker host/user/password that your Home Assistant instance uses
* configure the [Tasmota switches](https://github.com/arendst/Tasmota/wiki/Buttons-and-switches)

In the Sonoff web interface Console, turn on auto discovery (option 19) so Home Assistant can find your relays:

```
SetOption19 on
```

Then you must configure in Sonoff web interface the address and username/password for the
MQTT broker that Home Assistant uses.

For more information on flashing ESP8266 based relays:

* https://community.home-assistant.io/t/diy-cheap-3-esp8266-based-wifi-relay-switch-with-mqtt/40401
* https://github.com/arendst/Tasmota/wiki/LC-Technology-WiFi-Relay

#### Example Wiring with [MHCOZY 4CH WiFi RF Wireless Switch Relay](https://amazon.com/gp/product/B07TDJG2GJ?tag=rynoshark-20)

![LUNOS 4-Chan WiFi Case Example](https://github.com/rsnodgrass/hass-lunos/blob/master/img/lunos-switch-case.png?raw=true)

You need to put the 4-Channel smart relay into latching mode. Depending on the size of your 12V transformer, the MHCOZY can also be powered off the same 12V transformer used by the LUNOS controllers.

The only downside of the relay switch is that the four pins (GND, VCC, TXD, RXD) are solder filled which makes it difficult to temporarily hook up wires to flash Tasmota.

#### Example Wiring with ESP8266 WiFi Relay

The following is an example connecting a [LC Technology 12V ESP8266 Four-Channel WiFi Relay](https://www.banggood.com/DC12V-ESP8266-Four-Channel-Wifi-Relay-IOT-Smart-Home-Phone-APP-Remote-Control-Switch-p-1317255.html) to the LUNOS Controller.
Additional controllers that should work including the [Sonoff 4CH](https://amazon.com/Sonoff-4CH-Appliances-independently-Compatible/dp/B071JB5LXR?tag=rynoshark-20).

![LUNOS ESP8266 Example](https://github.com/rsnodgrass/hass-lunos/blob/master/img/lunos-esp8266.png?raw=true)

### Wireless and Alexa Integration

One idea for a clean physical LUNOS switch installation is assigning a [Lutron Caséta Pico Fan Speed Controller](http://www.lutron.com/TechnicalDocumentLibrary/Caseta_Fan_Control_Sell_Sheet.pdf) (PD-FSQN-WH-R) to a
LUNOS fan within Home Assistant allows extremely slick and simple control of a LUNOS fan in a single gang outlet box in
an occupied space. The larger W1 and W2 control switches can then be "hidden" in a utility room or closet.

Additionally, once added to Home Assistant, LUNOS fan speeds can be configured to be controlled by
Alexa or other voice enabled smart speaker.

## Currently Not Supported

* attribute indicating current ventilation mode: [standard, summer, exhaust-only] (standard = hrv)
* special handling of exhaust only ventilation mode (eGO models)
* fan controller modes that support a fourth flow rate (either when it can never be shut off, *OR* the turbo mode when W1 is pressed twice)
* LUNOS type RA 15-60 radial duct fan
* [LUNOS Smart Comfort Control 5/SC-FT](https://www.lunos.de/files/Downloads/Einbauanleitungen/Funktionsbeschreibung_Folientastatur.pdf)

#### LUNOS Control4 KMX Module Consistency

Ideally, we would update this integration to follow naming/conventions similar to what LUNOS provides with the the Control4 [KMX](https://www.home-assistant.io/integrations/knx/) module (which, btw, may provide an alternative way of integrating LUNOS ventilation with Home Assistant).

* Comfort mode (HVAC)
* Standby operation (HVAC)
* Night operation (HVAC)
* Temperature protection mode (HVAC)
* Shock ventilation (extended HVAC mode)
* Sleep (Off) (extended HVAC mode)
* Summer mode (switch object)
* Night operation (switch object)

## Known Issues

* IMPROVEMENT: manual fan speed changes are not immediately detected (only on 30 second interval updates)

## Future Ideas

* allow setting direction of fans individually (async_set_direction), exhaust only, balanced intake air for fireplace, etc (flag SUPPORT_DIRECTION)
* add more of the control features patterned off the [LUNOS 5/SC-FT](https://www.lunos.de/files/Downloads/Einbauanleitungen/Funktionsbeschreibung_Folientastatur.pdf)

## See Also

* [Home Assistant LUNOS support discussion](https://community.home-assistant.io/t/lunos-heat-recovery-ventilation-hrv-fan-control/157287)
* [LUNOS Ventilation FAQ](https://foursevenfive.com/blog/lunos-faq/)
* [Intro to LUNOS Heat Recovery Ventilation](https://foursevenfive.com/blog/introduction-to-lunos-e-heat-recovery-ventilation/)
* [LUNOS Operating Manual](https://foursevenfive.com/content/product/ventilation/lunos_e2/operating_manual_lunos_e2.pdf)
* [LUNOS](https://www.lunos.de/en/) (official site) and [475 High Performance Supply](https://foursevenfive.com/lunos-e/) (USA LUNOS distributor)
* [LUNOS Control4 KMX module](https://www.lunos.de/en/product/control4-e/) (KNX-LUNOS-CONTROL4) appears to offer sensor data such as indoor/outdoor temp
* [eWeLink Sonoff Device Control in Home Assistant](https://sonoff.tech/product-review/tutorial/how-to-add-your-sonoff-devices-on-home-assistant/)
* [LUNOS Advanced Controller Settings - 40269](https://store-b79re8owlk.mybigcommerce.com/content/product/ventilation/lunos_e2/advanced_controller_settings_guide.pdf)




[patreon]: https://www.patreon.com/rsnodgrass
[patreon-shield]: https://img.shields.io/endpoint.svg?url=https%3A%2F%2Fshieldsio-patreon.vercel.app%2Fapi%3Fusername%3Drsnodgrass%26type%3Dpatrons&style=for-the-badge
