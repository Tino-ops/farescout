# FareScout · Built by Tino

A personal travel discovery and price-watch dashboard focused on Black Friday, Cyber Monday and Travel Tuesday. Depart from **Halifax (YHZ), Toronto (YYZ), Montreal (YUL) or Harare (HRE)**.

## Run locally

Requires Python 3.11+; no external dependencies.

```sh
python3 app.py
```

Open http://127.0.0.1:8000. Data persists in `farescout.db`; set `FARESCOUT_DB` to change the path. The server binds to localhost by default.

## What works

- Responsive travel dashboard with original CSS destination illustrations.
- Filter by departure airport, destination, travel category, mood, currency, example price and seasonal campaign.
- Explore general travel ideas without picking a destination first.
- Save and remove trip ideas in a persistent shortlist.
- Create and delete trip targets with dates, adult count, currency and total budget.
- SQLite price observations, threshold notifications and history display.
- Optional SMTP email delivery worker.
- REST API with parameterized queries, validation, same-origin write checks and security headers.

## Honest demo status

**All supplied destinations and prices are fictional examples, not current travel offers.** Nothing is scraped. No Skyscanner, Expedia or Duffel connection is activated. Campaign labels are illustrative; no live promotion is asserted. Prices are not converted across CAD/USD, and package examples are not bookable bundles. Watchlists persist, but saving a watch does not start live monitoring.

2026 campaign calendar: Black Friday Nov 27; Cyber Monday Nov 30; Travel Tuesday Dec 1. The app contains dates rather than a misleading countdown that would expire.

## Connecting a real provider

1. Obtain approved access and verify that scheduled queries, storing observations and displayed/deep-linked results are allowed by its current terms.
2. Implement `provider.search(watch)` for `worker.collect(provider)`; return `None` if no strictly matching offer exists, otherwise `{amount, currency, source}`. `amount` must be the comparable total for all adults. Preserve route, dates, cabin/baggage, or hotel/room/refund/occupancy conditions. Add provider identifiers and comparison dimensions to the schema before tracking heterogeneous offers.
3. Keep API credentials in environment variables or a secret manager. Never in browser JavaScript or Git.
4. Run collection on an external scheduler within provider quotas. The existing worker CLI only delivers queued email; it does not collect prices until you implement and invoke an adapter.
5. Show provider attribution, checked times, expiry and fees when live data is introduced. Add a valid booking link only when the provider supplies it.

Starting points: [Skyscanner partner access](https://www.partners.skyscanner.net/product/travel-api), [Expedia Travel Redirect APIs](https://developers.expediagroup.com/travel-redirect-api), [Duffel documentation](https://duffel.com/docs). Access, pricing, inventory and monitoring permissions must be checked; no claim of full market coverage.

## Alerts

`record_price` stores observations and queues an in-app notification when an offer is within budget and lower than the previous observation (or it is the first observation). It rejects currency mismatches. With SMTP environment variables configured, `python3 worker.py` sends pending notifications. It is a **single-owner** email configuration, not a subscriber system. Delivery retries are at-least-once; a crash between sending and marking delivered can duplicate mail.

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/config` | GET | Airports and connection status |
| `/api/deals` | GET | Explicitly illustrative destination catalogue |
| `/api/watches` | GET / POST | List/create trip targets |
| `/api/watches/delete` | POST | Delete a target and related history |
| `/api/saved` | GET / POST | List/change saved ideas |
| `/api/notifications` | GET | Latest observed-price alerts |

## Verification

```sh
python3 -m unittest discover -s tests -v
node --check static/app.js
```

CI runs the Python integration tests and JavaScript syntax check on pushes and PRs.

## Deployment limits and next milestones

This is a local, single-user MVP, **not a public production booking service**. Python's standard-library HTTP server is for local development. Add authentication, owner-scoped records, CSRF tokens, rate limits, HTTPS, a production server, provider retries/quotas, migration tooling and consent/unsubscribe controls before public multi-user deployment. SQLite must use durable storage. No card data or bookings are processed.

Recommended next work: approved live provider; richer comparable quote schema; scheduled collection; auth; flexible date search; genuine package inventory; booking links; accessibility/browser tests.

## Repository

https://github.com/Tino-ops/farescout

## Duffel flight search integration

The separate flight quote form now calls a server-side Duffel v2 adapter when configured. See [provider decision and setup](docs/PROVIDERS.md). No token is included; no live account or route has been verified. The inspiration catalogue remains illustrative.

`GET /api/provider` exposes connection mode without secrets. `POST /api/flights/search` accepts origin, destination airport code, departure, return_date and adults. Search is user-triggered; test responses remain explicitly simulated. Live use requires `DUFFEL_ALLOW_LIVE=1`; a persistent UTC daily quota defaults to 20 attempts. These are total-party quotes in the provider’s currency. Quote expiry and operating carriers are displayed. No bookings, automatic collection or quote-history writes occur from this endpoint.
