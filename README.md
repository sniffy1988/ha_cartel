# HA Cartel

Home Assistant custom integration that polls [Cartel.in.ua](https://cartel.in.ua/) exchange rates for **Kharkiv office #1** (458-1, пр. Науки 7) every hour and creates Buy/Sell sensors.

## Install via HACS

1. Open **HACS** → **Integrations** → menu (⋮) → **Custom repositories**
2. Add `https://github.com/sniffy1988/ha_cartel` as category **Integration**
3. Search for **HA Cartel**, install, then restart Home Assistant
4. Go to **Settings** → **Devices & services** → **Add integration** → **HA Cartel**
5. Confirm setup — only one Kharkiv office is supported

## Sensors

Home Assistant sensors have a single numeric state, so each rate is its own entity:

| Name | Source |
| --- | --- |
| **USD Buy** / **USD Sell** | cash (`rates`) |
| **USD Buy Opt** / **USD Sell Opt** | cashless (`ratesOpt`), only when present |
| **EUR/USD Buy** / **EUR/USD Sell** | cross (`ratesCross`) |
| **EUR/USD Buy Opt** / **EUR/USD Sell Opt** | cross cashless (`ratesCrossOpt`), only when present |

FX-vs-UAH sensors use unit `UAH`. Cross-rate sensors use the quote currency (e.g. `USD`).

## Configuration

UI config flow only. No YAML configuration. One config entry per Home Assistant instance (office id 37).

## Data source

Rates are fetched from Cartel’s server proxy:

`POST https://cartel.in.ua/includes/admin_content_funcs.php` (`action=get-rates`)

Upstream course data is synced from Obmenka on Cartel’s server (the public site no longer calls Obmenka directly from the browser).

Poll interval: **1 hour**.

## License

MIT
