# Target Company List

Source of truth for **which companies** to source jobs from, and **how** each is read.

- `tier` — how the board is readable: `ats` (public JSON) · `browser` (JS/DOM or
  page-fetched API) · `walled` (Cloudflare/DataDome/signed — use manual links) · `manual`.
- `source` — the ATS + slug or URL to read (e.g. `greenhouse:stripe`, `lever:nium`,
  `ashby:ramp`, `smartrecruiters:Wise`, or a careers URL).
- `status` — `pending` · `scraped:<N>` · `no-matches` · `walled` · `manual`.

| company | tier | source | fit (why it matches you) | url | status |
|---------|------|--------|--------------------------|-----|--------|
| Stripe | ats | greenhouse:stripe | Fintech + payments platform; senior/staff PM roles in growth & monetization | https://stripe.com/jobs | scraped:3 |
| Wise | ats | smartrecruiters:Wise | Consumer fintech; lead product roles, London matches location prefs | https://wise.jobs | scraped:3 |
| GetYourGuide | ats | greenhouse:getyourguide | Marketplace/e-commerce; growth & paid-search PM in Berlin | https://getyourguide.careers | scraped:2 |
| Ramp | ats | ashby:ramp | Fintech; fast-growing, top-tier investors; senior product roles | https://ramp.com/careers | no-matches |
