# Provider decision · November 12, 2026

## Selected for the next integration: Duffel, on-demand flight search

The repository implements server-side Duffel v2 return-flight offer requests, economy, 1–9 adults, departing YHZ/YYZ/YUL/HRE. This is a **candidate requiring account activation and real-route validation**, not a claim of approved monitoring access or guaranteed Harare coverage.

- Access: create a Duffel account and start with test mode; activation is required for actual live prices.
- Cost: public USD pricing lists $3/order, 1% Managed Content order value and $0.005/excess search above the 1500:1 search/order ratio. FareScout does not book, so do not assume searches are free. Obtain confirmation of your search-only use and applicable charges before live activation.
- Harare: Duffel's airline list includes Airlink and Ethiopian Airlines; Airlink lists Harare in its network. This supports testing HRE, but does not verify a specific account, route, date, fare or inventory entitlement.
- Monitoring: no scheduler enabled. Confirm permission, retention, rate limits and commercial suitability with Duffel before background monitoring and storing detailed quote history.
- Secrets: server-side environment only. No credential entry in browser forms or source code.

Official references:
- https://duffel.com/pricing
- https://duffel.com/docs/api/offer-requests
- https://help.duffel.com/hc/en-gb/articles/4410085835282-Are-the-flight-prices-in-test-mode-sandbox-real
- https://duffel.com/flights/airlines
- https://www.flyairlink.com/network

## Alternatives

| Source | Access/data | Decision |
|---|---|---|
| Skyscanner | Approved commercial partnership; product and business criteria | Apply after demonstrable product; no dependency on approval |
| Expedia | Partner flight/lodging integrations | Revisit for hotels and packages; access/monitoring permissions unconfirmed |
| Travelpayouts Data API | Token after signup; cache of user searches, retained 2–7 days depending on query | Suitable candidate for inspiration content, not live availability; HRE cache density unverified; no current price claim without data |
| Travelpayouts Search API | Access approval and user-triggered searches; prohibits automatic data collection | Not selected for scheduled tracking |
| Amadeus Self-Service | Official portal says decommissioned July 17 | Do not build against old self-service tutorials |

Official references:
- https://www.partners.skyscanner.net/product/travel-api
- https://developers.expediagroup.com/travel-redirect-api
- https://support.travelpayouts.com/hc/en-us/articles/203956083-Requirements-for-Aviasales-data-API-access
- https://support.travelpayouts.com/hc/en-us/articles/34788165535250-Search-API-usage-rules
- https://developers.amadeus.com/api-catalog

## Setup

1. Get a test token from your Duffel dashboard. Do not send it through chat or commit it.
2. Set `DUFFEL_ACCESS_TOKEN` in the environment running FareScout. `.env.example` is documentation, not an automatically loaded file.
3. Restart `python3 app.py`. The quote form displays TEST MODE and simulated results when test credentials are used.
4. Verify a return search for each airport; record actual routes tested. None have been verified with a real token in this implementation.
5. Only after activation and fee review, install the live token and set `DUFFEL_ALLOW_LIVE=1`. The provider response's `live_mode` determines result labels, not a guessed label from the client.

Searches are manual, with a durable global daily cap (default 20 attempted requests) and 25-second network timeout. There are no automatic retries that could multiply cost. Currency is returned by Duffel, not converted to match a watch budget. Test quotes are never added to real price history. Quotes show expiry, operating carriers and returned fare/conditions data; no booking link is fabricated.

The personal dashboard still needs authentication/owner isolation and production hosting before public deployment. The GitHub repository is public; the app itself is not deployed.
