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

Entity names: the device is called **Gridhunt**, so the entities are `binary_sensor.gridhunt_riding`,
`sensor.gridhunt_tiles`, `device_tracker.gridhunt_position` and so on ("Gridhunt Riding", "Gridhunt Tiles"); your
account name does not appear in them. With more than one Gridhunt account in Home Assistant the first one keeps
"Gridhunt" and every next one is named "Gridhunt <account name>" (for example `sensor.gridhunt_jan_tiles`) so the
ids do not collide. Updating from 0.1.12 or older renames the old ids (`sensor.<account>_tiles` to
`sensor.gridhunt_tiles`) once, only those you have not renamed yourself and only when the new id is free. Update
your own dashboards, automations and scripts that still use the old ids.

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

## Sidebar panel

After setup the integration adds a **gridhunt** item with the Gridhunt mark to the Home Assistant sidebar (`/gridhunt`).
It opens a ready-made view, generated from your entities: the Gridhunt card with the map, your position map, and the
"Current ride" and "Account" sections, with Riding, Tiles and Square badges on top. Nothing to set up and nothing to edit:
the view follows your entities. With several accounts there is one item showing all of them.

- Turn it off: Settings > Devices & services > Gridhunt > Configure > "Show Gridhunt in the sidebar". The item disappears
  at once, no restart. With several accounts the item stays while any account has the option on.
- Want to edit it? Admins see "Editable copy" in the panel header: it creates a new dashboard (`/gridhunt-copy`) with the
  view written out, which you can change like any dashboard ("take control"). The panel itself stays generated.
- If another panel already uses `/gridhunt`, the item is not added (warning in the log).

## Privacy

Only public tile data and your own rides are exposed. Points inside privacy zones are cut by the server.

## Support

Report bugs at <https://github.com/gridhunt-app/home-assistant-gridhunt/issues>.

## License

MIT, see [LICENSE](LICENSE). Gridhunt is a service of Trop Labs sp. z o.o.
