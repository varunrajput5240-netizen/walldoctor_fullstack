# WallDoctor Backend

A Python (FastAPI) backend for the WallDoctor site — replaces the client-side
mock logic (fake AI call, fake auth, fake providers, fake bookings) with a
real API and database, at zero required cost.

## 1. What this fixes (audit summary)

| # | Original flaw | Fix here |
|---|---|---|
| 1 | Frontend called `api.anthropic.com` directly from the browser with **no API key** — only works inside Claude.ai's own sandbox, silently fails everywhere else | `POST /api/diagnosis` calls Claude server-side using `ANTHROPIC_API_KEY`, which never reaches the browser |
| 2 | The "AI report" silently fell back to a crude RGB-heuristic on every real deployment, with no indication to the user | Same heuristic is kept as a genuine degraded-mode fallback, but every diagnosis is tagged `source: "ai"` or `source: "fallback"` so the frontend can be honest about it |
| 3 | Login/signup accepted any input, stored the user in a JS variable, forgot it on refresh | Real `/api/auth/signup` and `/api/auth/login` with bcrypt-hashed passwords and JWTs |
| 4 | Providers were procedurally generated fake people with fake phone numbers | Providers now live in the `providers` table — the demo data is still seeded (ported 1:1 from the old generator) but is now a real, editable table, and the code is structured so real vetted providers can replace it |
| 5 | Bookings vanished on refresh; no one was ever notified | `POST /api/bookings` persists every booking with a real reference number |
| 6 | Services/prices were hardcoded in a JS array — a price change meant a code deploy | Services live in the `services` table, seeded once from the original data |

## 2. Stack (all free-tier / open-source)

