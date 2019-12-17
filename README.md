# LUNOS Heat Recovery Ventilation for Home Assistant

Provides control of decentralized [LUNOS Heat Recovery Ventilation fans](https://foursevenfive.com/blog/lunos-faq/) using any Home Assistant compatible smart relays. The LUNOS low-voltage fan controller is designed to be controlled using a pair of switches (W1/W2) to turn on/off
ventilation, to set fan speeds, and to toggle various additional modes. See the LUNOS installation details for more
information on [how the LUNOS wall switches are installed](https://youtu.be/wQxiYQebs10?t=418).

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
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

Configuration variables:
- **name** (*Optional*): Friendly name for this fan controller.
- **relay_w1** (*Required*): The HASS entity id for the relay switch that is connected as W1 to the LUNOS controller.
- **relay_w2** (*Required*): The HASS entity id for the relay switch that is connected as W2 to the LUNOS controller.
- **controller_coding** (*Optional*): Slug indicating the manual coding the LUNOS controller is set to (see lunos-codings.yaml).
- **fan_count** (*Optional*): The number of fans connected to this LUNOS controller.
- **default_speed** (*Optional*): The default speed when this LUNOS fan is turned on without any speed indicated.

#### Configuration Example

This example configuration assumes that the relay switches are already setup in Home Assistant, since that setup differs
substantially depending on the type of relay hardware being used (e.g. Tasmota MQTT vs WeMo Maker).

```yaml
fan:
  - platform: lunos
    name: Bedroom Ventilation
    relay_w1: switch.lunos_bedrooms_w1
    relay_w2: switch.lunos_bedrooms_w2
  
  - platform: lunos
    name: Basement Ventilation
    controller_coding: e2-usa
    entity: fan.lunos_basement_ventilation
    relay_w1: switch.lunos_basement_w1
    relay_w2: switch.lunos_basement_w2

  - platform: lunos
    name: Bathroom Fan
    default_speed: high
    controller_coding: ego
    relay_w1: switch.lunos_bathroom_w1
    relay_w2: switch.lunos_bathroom_w2
```

### Step 3: Add Lovelace Card

The following is a simple Lovelace card using the [fan-control-entity-row](https://community.home-assistant.io/t/lovelace-fan-control-entity-row/102952):

```yaml
- entity: fan.lunos_bathroom
  type: custom:fan-control-entity-row
```

### Step 4 (Optional): Automation

While using NodeRED can be used to easily create ventilation automation, here are several example manual
automations that change the LUNOS fan speeds based on occupancy or air quality issues:

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

# similar automation required to turn LUNOS back down to lower speed setting once humidity is within tolerance
```

These same strategies can be used with any Home Assistant compatible devices that track humidity ([ecobee](https://smile.amazon.com/ecobee3-lite-Smart-Thermostat-Black/dp/B06W56TBLN?tag=rynoshark-20), [Nest thermostat](https://amazon.com/Nest-T3007ES-Thermostat-Temperature-Generation/dp/B0131RG6VK/?tag=rynoshark-20)) or,
even better, using air quality measuring devices ([Airthings](https://amazon.com/Airthings-2930-Quality-Detection-Dashboard/dp/B07JB8QWH6/?tag=rynoshark-20), [AirVisual IQAir](https://amazon.com/IQAir-AirVisual-Temperature-Real-Time-Forecasting/dp/B0784TZFRW/?tag=rynoshark-20), [Foobot](https://amazon.com/Foobot-Quality-Monitor-Homeowners-Renters/dp/B06Y8VLCH8?tag=rynoshark-20)) that measure CO2, VOCs, etc.

Automatically turning up LUNOS when high CO2 or VOCs are detected can provide a great balance between LUNOS fan noise (which
is already a very quiet fan) and maintaining optimal fresh indoor air quality.

### Supported Services

* **lunos_turn_summer_ventilation_on** (only for supported LUNOS e2 models)
* **lunos_turn_summer_ventilation_off**
* **lunos_clear_filter_change_reminder**

## Hardware Requirements

* LUNOS e2 HRV fan pairs or [LUNOS eGO HRV fan](https://foursevenfive.com/blog/introducing-the-lunos-ego/)
* LUNOS Universal Controller
* Home Assistant compatible relay

The LUNOS Universal Controller (5/UNI-FT) is powered by a 12V transformer (e.g. the Mean Well #RS-15-12 12V/1.3A/15.6W).
To power more than one LUNOS Controllers and fan sets (plus powering a ESP8266 based WiFi relay) from a single transformer,
it is recommended the LUNOS included 12V transformer be upgraded to a larger unit. For example, the
[Mean Well #RS-50-12](https://amazon.com/MEAN-WELL-RS-50-12-Supply-Single/dp/B005T8WCHC?tag=rynoshark-20) transformer produces up to 50W at 12V.

#### WiFi Smart Relays

IMPORTANT: The pair of smart switches CANNOT be 120V switches as they MUST NOT be connected to any power source. For non-smart
installations, the LUNOS Universal Controller typically has non-electrified rocker switches connected as switche W1 and W2. These
are relay switches only and not powered. Any smart switches connected the LUNOS Universal Controller must be relay switches only
with no chance that the LUNOS Controller would be electrified.

While single-channel WiFi relays can be purchased, for centralized control of several LUNOS zones (using several LUNOS Controllers),
purchasing multi-relay modules typically costs less than separate single-channel relays.

Example relays compatible with Home Assistant:

| Model | Relays | Tasmota Supported | Manual Buttons | Power |
|-------|:------:|:-----------------:|:--------------:|-------|
| [WiFi Relay Switch Module](https://amazon.com/Channel-Momentary-Inching-Self-Locking-Control/dp/B08211H51X/?tag=rynoshark-20) | 4 | Y | Y | 5V USB |
| [MHCOZY 4-channel WiFI wireless switch](https://amazon.com/Channel-Momentary-Inching-Self-lock-Controller/dp/B071KFX63R/?tag=rynoshark-20) | 4 | Y | N | 5-32V |
| [LC Technology 4X WiFi Relay (12V ESP8266)](https://www.banggood.com/DC12V-ESP8266-Four-Channel-Wifi-Relay-IOT-Smart-Home-Phone-APP-Remote-Control-Switch-p-1317255.html) | 4 | Y | N | 12V |

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

#### Example Wiring with [WiFi Relay Switch Module](https://amazon.com/Channel-Momentary-Inching-Self-Locking-Control/dp/B08211H51X/?tag=rynoshark-20)

![LUNOS 4-Chan WiFi Case Example](https://github.com/rsnodgrass/hass-lunos/blob/master/img/lunos-switch-case.png?raw=true)

#### Example Wiring with ESP8266 WiFi Relay

The following is an example connecting a [LC Technology 12V ESP8266 Four-Channel WiFi Relay](https://www.banggood.com/DC12V-ESP8266-Four-Channel-Wifi-Relay-IOT-Smart-Home-Phone-APP-Remote-Control-Switch-p-1317255.html) to the LUNOS Controller.

![LUNOS ESP8266 Example](https://github.com/rsnodgrass/hass-lunos/blob/master/img/lunos-esp8266.png?raw=true)

### Wireless and Alexa Integration

For a clean LUNOS installation, assigning a [Lutron Caséta Pico Fan Speed Controller](http://www.lutron.com/TechnicalDocumentLibrary/Caseta_Fan_Control_Sell_Sheet.pdf) (PD-FSQN-WH-R) to a
LUNOS fan within Home Assistant allows extremely slick and simple control of a LUNOS fan in a single gang outlet box in
an occupied space. The larger W1 and W2 control switches can then be "hidden" in a utility room or closet.

Additionally, once added to Home Assistant, LUNOS fan speeds can be configured to be controlled by
Alexa or other voice enabled smart speaker.

## See Also

* [LUNOS Ventilation FAQ](https://foursevenfive.com/blog/lunos-faq/)
* [Intro to Lunos Heat Recovery Ventilation](https://foursevenfive.com/blog/introduction-to-lunos-e-heat-recovery-ventilation/)
* [LUNOS](https://www.lunos.de/en/) (official site)
* [475 High Performance Supply](https://foursevenfive.com/lunos-e/) (USA distributor)
* [LUNOS Operating Manual](https://foursevenfive.com/content/product/ventilation/lunos_e2/operating_manual_lunos_e2.pdf)

* https://community.home-assistant.io/t/fibaro-rgbw-to-switch-fan-controller/104872
* https://github.com/arendst/Tasmota/wiki/LC-Technology-WiFi-Relay

## Currently Not Supported

## TODO

* BUG: does NOT detect the current relay switch state to determine current speed on startup
* BUG: add 3+ second delay between state changes

### Currently Not Supported

* automatic speed detection based on relay changes (e.g. manual change or delayed switch update)
* add attribute indicating ventilation mode: [standard, summer, exhaust-only] (standard = hrv)
* exhaust only ventilation mode (eGO models)
* fan controllers modes which support a fourth flow rate setting (either when it can never be shut off, *OR* the turbo mode when W1 is pressed twice)
* LUNOS type RA 15-60 radial duct fan
* LUNOS e2 Neo decibal level attributes
