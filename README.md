# HA Cartel

Home Assistant custom integration that polls [Obmenka exchange rates](https://api.obmenka.dn.ua:5001/course?org=2) every hour and creates Buy/Sell sensors for a selected city/office.

## Install via HACS

1. Open **HACS** → **Integrations** → menu (⋮) → **Custom repositories**
2. Add `https://github.com/sniffy1988/ha_cartel` as category **Integration**
3. Search for **HA Cartel**, install, then restart Home Assistant
4. Go to **Settings** → **Devices & services** → **Add integration** → **HA Cartel**
5. Pick a city, then an office

You can add the integration multiple times for different offices.

## Sensors

Home Assistant sensors have a single numeric state, so each rate is its own entity:

| Name | Source |
| --- | --- |
| **USD Buy** / **USD Sell** | cash (`rates`) |
| **USD Buy Opt** / **USD Sell Opt** | cashless (`ratesOpt`), only when present |
| **EUR/USD Buy** / **EUR/USD Sell** | cross (`ratesCross`) |
| **EUR/USD Buy Opt** / … | cross cashless (`ratesCrossOpt`), only when present |

FX-vs-UAH sensors use unit `UAH`. Cross-rate sensors use the quote currency (e.g. `USD`).

## Configuration

UI config flow only. No YAML configuration.

## Data source

Rates are fetched from:

`https://api.obmenka.dn.ua:5001/course?org=2`

Poll interval: **1 hour**.

## License

MIT
