#!/usr/bin/env python3
"""Post-process the Simply Static export in public/.

1. Rewire the Contact Form 7 form to post to Formspree from the browser
   (Formspree verifies Turnstile).
2. Remove Mailchimp completely (superseded by MailerLite): the orphaned
   "Join my newsletter" overlay and its custom CSS.

Safe to re-run after a fresh export: each step skips pages already done.
Usage: python3 scripts/patch-export.py
"""
import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent / "public"
MARKER = 'id="ask-contact-js"'

CF7_SCRIPTS = ["swv-js", "contact-form-7-js-translations", "contact-form-7-js-before", "contact-form-7-js"]

CONTACT_CSS = """<style id="ask-contact-css">
.wpcf7 form .wpcf7-response-output { background: #fff; margin-bottom: 2em; }
.wpcf7 form.wpcf7-form { display: flow-root; } /* keep that margin inside the panel instead of collapsing through it */
</style>
"""

FORMSPREE = "https://formspree.io/f/maenvjzp"

MENU_CSS = """<style id="ask-menu-css">
/* Mobile menu: the open menu had no background (unreadable over the hero photo),
   default blue links, and the white logo vanished once a background was added */
@media (max-width: 768px) {
  .main-navigation.toggled { background: #fff; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18); position: relative; z-index: 1000; }
  .main-navigation.toggled .navigation-branding .main-title a,
  .main-navigation.toggled .main-nav a { color: #8834FD; }
  .main-navigation.toggled .main-nav a:hover { color: #654597; }
  .main-navigation.toggled .menu-toggle { color: #654597; }
}
</style>
"""

SERVICES_CSS = """<style id="ask-services-css">
/* Services at a glance: pin each card's "read more" button to the bottom of the card */
.mh-content-container-services { display: flex; flex-direction: column; }
.mh-content-container-services > :has(> .mh-butoon-one) { margin-top: auto; padding-top: 2rem; }
</style>
"""

CONTACT_JS = """<script id="ask-contact-js">
// Posts straight to Formspree from the browser. Formspree verifies the Turnstile token itself
// (Turnstile secret key is set in the Formspree form's CAPTCHA settings).
document.querySelectorAll('form.wpcf7-form').forEach(function (form) {
  var out = form.querySelector('.wpcf7-response-output');
  var btn = form.querySelector('input[type=submit]');
  var val = function (n) { var el = form.elements[n]; return el ? el.value.trim() : ''; };
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (!form.reportValidity()) return;
    btn.disabled = true;
    form.classList.remove('init');  // CF7's CSS hides the response box while .init is set
    out.removeAttribute('aria-hidden');
    out.textContent = 'Sending…';
    var data = new FormData();
    data.append('name', val('your-name'));
    data.append('email', val('your-email'));
    data.append('telephone', val('your-telephone'));
    data.append('message', val('your-message'));
    data.append('_subject', 'Website enquiry from ' + val('your-name'));
    data.append('_gotcha', val('_wpcf7_ak_hp_textarea'));  // honeypot: only bots fill it
    data.append('cf-turnstile-response', val('cf-turnstile-response'));
    var ok = false, msg = '';
    try {
      var res = await fetch('""" + FORMSPREE + """', { method: 'POST', body: data, headers: { Accept: 'application/json' } });
      var body = await res.json().catch(function () { return {}; });
      ok = res.ok;
      if (!ok && body.errors) msg = body.errors.map(function (x) { return x.message; }).join(' ');
    } catch (err) {}
    out.textContent = ok
      ? 'Thank you. Your message has been sent and Catherine will be in touch soon.'
      : "Sorry, your message couldn't be sent" + (msg ? ' (' + msg + ')' : '') + '. Please try again, or email catherine@askcatherine.co.uk.';
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
    html = re.sub(r'action="[^"]*\?simply_static_page=[^"]*#wpcf7-[^"]*"', 'action="%s"' % FORMSPREE, html)
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


ARROW = ('<span class="gb-shape"><svg aria-hidden="true" height="1em" width="1em" viewBox="0 0 256 512" '
         'xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M224.3 273l-136 136c-9.4 9.4-24.6 9.4-33.9 0'
         'l-22.6-22.6c-9.4-9.4-9.4-24.6 0-33.9l96.4-96.4-96.4-96.4c-9.4-9.4-9.4-24.6 0-33.9L54.3 103c9.4-9.4 24.6-9.4 '
         '33.9 0l136 136c9.5 9.4 9.5 24.6.1 34z"></path></svg></span>')

# 404 copy: three options; NOT_FOUND_COPY picks one. Buttons are (label, href).
NOT_FOUND_OPTIONS = {
    "wandered": {
        "title": "Sorry, this page has wandered off.",
        "text": "It may have moved, or the link might be out of date. Let’s get you back on track – head to the "
                "homepage, or get in touch and I’ll point you in the right direction.",
        "buttons": [("Back to the homepage", "/"), ("Contact Catherine", "/#contact")],
    },
    "dead-end": {
        "title": "Even the best plans hit a dead end.",
        "text": "This page doesn’t exist any more – but the help you came for does. Book a free 15-minute chat "
                "and we’ll work out your next step together.",
        "buttons": [("Book a free 15-minute chat", "https://calendly.com/askcatherine/strategy-call"),
                    ("Back to the homepage", "/")],
    },
    "signpost": {
        "title": "Page not found.",
        "text": "Here’s where most people are heading:",
        "buttons": [("Services", "/#services"), ("Testimonials", "/category/testimonials/"), ("Contact", "/#contact")],
    },
}
NOT_FOUND_COPY = os.environ.get("NOT_FOUND_COPY", "wandered")

NOT_FOUND_CSS = """<style id="ask-404-css">
/* 404: footer sits at the bottom of the window; message centred on the Contact Catherine photo */
body.error404 { min-height: 100vh; min-height: 100dvh; display: flex; flex-direction: column; }
body.error404 #page { flex: 1 0 auto; display: flex; width: 100%; max-width: none; margin: 0; padding: 0; }
.ask-404 { flex: 1; display: flex; align-items: center; justify-content: center; text-align: center;
  padding: 6rem 20px; background: url('/wp-content/uploads/2025/12/IMG_1309.jpeg') center / cover no-repeat; }
