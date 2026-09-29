import { Env } from './contact';

export async function handleNewsletter(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  const { email } = await request.json() as { email: string };

  if (!email || !email.includes('@')) {
    return new Response(JSON.stringify({ error: 'Valid email required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Subscribe via MailerLite API
  const response = await fetch('https://connect.mailerlite.com/api/subscribers', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.MAILERLITE_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      email: email,
      status: 'active',
      groups: [env.MAILERLITE_GROUP_ID]
    })
  });

  if (!response.ok) {
    return new Response(JSON.stringify({ error: 'Subscription failed' }), {
      status: response.status,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Welcome! Check your email to confirm.'
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    }
  );
}
