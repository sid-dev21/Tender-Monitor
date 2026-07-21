# Interface mockups — Tender Monitor

Rendered from the revised Stitch HTML with headless Chromium at **2x**,
1440 px CSS width. Tailwind is compiled locally and the fonts and logo are
embedded, so nothing is fetched from a CDN.

| File | Screen |
|---|---|
| 01_login.png | Login |
| 02_registration.png | Registration |
| 03_dashboard.png | Dashboard |
| 04_tenders_list.png | Tenders list |
| 05_tender_detail.png | Tender detail |
| 06_data_sources.png | Data sources |
| 07_alerts.png | Alerts |
| 08_profile.png | Profile |
| 09_settings.png | Settings |

## Rendering note: sidebar height

The sidebars are `position: fixed` with `inset-y-0` / `h-screen`, so they size
to the viewport rather than the document. Capturing a taller page against a
1000 px viewport left them stopping part-way down — on the dashboard, at
1000/1444 = 69% of the page. The renderer now measures the document height and
grows the viewport to match before capturing, so the sidebar spans the full
image. Verified by pixel probe: the sidebar colour now runs to 99% of the image
height on every affected screen (dashboard, tenders list, tender detail,
profile).

## Logo

The logo src pointed at Stitch's Google CDN and never loaded offline; it is now
a local asset. Because the mark is navy and every placement sits on a navy
panel, a light variant is used on dark backgrounds — see `logo_variants/`.
