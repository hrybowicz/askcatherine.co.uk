#!/usr/bin/env python3
"""Rewire the Contact Form 7 form in the Simply Static export to /api/contact.

Safe to re-run after a fresh export: pages already patched are skipped.
Usage: python3 scripts/patch-forms.py
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
    html = page.read_text(encoding="utf-8")
    if "wpcf7-form" not in html or MARKER in html:
        continue
    page.write_text(patch(html), encoding="utf-8")
    print("patched", page.relative_to(ROOT))
