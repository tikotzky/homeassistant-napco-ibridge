# Napco iBridge for Home Assistant

[![hacs][hacsbadge]][hacs]
[![License][license-shield]](LICENSE)
![Project Maintenance][maintenance-shield]

Home Assistant integration for Napco GEM-series alarm panels that expose an **iBridge** module. Talks to the panel over the local network (no cloud), uses the same binary protocol that the Napco mobile app uses, and ships an alarm-control-panel entity plus sensors for the keypad display, LED states, and panic shortcuts.

![Napco iBridge](custom_components/napco_ibridge/brand/icon.png)

## Features

- **100% local** — TCP socket directly to the iBridge on port 8000; no Napco cloud, no account required.
- **Auto-discovery** — UDP broadcast finds the panel on your LAN, or enter the IP manually.
- **Push updates** — long-lived TCP connection: the keypad display, arm state, and LED indicators stream in real time.
- **Arm / disarm from HA** — a standard `alarm_control_panel` entity with `armed_home`, `armed_away`, `armed_night`, and `arming` states.
- **Optional saved user code** — store it in the config entry and HA arms/disarms silently; leave it blank and HA prompts on every disarm.
- **Panic buttons** — one-press Fire / Ambulance / Police shortcuts.
- **Service action `napco_ibridge.send_keys`** — script any arbitrary keypad sequence (handy for bypass, function menus, programming, etc.).

## Entities

This integration creates **one device per panel** and the following entities:

| Platform              | Entity                            | Purpose                                                                                                                                    |
| --------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `alarm_control_panel` | Panel                             | Primary control. Maps the iBridge arm-state to `disarmed` / `armed_home` / `armed_away` / `armed_night` / `arming`.                        |
| `sensor`              | Display                           | The two-line keypad display, combined into one string.                                                                                     |
| `sensor`              | Arm state                         | Raw enum (`disarm`, `stay`, `away`, `night`, `arming_*`, `not_ready`). Useful for automations that need finer state than HA's alarm panel. |
| `binary_sensor`       | Trouble                           | `device_class: problem` — on when the panel's Trouble LED is anything but Off.                                                             |
| `binary_sensor`       | Fire                              | `device_class: smoke` — on when the Fire LED is lit.                                                                                       |
| `binary_sensor`       | Fire trouble                      | `device_class: problem` — on when the Fire Trouble LED is lit.                                                                             |
| `binary_sensor`       | Bypass active                     | On when one or more zones are bypassed.                                                                                                    |
| `binary_sensor`       | Sounder                           | `device_class: sound` — on while the panel is making noise.                                                                                |
| `button`              | Panic — Fire / Ambulance / Police | Sends the corresponding panic key.                                                                                                         |

## Arm sequence mapping

The integration speaks the same wire-protocol as the keypad, so arm actions are simply long-press keystrokes:

| Action    | Sent to panel                                   |
| --------- | ----------------------------------------------- |
| Arm Away  | long-press `ButtonInstantAway` (no code)        |
| Arm Home  | long-press `ButtonInteriorStay` (no code)       |
| Arm Night | long-press `ButtonInteriorStay` twice (no code) |
| Disarm    | user-code digits + `ButtonOnOffEnter`           |

## Services

### `napco_ibridge.send_keys`

Send an arbitrary ordered sequence of keypad buttons. Each chip is one keystroke; you can add the same button multiple times (e.g. `Button1`, `Button1`, `Button1`, `Button1`, `ButtonOnOffEnter` to type "1111 + Enter").

```yaml
action: napco_ibridge.send_keys
data:
  keys:
    - Button1
    - Button1
    - Button5
    - Button6
    - ButtonOnOffEnter
```

The action also accepts raw integer button codes for power users. Available button names: `Button0`–`Button9`, `ButtonStar`, `ButtonBreak`, `ButtonStartBreak`, `ButtonShift0`–`ButtonShift9`, `ButtonOnOffEnter`, `ButtonOnOffEnter2`, `ButtonReset`, `ButtonNext`, `ButtonYes`, `ButtonInteriorStay`, `ButtonInteriorStayLong`, `ButtonPrev`, `ButtonNo`, `ButtonInstantAway`, `ButtonInstantAwayLong`, `ButtonBypass`, `ButtonF`, `ButtonA`, `ButtonP`, `ButtonFunctionMenu`, `ButtonZoneDirectory`, `ButtonLongPrefix`.

## Installation

### HACS (recommended)

1. Open HACS → Integrations → **⋮** → Custom repositories.
2. Add `https://github.com/tikotzky/homeassistant-napco-ibridge` with category **Integration**.
3. Install "Napco iBridge" and restart Home Assistant.

### Manual

Copy `custom_components/napco_ibridge/` from this repo into your Home Assistant `config/custom_components/` directory, then restart Home Assistant.

## Configuration

After installation:

1. **Settings → Devices & Services → Add Integration → Napco iBridge.**
2. Pick **Auto-discover panel** (UDP broadcast on the LAN) or **Enter IP manually**.
3. Optionally enter your user code:
   - Filled in → HA arms/disarms silently using the stored code.
   - Left blank → HA prompts for the code on each disarm action.

The user code can be added, changed, or cleared later via the integration's **Configure** button (options flow).

## Network requirements

- The iBridge listens on **TCP port 8000** for control traffic.
- Discovery uses a **UDP broadcast on port 30717**. If your panel and Home Assistant aren't on the same broadcast domain, use manual IP entry.
- The integration holds a persistent TCP connection and polls status every second. The panel only supports a single client connection — if the Napco mobile app is also connected, one of them will disconnect.

## Logo / branding

The integration ships its own logo at `custom_components/napco_ibridge/brand/`. Home Assistant 2026.3+ serves these locally with no brands repo PR needed.

## Acknowledgements

- The wire-protocol implementation is a Python port of the `node-napco-ibridge` reverse-engineering work in this repo's parent directory.
- Project structure based on [`jpawlowski/hacs.integration_blueprint`](https://github.com/jpawlowski/hacs.integration_blueprint).

## License

MIT — see [LICENSE](LICENSE).

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/tikotzky/homeassistant-napco-ibridge.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40tikotzky-blue.svg?style=for-the-badge
