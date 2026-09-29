import { handleContact, Env } from './api/contact';
import { handleNewsletter } from './api/newsletter';

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // API routes
    if (url.pathname === '/api/contact') {
      return handleContact(request, env);
    }
    if (url.pathname === '/api/newsletter') {
      return handleNewsletter(request, env);
    }

    // Static files + fallback to index.html for SPA routes
    return env.ASSETS.fetch(request);
  }
};
