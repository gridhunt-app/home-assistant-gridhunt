# Gridhunt for Home Assistant

Custom integration for [Gridhunt](https://gridhunt.app) (collect map tiles by bike).
Cloud polling plus webhooks. Repository: <https://github.com/gridhunt-app/home-assistant-gridhunt>.

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gridhunt-app&repository=home-assistant-gridhunt&category=integration)

## Install (HACS)

1. Open HACS and search for **Gridhunt**. If it is not listed yet: three-dot menu, Custom repositories,
   add `https://github.com/gridhunt-app/home-assistant-gridhunt`, category *Integration*.
2. Download **Gridhunt**, restart Home Assistant.
3. Settings, Devices & services, Add integration, **Gridhunt**.

Requires Home Assistant 2025.4 or newer (Python 3.13). The integration icon is shown from Home Assistant 2026.3.

## Install (manual)

Copy `custom_components/gridhunt` into `/config/custom_components/gridhunt` and restart Home Assistant.

## Configure

Pick one method:

- **Pairing code** (default): the dialog shows a code and a link. Open the link while signed in to
  Gridhunt, approve, then press Submit in Home Assistant.
- **Paste a token**: create one in Gridhunt under Settings, Connections, Home Assistant.

The server address defaults to `https://gridhunt.app`. A revoked token starts a re-authentication prompt.

For instant events Home Assistant needs a public https address (Nabu Casa or your own external URL).
Without it the integration falls back to polling and fires the same events a little later.

## Entities

| Entity | Notes |
|---|---|
| Riding (binary sensor, moving) | on while a ride is recorded |
| Route progress, Distance done, Distance left | only while riding |
| Ride distance, New tiles (this ride) | current ride |
| Square size | current square, falls back to your best square |
| Tiles, New tiles this year | refreshed every 15 minutes |
| Last ride (timestamp) | attributes: name, kind, distanceKm, tiles |
| Position (device tracker) | GPS, only while riding |

Polling: every 20 s while riding, every 60 s otherwise.

## Events

Fired on the Home Assistant bus; use them as automation triggers.

- `gridhunt_ride_started`
- `gridhunt_ride_finished`
- `gridhunt_new_square`
- `gridhunt_test` (the test button in Gridhunt settings)

Event data: `routeName`, `kind`, `startedAt`, `endedAt`, `distanceKm`, `progress`, `tiles`, `square`,
`liveUrl`, `entry_id`, and `source` (`webhook` or `poll`). Each event is fired once even if both arrive.

## Service

`gridhunt.refresh` fetches fresh data immediately (optional `entry_id`).

## Lovelace card

The integration serves `/gridhunt_static/gridhunt-card.js` and loads it automatically.
Add a card of type `custom:gridhunt-card`.

### Ready-made dashboard (one step)

The same file registers a dashboard strategy and a view strategy that build the full Gridhunt view from your entities
(live ride, current ride tiles, account tiles; text in your HA language, Polish or English).

- UI: Settings > Dashboards > Add dashboard > Community dashboards > Gridhunt. If the entry is missing, reload the
  browser page (Ctrl/Cmd+Shift+R) and open the dialog again.
- YAML (dashboard in raw configuration editor):

```yaml
strategy:
  type: custom:gridhunt
```

- Or just one view inside your own dashboard (view strategies cannot be picked in the editor yet):

```yaml
views:
  - strategy:
      type: custom:gridhunt
```

With several Gridhunt accounts the view repeats the sections per account; add `device_id: <device id>` under `strategy`
to limit it to one account. Missing entities are skipped.

## Privacy

Only public tile data and your own rides are exposed. Points inside privacy zones are cut by the server.

## Support

Report bugs at <https://github.com/gridhunt-app/home-assistant-gridhunt/issues>.

## License

MIT, see [LICENSE](LICENSE). Gridhunt is a service of Trop Labs sp. z o.o.
