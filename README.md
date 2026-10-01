# askcatherine.co.uk

Faithful static snapshot of the WordPress site (Simply Static export), served by
Cloudflare Workers static assets. Redesign with Decap CMS to follow.

## How it works

- `public/` is the Simply Static export, post-processed by `scripts/patch-export.py`.
- Deploys automatically: Cloudflare Workers Builds runs `npx wrangler deploy` on every push to `master`.
- No server code. `wrangler.jsonc` only configures the assets and the 404 page.

## Integrations

| What | How |
|---|---|
| Contact form (homepage, privacy policy) | Posts from the browser to Formspree form `maenvjzp`. Formspree verifies Cloudflare Turnstile (secret key in the Formspree form's CAPTCHA settings; widget hostnames in Cloudflare Turnstile) |
| Newsletter | MailerLite Universal popup (account 2221166), loaded by MailerLite's own script |
| Read more popups | GenerateBlocks Pro overlays (plugin JS/CSS in `public/wp-content/plugins/generateblocks-pro/dist/`) |

## Re-exporting from WordPress

1. Export with Simply Static (relative URLs) and replace `public/` with the new export.
2. Run `python3 scripts/patch-export.py`. It is safe to re-run. It:
   - rewires the Contact Form 7 form to Formspree and removes CF7's WordPress-only scripts
   - removes Mailchimp (superseded by MailerLite)
   - makes canonical, Open Graph, Twitter and sitemap URLs absolute; rewrites `robots.txt`
   - fixes the Archivo font URL (was the old Cloudways hostname)
   - strips scripts with no use on a static site (jQuery, Akismet, Breeze lazy-load, i18n…)
   - builds `404.html`
3. Check locally with `npx wrangler dev`, then commit and push.

## Cutover checklist

- Worker → Settings → Domains & Routes: add `askcatherine.co.uk` and `www.askcatherine.co.uk`.
- Leave MX, SPF, DKIM and DMARC untouched (mail is on Proton Mail).
- www → root redirect: see the Cloudflare runbook in the project.
- Purge the Cloudflare cache; test pages, contact form and the MailerLite popup on the live domain.
- Google Search Console: resubmit `https://askcatherine.co.uk/sitemaps.xml`.