.ask-404__inner { max-width: 46rem; }
.ask-404 h1 { color: var(--light1); font-size: 3em; line-height: 1.3; margin-bottom: 1.5rem; }
.ask-404 p { color: var(--light1); font-size: 1.5rem; line-height: 1.6; margin-bottom: 2.5rem; }
.ask-404__actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 1rem; }
.ask-404 .mh-butoon-one { display: inline-flex; align-items: center; gap: 0.5em; }
.ask-404 .mh-butoon-one svg { width: 1em; height: 1em; }
@media (max-width: 767px) {
  .ask-404 { padding: 2rem 20px; }
  .ask-404 h1 { font-size: 1.75em; margin-bottom: 1rem; }
  .ask-404 p { font-size: 1.125rem; margin-bottom: 1.75rem; }
  .ask-404__actions { flex-direction: column; align-items: center; gap: 0.75rem; }
  .ask-404 .mh-butoon-one { width: 100%; max-width: 18rem; justify-content: center; }
}
</style>
"""


def make_404(template: str) -> str:
    """Build 404.html from an exported page, keeping the real menu and footer."""
    copy = NOT_FOUND_OPTIONS[NOT_FOUND_COPY]
    html = re.sub(r"<title>[^<]*</title>", "<title>Page not found - —ask catherine</title>", template, count=1)
    html = re.sub(r'<link rel="canonical"[^>]*>\n?|<meta (?:property|name)="(?:og|twitter|description)[^>]*>\n?', "", html)
    html = re.sub(r'<meta name="robots" content="[^"]*"', '<meta name="robots" content="noindex, follow"', html)
    html = re.sub(r'<body class="[^"]*?(wp-theme-generatepress)', r'<body class="error404 \1', html, count=1)
    html = html.replace("</head>", NOT_FOUND_CSS + "</head>", 1)
    buttons = "".join(f'<a class="mh-butoon-one" href="{href}">{label}{ARROW}</a>' for label, href in copy["buttons"])
    body = ('<div id="page"><main class="ask-404 photo-overlay-text" id="main"><div class="ask-404__inner">'
            f'<h1><mark>{copy["title"]}</mark></h1><p><mark>{copy["text"]}</mark></p>'
            f'<div class="ask-404__actions">{buttons}</div></div></main></div>\n\n')
    a = html.find('<div class="site grid-container')
    b = html.find('<div class="site-footer', a)
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


def remove_search(html: str) -> str:
    """WordPress search (/?s=) needs a server; the site is static and only ~14 pages."""
    html = re.sub(r'<form method="get" class="search-form navigation-search"[^>]*>.*?</form>', "", html, flags=re.S)
    html = re.sub(r'<li class="search-item[^"]*">.*?</li>', "", html, flags=re.S)
    html = re.sub(r'<span class="search-item">\s*<a [^>]*>.*?</a>\s*</span>', "", html, flags=re.S)
    for hid in ("generate-navigation-search-js-before", "generate-navigation-search-js"):
        html = drop_handle(html, hid)
    return html


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
    html = remove_search(html)
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
    html = re.sub(r'<style id="ask-(?:services|menu)-css">.*?</style>\n', "", html, flags=re.S)
    if 'id="site-navigation"' in html:
        html = html.replace("</head>", MENU_CSS + "</head>", 1)
    if 'class="mh-content-container-services"' in html:
        html = html.replace("</head>", SERVICES_CSS + "</head>", 1)
    # Stray line break at the start of a services-card paragraph (the AI card, from the WordPress editor)
    html = re.sub(r'(<div class="mh-content-container-services">\s*<h3\b.*?</h3>\s*<p\b[^>]*>)\s*<br\s*/?>\s*', r"\1", html, flags=re.S)
    html = strip_unused(absolute_seo_urls(remove_mailchimp(html)))
    if html != original:
        page.write_text(html, encoding="utf-8")
        print("patched", page.relative_to(ROOT))

# Sitemaps: <loc> must be absolute URLs
for sitemap in ROOT.glob("*sitemap*.xml"):
    xml = sitemap.read_text(encoding="utf-8")
    fixed = re.sub(r"<(loc|image:loc)>/", r"<\1>" + SITE + "/", xml)
    # Simply Static gave the index its own XSL, which only lists <urlset> pages, so the
    # index displayed as an empty table. sitemaps_xsl.xsl (as on WordPress) handles both.
    fixed = fixed.replace('href="/main-sitemap.xsl"', 'href="/sitemaps_xsl.xsl"')
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
