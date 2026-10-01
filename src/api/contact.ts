export interface Env {
  FORMSPREE_KEY: string;
  MAILERLITE_API_KEY: string;
  MAILERLITE_ACCOUNT: string;
  MAILERLITE_GROUP_ID: string;
  TURNSTILE_SECRET: string;
  TURNSTILE_SITEKEY: string;
  ASSETS: Fetcher;
}

const json = (body: object, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

const FAIL = "Sorry, your message couldn't be sent. Please try again, or email catherine@askcatherine.co.uk.";

export async function handleContact(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') return json({ error: 'Method not allowed' }, 405);

  const form = await request.formData();
  const field = (name: string) => String(form.get(name) ?? '').trim();

  // Akismet honeypot from the original form: bots fill it, people never see it
  if (field('_wpcf7_ak_hp_textarea')) return json({ success: true, message: 'Thank you.' });

  const name = field('your-name') || field('name');
  const email = field('your-email') || field('email');
  const telephone = field('your-telephone') || field('telephone');
  const message = field('your-message') || field('message');
  if (!name || !email.includes('@') || !message) {
    return json({ error: 'Please fill in your name, email and message.' }, 400);
  }

  const token = field('cf-turnstile-response') || field('_wpcf7_turnstile_response');
  if (!token) return json({ error: 'Please complete the security check.' }, 400);

  const verify = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      secret: env.TURNSTILE_SECRET,
      response: token,
      remoteip: request.headers.get('CF-Connecting-IP') ?? undefined
    })
  });
  const result = (await verify.json()) as { success: boolean };
  if (!result.success) return json({ error: 'Security check failed. Please try again.' }, 400);

  const sent = await fetch(`https://formspree.io/${env.FORMSPREE_KEY}`, {
    method: 'POST',
    // Server-side request: no browser Referer, which Formspree's "Restrict to
    // Domain" treats as spam. Turnstile has already verified the visitor.
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', Referer: 'https://askcatherine.co.uk/' },
    body: JSON.stringify({ name, email, telephone, message, _replyto: email, _subject: `Website enquiry from ${name}` })
  });
  if (!sent.ok) {
    console.log('Formspree rejected submission', sent.status, await sent.text());
    return json({ error: FAIL }, 502);
  }

  return json({ success: true, message: "Thank you. Your message has been sent and Catherine will be in touch soon." });
}
