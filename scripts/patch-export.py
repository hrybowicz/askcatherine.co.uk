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

CONTACT_JS = """<script id="ask-contact-js">
document.querySelectorAll('form.wpcf7-form').forEach(function (form) {
  var out = form.querySelector('.wpcf7-response-output');
  var btn = form.querySelector('input[type=submit]');
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (!form.reportValidity()) return;
    btn.disabled = true;
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


for page in ROOT.rglob("*.html"):
    original = html = page.read_text(encoding="utf-8")
    if "wpcf7-form" in html and MARKER not in html:
        html = patch(html)
    html = remove_mailchimp(html)
    if html != original:
        page.write_text(html, encoding="utf-8")
        print("patched", page.relative_to(ROOT))
