# HA Cartel

Home Assistant custom integration that polls [Obmenka exchange rates](https://api.obmenka.dn.ua:5001/course?org=2) every hour and exposes one sensor per currency (or cross pair) for a selected city/office.

## Install via HACS

1. Open **HACS** → **Integrations** → menu (⋮) → **Custom repositories**
2. Add `https://github.com/sniffy1988/ha_cartel` as category **Integration**
3. Search for **HA Cartel**, install, then restart Home Assistant
4. Go to **Settings** → **Devices & services** → **Add integration** → **HA Cartel**
5. Pick a city, then an office

You can add the integration multiple times for different offices.

## Sensors

One sensor per `val` (and cross `val`/`to_val`), with multiple values as attributes:

| Sensor | State | Attributes |
| --- | --- | --- |
| **USD** | cash buy (fallback: opt buy) | `buy`, `sell`, and if present `buy_opt`, `sell_opt` |
| **EUR** | same | same |
| **EUR/USD** | cross buy | same for `ratesCross` / `ratesCrossOpt` |

Example for office `59`:

- `sensor.…_usd` → state `44.50`, attributes `buy=44.50`, `sell=45.05`, `buy_opt=44.65`, `sell_opt=45.05`
- `sensor.…_eur_usd` → cross rates with buy/sell(/opt) attributes

FX-vs-UAH sensors use unit `UAH`. Cross-rate sensors use the quote currency (e.g. `USD`).

## Configuration

UI config flow only. No YAML configuration.

## Data source

Rates are fetched from:

`https://api.obmenka.dn.ua:5001/course?org=2`

Poll interval: **1 hour**.

## License

MIT
