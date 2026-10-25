# Storm warnings for Home Assistant

A binary sensor that turns on when an official weather warning for your area, yellow or higher,
is in progress or starts within the next 24 hours. It turns off once no warning qualifies. A
blueprint uses it to switch an inverter into backup mode (e.g. Solax via solax_modbus) and back.

| Source                       | Coverage                | Area                                   |
|------------------------------|-------------------------|----------------------------------------|
| Met Éireann                  | Ireland, direct from met.ie | Pick counties from a list          |
| MeteoAlarm                   | ~38 European countries  | Country + EMMA_ID region codes         |
| National Weather Service     | United States           | Map location, defaults to your home    |

## Install

### HACS

1. HACS > Integrations > ⋮ > Custom repositories: add `https://github.com/yoctopidg3/ha-storm-warnings`,
   category Integration.
2. Install "Storm Warnings" and restart Home Assistant.

### Manually

Copy `custom_components/storm_warnings` into your HA `config/custom_components/` and restart.

## Set up

1. Settings > Devices & services > Add integration > **Storm Warnings**.
2. Choose a source, then your area and filters:
   - **Hours of notice**: how long before a warning starts the sensor turns on (default 24).
   - **Minimum level**: yellow, orange or red.
   - **Warning types**: matched as text inside the warning type (NWS: the event name, e.g. "High
     Wind Warning"), so fog or heat warnings don't trigger backup. You can type your own.

   Add the integration again for each extra area. To change the filters later, click **Configure**
   on the entry.

3. Import the blueprint:

   [![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fyoctopidg3%2Fha-storm-warnings%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fstorm_warnings%2Fstorm_backup.yaml)

   Or copy `blueprints/automation/storm_warnings` into `config/blueprints/automation/`.

4. Settings > Automations > Create > from blueprint **Storm backup mode**. Pick the warning sensor
   and the inverter's mode select. For solax_modbus that is `select.solax_charger_use_mode`, and
   the defaults `Back Up Mode` / `Self Use Mode` are already right.

The feed is polled every 15 minutes. If a fetch fails, the sensor keeps its last state, so an
internet outage during a storm will not take you out of backup. When the warning ends, the
blueprint only switches back if the inverter is still in the backup mode, so a mode you set
manually is left alone.

## Severity

Met Éireann and MeteoAlarm use yellow/orange/red directly. NWS severity is mapped:
Moderate = yellow, Severe = orange, Extreme = red; Minor is ignored.

## MeteoAlarm region codes

Country is the name in the feed URL `https://feeds.meteoalarm.org/api/v1/warnings/feeds-COUNTRY`
(e.g. `ireland`, `united-kingdom`, `france`); setup checks that the feed exists. For region codes,
open that URL and look for `"valueName":"EMMA_ID"` next to an `areaDesc` naming your area.
Irish counties use the same codes as met.ie (EI04 Cork, EI07 Dublin, ...).

## Test

`python3 test_matching.py`