- **FastAPI** + **Uvicorn** — API framework
- **SQLAlchemy** — ORM; **SQLite** for local dev, drop-in **PostgreSQL** for production (free tier: [Neon](https://neon.tech) or [Supabase](https://supabase.com))
- **passlib[bcrypt]** — password hashing
- **python-jose** — JWT auth
- **httpx** — server-side calls to the Anthropic API
- **Pillow** — image stats for the offline fallback heuristic

No paid service is required to run this in production at small scale.

## 3. Running locally

```bash
cd walldoctor-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env:
#   - set ANTHROPIC_API_KEY to a real key (get one at console.anthropic.com)
#   - set JWT_SECRET_KEY to a random string:
#       python -c "import secrets; print(secrets.token_hex(32))"

python -m app.seed              # creates walldoctor.db and loads services/providers
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Interactive docs (auto-generated
by FastAPI) are at `http://localhost:8000/docs`.

## 4. API reference

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/signup` | — | Create account, returns JWT |
| POST | `/api/auth/login` | — | Login, returns JWT |
| GET | `/api/auth/me` | required | Current user info |
| GET | `/api/categories` | — | List service categories |
| GET | `/api/services?category=&budget=&min_rating=&duration=&sort=` | — | Filtered/sorted service catalog |
| GET | `/api/providers?category=` | — | Providers for a category, with quoted price |
| POST | `/api/diagnosis` | optional | Upload a photo (`multipart/form-data`, field `image`), returns a diagnosis report |
| GET | `/api/diagnosis/mine` | required | A logged-in user's past reports |
| POST | `/api/bookings` | optional | Create a booking |
| GET | `/api/bookings/mine` | required | A logged-in user's bookings |
| GET | `/api/bookings/{booking_ref}` | — | Look up a booking by its reference (e.g. for a confirmation page) |

"Auth: optional" endpoints work for guests (`user_id` is left null) and
automatically attach the logged-in user if a valid `Authorization: Bearer
<token>` header is sent.

## 5. Integration guide: connecting `wall-doctor-12.html` to this backend

The existing frontend does everything in one big `<script>` block with
in-memory fake data. The changes are all *replacements of existing
functions* — the visual design, layout, and CSS stay exactly as they are.

**5.1 — Diagnosis (`analyze()` function)**

Replace the direct `fetch("https://api.anthropic.com/v1/messages", ...)`
call with a call to your own backend, sending the actual image file instead
of a base64 string:

```js
async function analyze(file) {
  const form = new FormData();
  form.append('image', file);

  const headers = {};
  if (authToken) headers['Authorization'] = 'Bearer ' + authToken;

  const response = await fetch(API_BASE + '/api/diagnosis', {
    method: 'POST', headers, body: form
  });
  if (!response.ok) throw new Error('Diagnosis failed');
  const parsed = await response.json();
  // parsed.source is "ai" or "fallback" — use it to show an honest badge,
  // e.g. "AI-analyzed" vs "Estimated (AI unavailable)"
  renderResult(parsed);
}
```

You no longer need `resizeImage()`'s pixel-sampling step in the browser —
the backend computes stats itself only if it needs the fallback path. You
can keep client-side image resizing purely as a bandwidth optimization
before upload if you want.

**5.2 — Auth**

Replace the fake `authSubmitBtn` handler with real calls, and store the
returned JWT (e.g. in a JS variable + `sessionStorage`, not `localStorage`
if you want it cleared when the tab closes):

```js
const res = await fetch(API_BASE + '/api/auth/login', {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({ email, password })
});
const data = await res.json();
authToken = data.access_token;
currentUser = { name: data.user_name, email: data.user_email };
```

Use `/api/auth/signup` the same way for the sign-up tab.

**5.3 — Services & Providers**

Replace the hardcoded `SERVICES` / `CATEGORIES` arrays and `buildProviders()`
with a fetch on page load:

```js
const services = await (await fetch(API_BASE + '/api/services')).json();
const categories = await (await fetch(API_BASE + '/api/categories')).json();
// renderGrid() / categoryChips logic stays the same, just reads from these instead
```

And for providers, replace the local `.filter()` on the fake array:

```js
const matches = await (await fetch(
  API_BASE + '/api/providers?category=' + encodeURIComponent(cat)
)).json();
// each item already has `.quoted_price` computed server-side
```

**5.4 — Bookings**

Replace the client-generated `bookingId` in `payNowBtn`'s handler with a
real request:

```js
const res = await fetch(API_BASE + '/api/bookings', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', ...(authToken ? {Authorization: 'Bearer '+authToken} : {}) },
  body: JSON.stringify({
    provider_id: currentProvider.id,
    service_category: currentCategory,
    quoted_amount: currentAmount,
    payment_method: currentMethod,
    customer_name: currentUser?.name || nameFieldValue,
    customer_phone: phoneFieldValue,
  })
});
const booking = await res.json();
document.getElementById('bookingId').textContent = booking.booking_ref;
```

Note: this endpoint records the booking and its payment *method*, but does
not itself move money — see the note on payments below.

**5.5 — One constant to add near the top of the script**

```js
const API_BASE = 'http://localhost:8000'; // swap for your deployed URL in production
```

## 6. On payments

The current `payNowBtn` flow was always a UI mock, not a real charge. This
backend records what the user *intends* to pay and how, which is enough to
run the business manually (call the customer, confirm, take payment over
phone/in person). To actually charge cards online, integrate a payment
processor's own hosted checkout (e.g. Stripe Checkout, which has no monthly
fee — it only takes a per-transaction cut) and have it call
`PATCH /api/bookings/{id}` (add this endpoint) via webhook to flip
`payment_status` to `paid`. That's a deliberately separate step from this
backend, since it involves real money and compliance (PCI) that's worth
doing with the processor's own hosted UI rather than custom code.

## 7. Deployment strategy (all free-tier)

| Piece | Free-tier option | Notes |
|---|---|---|
| API hosting | [Render](https://render.com) Free Web Service, or [Railway](https://railway.app) free tier | Both auto-deploy from GitHub; set the env vars from `.env.example` in their dashboard |
| Database | [Neon](https://neon.tech) free Postgres, or [Supabase](https://supabase.com) free Postgres | Swap `DATABASE_URL` in `.env` — no code changes needed, SQLAlchemy handles both |
| Frontend | [Cloudflare Pages](https://pages.cloudflare.com) or [Vercel](https://vercel.com) free tier, or GitHub Pages | Static HTML, so any of these works; just update `API_BASE` |

Render/Railway free tiers sleep after inactivity — fine for a low-traffic
local-services site; upgrade only once real booking volume justifies it.

## 8. Security notes already applied

- API key lives only in server env vars, never sent to the browser
- Passwords are bcrypt-hashed, never stored or logged in plaintext
- Login/signup return the same generic error for "no such user" and "wrong
  password" so the API can't be used to enumerate registered emails
- Uploaded images are capped at 8MB and content-type checked before
  processing
- CORS is locked to an explicit origin list via `CORS_ORIGINS`, not `*`

## 9. Not included (intentionally out of scope for this pass)

- An admin panel for editing services/providers (currently: edit via
  `python -m app.seed` or directly in the DB — a small FastAPI admin router
  would be the natural next step)
- Real payment processing (see §6)
- Rate limiting on `/api/diagnosis` (each real AI call costs money — worth
  adding `slowapi` or a Cloudflare rule before high traffic)
- Alembic migrations (schema currently just auto-creates; fine until you
  need to change existing columns in production)
