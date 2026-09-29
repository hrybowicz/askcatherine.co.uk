# askcatherine.co.uk Cloudflare Worker

Static site deployment of askcatherine.co.uk to Cloudflare Workers with API handlers for contact forms and newsletter signup.

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set secrets (Wrangler will prompt for these during deploy):**
   ```bash
   npx wrangler secret put TURNSTILE_SECRET --env production
   npx wrangler secret put MAILERLITE_API_KEY --env production
   ```

3. **Static files:**
   - Copy Simply Static export to `public/` directory
   - All files will be served as static assets

## Development

```bash
npm run dev
# Open http://localhost:8787
```

## Deployment

```bash
npx wrangler deploy --env production
```

## Environment Variables

### Public (vars in wrangler.jsonc)
- `FORMSPREE_KEY`: Contact form submission endpoint
- `MAILERLITE_ACCOUNT`: Account ID (2221166)
- `MAILERLITE_GROUP_ID`: Audience group for newsletter signups
- `TURNSTILE_SITEKEY`: CAPTCHA site key for contact form

### Secrets (set via CLI)
- `TURNSTILE_SECRET`: CAPTCHA verification secret
- `MAILERLITE_API_KEY`: API key for subscriber management

## API Routes

### POST /api/contact
Contact form handler with Turnstile CAPTCHA verification. Forwards to Formspree.

**Request:**
```
multipart/form-data:
- name: string
- email: string
- message: string
- cf-turnstile-response: string (from widget)
```

**Response:**
```json
{
  "success": true,
  "message": "Your message has been sent. We'll be in touch soon."
}
```

### POST /api/newsletter
Newsletter signup handler. Subscribes email to MailerLite audience.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Welcome! Check your email to confirm."
}
```

## DNS Configuration

Once deployed and tested:
1. Add custom domains in Cloudflare Workers
2. Update DNS to point to Workers subdomain
3. Keep MX/SPF/DKIM records unchanged

## Post-Deployment Checklist

- [ ] Contact form submission works
- [ ] Newsletter signup works
- [ ] All pages load from `public/`
- [ ] Images and assets load correctly
- [ ] CORS headers set for API routes
- [ ] Turnstile verification functional
- [ ] Formspree emails arriving

## Phase 2: Decap CMS

Future: Add Decap CMS for content editing via Git workflow.
