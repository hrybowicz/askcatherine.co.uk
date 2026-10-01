#!/usr/bin/env python3
"""Post-process the Simply Static export in public/.

1. Rewire the Contact Form 7 form to /api/contact (Turnstile + Formspree).
2. Remove Mailchimp completely (superseded by MailerLite): the orphaned
   "Join my newsletter" overlay and its custom CSS.

Safe to re-run after a fresh export: each step skips pages already done.
Usage: python3 scripts/patch-export.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent / "public"
MARKER = 'id="ask-contact-js"'

CF7_SCRIPTS = ["swv-js", "contact-form-7-js-translations", "contact-form-7-js-before", "contact-form-7-js"]

CONTACT_CSS = """<style id="ask-contact-css">
.wpcf7 form .wpcf7-response-output { background: #fff; margin-bottom: 2em; }
</style>
"""

CONTACT_JS = """<script id="ask-contact-js">
document.querySelectorAll('form.wpcf7-form').forEach(function (form) {
  var out = form.querySelector('.wpcf7-response-output');
  var btn = form.querySelector('input[type=submit]');
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (!form.reportValidity()) return;
    btn.disabled = true;
    form.classList.remove('init');  // CF7's CSS hides the response box while .init is set
    out.removeAttribute('aria-hidden');
    out.textContent = 'Sending…';
    var ok = false;
    try {
      var res = await fetch('/api/contact', { method: 'POST', body: new FormData(form) });
      var data = await res.json();
      ok = res.ok && data.success;
      out.textContent = data.message || data.error || 'Something went wrong. Please try again.';
    } catch (err) {
      out.textContent = 'Something went wrong. Please try again, or email catherine@askcatherine.co.uk.';
    }
    form.setAttribute('data-status', ok ? 'sent' : 'failed');
    form.classList.toggle('sent', ok);
    form.classList.toggle('failed', !ok);
    if (ok) form.reset();
    if (window.turnstile) turnstile.reset();
    btn.disabled = false;
  });
});
</script>
"""


MAILCHIMP_CSS = [("/* MH newsletter form */", ".mh-purple {"), ("/* Mailchimp form */", "/* overlay box */")]


def remove_element(html: str, start: int) -> str:
    """Remove the <div> starting at `start`, including everything nested in it."""
    depth, i = 0, start
    for m in re.finditer(r"<(/?)div\b[^>]*>", html[start:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            end = start + m.end()
            return html[:start] + html[end:]
    raise ValueError("unbalanced <div> at %d" % start)


def remove_mailchimp(html: str) -> str:
    shell = html.find('<div id="mc_embed_shell">')
    if shell != -1:
        overlay = html.rfind('<div id="gb-overlay-', 0, shell)
        html = remove_element(html, overlay)
    for begin, until in MAILCHIMP_CSS:
        a = html.find(begin)
        b = html.find(until, a)
        if a != -1 and b != -1:
            html = html[:a] + html[b:]
    return html


def patch(html: str) -> str:
    for sid in CF7_SCRIPTS:
        html = re.sub(r'<script[^>]*id="%s"[^>]*>.*?</script>\s*' % re.escape(sid), "", html, flags=re.S)
    html = re.sub(r'action="/\?simply_static_page=[^"]*#wpcf7-[^"]*"', 'action="/api/contact"', html)
    html = html.replace('data-response-field-name="_wpcf7_turnstile_response"', 'data-response-field-name="cf-turnstile-response"')
    # Required fields get native browser validation (CF7's JS used to do this)
    html = re.sub(r'(<(?:input|textarea)[^>]*aria-required="true")', r"\1 required", html)
    html = html.replace('novalidate="novalidate" ', "")
    return html.replace("</body>", CONTACT_JS + "</body>", 1)


SITE = "https://askcatherine.co.uk"
OLD_HOSTS = r"https://(?:wordpress-1666078-6669163\.cloudwaysapps\.com|(?:www\.)?askcatherine\.co\.uk)"


def absolute_seo_urls(html: str) -> str:
    """Simply Static made every URL relative; canonical, Open Graph and Twitter
    URLs must be absolute or Google and social previews ignore them."""
    html = re.sub(r'(<link rel="canonical" href=")(/[^"]*")', r"\1" + SITE + r"\2", html)
    html = re.sub(
        r'(<meta (?:property|name)="(?:og:url|og:image|og:image:secure_url|twitter:image)" content=")(/[^"]*")',
        r"\1" + SITE + r"\2", html)
    # Preloads for font files that don't exist (also 404 on the WordPress site)
    return re.sub(r'<link rel="preload" href="[^"]*archivo-v25[^"]*"[^>]*>\n?', "", html)


def make_404(template: str) -> str:
    """Build 404.html from an exported page, keeping header and footer."""
    html = re.sub(r"<title>[^<]*</title>", "<title>Page not found - —ask catherine</title>", template, count=1)
    html = re.sub(r'<link rel="canonical"[^>]*>\n?|<meta (?:property|name)="(?:og|twitter|description)[^>]*>\n?', "", html)
    html = re.sub(r'<meta name="robots" content="[^"]*"', '<meta name="robots" content="noindex, follow"', html)
    a = html.find('<main class="site-main" id="main">')
    b = html.find("</main>", a)
    body = ('<main class="site-main" id="main"><article class="page"><div class="inside-article">'
            '<header class="entry-header"><h1 class="entry-title">Oops! That page can’t be found.</h1></header>'
            '<div class="entry-content"><p>It looks like nothing was found at this location. '
            'Try the <a href="/">homepage</a> or the <a href="/category/testimonials/">testimonials</a>.</p></div>'
            "</div></article>")
    return html[:a] + body + html[b:]


# Scripts/styles with no remaining user on a static site, by WordPress handle id
UNUSED_EVERYWHERE = [
    "jquery-core-js", "jquery-migrate-js",          # only Mailchimp used jQuery
    "breeze-lazy-js", "breeze-lazy-js-after",       # no .br-lazy images in the export
    "akismet-frontend-js",                          # no Akismet server any more
    "wp-hooks-js", "wp-i18n-js", "wp-i18n-js-after",  # only Contact Form 7 used these
    "mailerlite_forms.css-css",                     # WP plugin forms; popup ships its own CSS
    # Contact Form 7's own scripts (replaced by ask-contact-js); they error without wp.i18n
    "swv-js", "contact-form-7-js-translations", "contact-form-7-js-before", "contact-form-7-js",
]
# Only needed on pages that contain the matching element
UNUSED_UNLESS = {
    "gb-carousel": ["generateblocks-carousel-js", "generateblocks-carousel-css"],
    "wpcf7-form": ["contact-form-7-css", "cloudflare-turnstile-js", "cloudflare-turnstile-js-after", "ask-contact-js", "ask-contact-css"],
}


def drop_handle(html: str, hid: str) -> str:
    html = re.sub(r'<(script|style)[^>]*\bid="%s"[^>]*>.*?</\1>\n?' % re.escape(hid), "", html, flags=re.S)
    return re.sub(r'<link[^>]*\bid="%s"[^>]*>\n?' % re.escape(hid), "", html)


def strip_unused(html: str) -> str:
    for hid in UNUSED_EVERYWHERE:
        html = drop_handle(html, hid)
    for marker, handles in UNUSED_UNLESS.items():
        if not re.search(r'class="[^"]*\b%s\b' % marker, html):
            for hid in handles:
                html = drop_handle(html, hid)
    # Cloudflare bot-check snippet captured from the live site (Cloudflare injects a fresh one itself)
    html = re.sub(r"<script>\(function\(\)\{function c\(\)[^<]*?challenge-platform.*?</script>\n?", "", html, flags=re.S)
    # WordPress-only head links: XML-RPC, version number, shortlink
    return re.sub(r'<link rel="(?:EditURI|shortlink)"[^>]*>\n?|<meta name="generator"[^>]*>\n?', "", html)


for page in ROOT.rglob("*.html"):
    if page.name == "404.html":
        continue
    original = html = page.read_text(encoding="utf-8")
    if "wpcf7-form" in html and MARKER not in html:
        html = patch(html)
    if MARKER in html:
        # (Re)apply the current contact script and its CSS, so edits here reach pages patched earlier
        html = re.sub(r'<script id="ask-contact-js">.*?</script>\n', lambda m: CONTACT_JS, html, flags=re.S)
        html = re.sub(r'<style id="ask-contact-css">.*?</style>\n', "", html, flags=re.S)
        html = html.replace("</head>", CONTACT_CSS + "</head>", 1)
    html = strip_unused(absolute_seo_urls(remove_mailchimp(html)))
    if html != original:
        page.write_text(html, encoding="utf-8")
        print("patched", page.relative_to(ROOT))

# Sitemaps: <loc> must be absolute URLs
for sitemap in ROOT.glob("*sitemap*.xml"):
    xml = sitemap.read_text(encoding="utf-8")
    fixed = re.sub(r"<(loc|image:loc)>/", r"<\1>" + SITE + "/", xml)
    if fixed != xml:
        sitemap.write_text(fixed, encoding="utf-8")
        print("patched", sitemap.name)

# Theme fonts were loaded from the old Cloudways hostname (403 from anywhere else)
for css in ROOT.rglob("*.css"):
    text = css.read_text(encoding="utf-8", errors="surrogateescape")
    fixed = re.sub(OLD_HOSTS + r"(/wp-content/)", r"\1", text)
    if fixed != text:
        css.write_text(fixed, encoding="utf-8", errors="surrogateescape")
        print("patched", css.relative_to(ROOT))

# robots.txt: point crawlers at the sitemap; drop the 60-second crawl delay
(ROOT / "robots.txt").write_text(f"User-agent: *\nDisallow:\n\nSitemap: {SITE}/sitemaps.xml\n", encoding="utf-8")

(ROOT / "404.html").write_text(strip_unused(make_404((ROOT / "privacy-policy" / "index.html").read_text(encoding="utf-8"))), encoding="utf-8")
