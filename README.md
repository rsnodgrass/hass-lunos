# LUNOS Heat Recovery Ventilation for Home Assistant

***NOT YET IMPLEMENTED***

Provides control of [LUNOS Heat Recovery Ventilation fans](https://foursevenfive.com/blog/lunos-faq/) (e2/eGO) using pairs of smart on/off relays. Per the design of the LUNOS low-voltage fan controller, a pair of switches (W1/W2) are used to turn on/off the fans and set the speed settings by setting the switches to specific combinations. See the LUNOS installation details for more information on [how the LUNOS wall switches are installed](https://youtu.be/wQxiYQebs10?t=418).

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)

## Installation

Visit the Home Assistant community if you need [help with installation and configuration of LUNOS Fan Control]().

### Step 1: Install Custom Components

Easiest installation is by setting up [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs), and then adding the "Integration" repository: rsnodgrass/hass-lunos.

However you can also manually copy all the files in [lunos/](https://github.com/rsnodgrass/hass-lunos/custom_components/lunos) directory to `/config/custom_components/lunos` on your Home Assistant installation.

### Step 2: Configure Fans

This example configuration assumes that the relay switches are already setup in Home Assistant, since that
setup differs substantially depending on what type of relay hardware you are using (e.g. MQTT with ESP8266 vs WeMo Maker).

```yaml
lunos:
  - name: "Bedroom Ventilation"
    relay_w1: switch.lunos_bedrooms_w1
    relay_w2: switch.lunos_bedrooms_w2
  - name: "Basement Ventilation"
    entity: fan.lunos_basement_ventilation
    relay_w1: switch.lunos_basement_w1
    relay_w2: switch.lunos_basement_w2
  - name: "Bathroom Fan"
    default_speed: high
    relay_w1: switch.lunos_bathroom_w1
    relay_w2: switch.lunos_bathroom_w2
```

### Step 3: Add Lovelace Card

The following is a simple Lovelace card using the [fan-control-entity-row](https://community.home-assistant.io/t/lovelace-fan-control-entity-row/102952):

```yaml
- entity: fan.lunos_bathroom
  type: custom:fan-control-entity-row
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


## Hardware

* LUNOS e2 HRV fan pairs or [LUNOS eGO HRV fan](https://foursevenfive.com/blog/introducing-the-lunos-ego/)
* NOTE: LUNOS Universal Controller (5/UNI-FT) is powered by a 12V transformer (such as Mean Well #RS-15-12 12V/1.3A/15.6W)

While single-channel WiFi relays can be purchased, for centralized control of several LUNOS zones (using
several LUNOS Controllers), purchasing multi-relay modules typically costs less than separate single-channel relays.

Example Home Assistant compatible relays (most can be flashed with Tasmota/MQTT):

| Model | Relays | Tasmota Supported | Manual Buttons | Power |
|-------|:------:|:-----------------:|:--------------:|-------|
| [WiFi Relay Switch Module](https://amazon.com/Channel-Momentary-Inching-Self-Locking-Control/dp/B08211H51X/?tag=rynoshark-20) | 4 | Y | Y | 5V USB |
| [MHCOZY 4-channel WiFI wireless switch](https://amazon.com/Channel-Momentary-Inching-Self-lock-Controller/dp/B071KFX63R/?tag=rynoshark-20) | 4 | Y | N | 5-32V |
| [LC Technology 12V ESP8266 Four-Channel WiFi Relay](https://www.banggood.com/DC12V-ESP8266-Four-Channel-Wifi-Relay-IOT-Smart-Home-Phone-APP-Remote-Control-Switch-p-1317255.html) | 4 | Y | N | 12V |

#### MQTT Setup

```yaml
```

#### ESP8266 WiFi Relay

For example, the [LC Technology 12V ESP8266 Four-Channel WiFi Relay](https://www.banggood.com/DC12V-ESP8266-Four-Channel-Wifi-Relay-IOT-Smart-Home-Phone-APP-Remote-Control-Switch-p-1317255.html) or


## Supported Smart Relays

IMPORTANT: The pair of smart switches CANNOT be 120V switches as they MUST NOT be connected to any power source.
For non-smart installations, the LUNOS Universal Controller typically has non-electrified rocker switches connected
as switche W1 and W2. These are relay switches only and not powered. Any smart switches connected the LUNOS Universal
Controller must be relay switches only with no chance that the LUNOS Controller would be electrified.

### EASY OPTION ($$$): Belkin WeMo Maker

The [Belkin WeMo Maker](https://www.belkin.com/uk/p/P-F7C043/) (F7C043) is the recommended option for novices as the Maker
is UL-listed, uses a standard USB-based power adapter that plugs into any wall outlet, keeps the 120V circuit completely
separate from the relay side (since it is powered by a 5V/1A micro USB cable), and communicates over WiFi
Since the WeMo Maker is powered by a 5V/1A micro USB cable, no electrical inspection should be required for the
install and wiring of this to a LUNOS Universal Controller.

Two WeMo Makers are required. The WeMo relay contacts should be connected to the LUNOS Universal Controller in
similar setup to the ESP8266 version. Both of the WeMo Makers should have their switch type configured in WeMo
software to be in Toggle mode.

The downside of this approach is the WeMo Maker is expensive ($80+), and two are required.

### MEDIUM DIFFICULTY OPTION ($): ESP8266 WiFi Relay with Sonoff/MQTT ($)

Using an ESP8266 based WiFi relay (with Sonoff support, such as the [12V ESP8266 Dual WiFi Relay Module](https://www.banggood.com/12V-ESP8266-Dual-WiFi-Relay-Module-Internet-Of-Things-Smart-Home-Mobile-APP-Remote-Switch-p-1276094.html))
is a very inexpensive model (under $10 for a relay module that can support up to two independent LUNOS Controllers).
The ESP8266 module can share an upsized 12V transformer with LUNOS Universal Controller.

![LUNOS ESP8266 Example](https://github.com/rsnodgrass/hass-lunos/blob/master/img/lunos-esp8266.png?raw=true)

The downside is that this requires the ESP8266 device to manually be flashed with Sonoff firmware to support
easy integration into Home Assistant. For detail on flashing the LC Technology ESP8266 WiFi Relays with Sonoff/MQTT, see:

* https://community.home-assistant.io/t/diy-cheap-3-esp8266-based-wifi-relay-switch-with-mqtt/40401
* https://github.com/arendst/Tasmota/wiki/LC-Technology-WiFi-Relay

If you want to operate two independent LUNOS Controllers, it is recommended the 12V transformer be upgraded
to a larger unit, like the Mean Well #RS-50-12 transformer, which produces up to 50W at 12V.

### Other Alternatives

* USB relays (such as [2-port](https://relaypros.com/Relay/Relay/CAT_RELAY2_USB))
* Raspberry Pi with various relay module

Also note, to meet code requirements, 120V circuits must be separated from any low-voltage circuit. These approaches are for advanced users only:

* Pair of [Tuya Wi-Fi Switch Module Relay](https://amazon.com/Momentary-Inching-Self-Locking-90-264V-Compatible/dp/B07ZV73ZV7/?tag=rynoshark-20) with L(out) and first relay contact wire nut connected as W1 or W2 to LUNOS Controller

### Wireless and Alexa Integration

For a clean LUNOS installation, assigning a [Lutron Caséta Pico Fan Speed Controller](http://www.lutron.com/TechnicalDocumentLibrary/Caseta_Fan_Control_Sell_Sheet.pdf) (PD-FSQN-WH-R) to a LUNOS fan within Home Assistant allows extremely slick and simple control of a LUNOS fan in a single gang outlet box in an occupied space. The larger W1 and W2 control switches can then be "hidden" in a utility room or closet.

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

## Feature Requests

* service turn_on / turn_off
* service set_speed (low, medium, high)
* example of poor air quality and auto-turning up the fan (e.g. Foobot or Airwave)
* add 3 second delay between state changes (bug fix)

* support for wiring filter LED light to a smart sensor (such as WeMo Maker sensor input)
* NOTE: flipping W2 (right) on/off within 3 seconds activates Summer ventilation mode
* WARNING: flipping W1 within 3 seconds clears the filter warning light

## Not Supported

* enabling the summer/night ventilation mode (e2)
* eGO exhaust only modes
* e2 four-flow rate mode (non-US models)
* LUNOS type RA 15-60 radial duct fan

