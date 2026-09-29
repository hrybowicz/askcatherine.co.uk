export interface Env {
  FORMSPREE_KEY: string;
  MAILERLITE_API_KEY: string;
  MAILERLITE_ACCOUNT: string;
  MAILERLITE_GROUP_ID: string;
  TURNSTILE_SECRET: string;
  TURNSTILE_SITEKEY: string;
}

export async function handleContact(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  const formData = await request.formData();

  // Validate with Turnstile
  const token = formData.get('cf-turnstile-response');
  if (!token) {
    return new Response(JSON.stringify({ error: 'Turnstile token missing' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Verify Turnstile
  const turnstileResponse = await fetch('https://challenges.cloudflare.com/turnstile/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      secret: env.TURNSTILE_SECRET,
      response: token
    })
  });

  const turnstileResult = await turnstileResponse.json() as any;
  if (!turnstileResult.success) {
    return new Response(JSON.stringify({ error: 'Verification failed' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Forward to Formspree
  const formspreeResponse = await fetch(`https://formspree.io/${env.FORMSPREE_KEY}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: formData.get('name'),
      email: formData.get('email'),
      message: formData.get('message')
    })
  });

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Your message has been sent. We'll be in touch soon.'
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    }
  );
}
