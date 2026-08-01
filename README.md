# HA Cartel

Home Assistant custom integration that polls [Obmenka exchange rates](https://api.obmenka.dn.ua:5001/course?org=2) every hour and exposes Buy/Sale sensors for a selected city/office.

## Install via HACS

1. Open **HACS** → **Integrations** → menu (⋮) → **Custom repositories**
2. Add `https://github.com/sniffy1988/ha_cartel` as category **Integration**
3. Search for **HA Cartel**, install, then restart Home Assistant
4. Go to **Settings** → **Devices & services** → **Add integration** → **HA Cartel**
5. Pick a city, then an office

You can add the integration multiple times for different offices.

## Sensors

For the selected office the integration creates sensors from:

- **Cash** rates (`rates`) — Buy and Sale per currency
- **Cashless** rates (`ratesOpt`) — Buy and Sale per currency

Example entity IDs (office `59`):

| Entity | Meaning |
| --- | --- |
| `sensor.ha_cartel_59_cash_usd_buy` | Cash USD buy |
| `sensor.ha_cartel_59_cash_usd_sale` | Cash USD sale |
| `sensor.ha_cartel_59_cashless_usd_buy` | Cashless USD buy |

State values are numeric (UAH). Attributes include city, office id, rate type, currency, side, and API date.

## Configuration

UI config flow only. No YAML configuration.

## Data source

Rates are fetched from:

`https://api.obmenka.dn.ua:5001/course?org=2`

Poll interval: **1 hour**.

## License

MIT
