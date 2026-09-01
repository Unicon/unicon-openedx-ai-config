---
description: Launch and drive this MFE (frontend-app-authoring) against a local Tutor devstack, log in as Studio, and screenshot a page with a headless browser. Use this instead of rediscovering the devstack ports, the login flow, and the router basename from scratch.
---

# Running frontend-app-authoring against a local Tutor devstack

## Prerequisites

A Tutor dev devstack is expected to already be running (check with
`docker ps --format '{{.Names}}\t{{.Status}}'` — look for `tutor_dev-cms-1`,
`tutor_dev-lms-1`, and a container named after this MFE, e.g. `tutor_dev-authoring-1`). If
it isn't running, start it the normal Tutor way for this environment (`tutor dev start` or
equivalent) before continuing — this skill only covers driving an already-running
devstack, not standing one up.

The per-MFE dev container (e.g. `tutor_dev-authoring-1`) mounts this exact local checkout
at `/openedx/app` inside the container and runs `npm start` (webpack-dev-server) against
it, so any uncommitted local change is live and hot-reloaded — there is nothing to
separately "start" for this MFE once the devstack is up. Confirm the mount and the feature
flag you need with:

```bash
docker inspect tutor_dev-authoring-1 --format '{{json .Mounts}}'
docker exec tutor_dev-authoring-1 grep -i "TAGGING\|<your flag>" /openedx/app/.env /openedx/app/.env.development
```

**First hit after the container starts (or after certain file changes) triggers a real
webpack build that can take 30-40s**, during which the page is blank/white. Don't treat
that as a failure — wait longer or poll, don't just retry.

## URLs

- CMS/Studio login: `http://local.openedx.io:8000/login`
- This MFE's dev server: `http://apps.local.openedx.io:<port>/authoring/<route>` — the
  exact port is whatever `docker ps` shows mapped for the MFE's container (`2001` in one
  observed session, but check, don't assume it's stable across restarts).
  **The `/authoring` basename prefix is required.** The app's router has
  `<Router basename="/authoring/">`, so any URL without that prefix renders nothing and
  logs `No routes matched location "..."` in the console — this is not a bug in the page,
  it's a wrong URL.
- Existing taxonomy pages: `/authoring/taxonomy/:id`, `/authoring/taxonomy/:id/competencies`, etc.

## Logging in

Studio's `/login` page is a legacy server-rendered form, but the actual submit is
**AJAX-driven, not a normal page POST** — clicking submit fires a `POST
/api/user/v1/account/login_session/` and then a client-side redirect. Don't
`waitForLoadState('networkidle')` right after clicking submit; wait for the URL to
actually change instead:

```js
await page.goto('http://local.openedx.io:8000/login', { waitUntil: 'domcontentloaded' });
await page.fill('#login-email', '<email>');
await page.fill('#login-password', '<password>');
await page.click('button[type="submit"]');
await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 30000 });
```

Cookies set on `local.openedx.io:8000` are sent to `apps.local.openedx.io:<port>` too
(same parent domain, different subdomain/port — cookies aren't port-scoped), so one login
covers both origins in the same browser context.

### A throwaway test user needs a `UserProfile`, not just a `User`

Creating only a Django `User` (e.g. via `manage.py shell`) and logging in with it 500s at
`login_session/` with `User has no profile` (edx-platform's login view reads
`user.profile.name`). Create both:

```python
from django.contrib.auth import get_user_model
from common.djangoapps.student.models import UserProfile
U = get_user_model()
u, _ = U.objects.get_or_create(username="qa_verify", defaults={
    "email": "qa_verify@example.com", "is_staff": True, "is_superuser": True, "is_active": True,
})
u.set_password("<password>"); u.save()
UserProfile.objects.get_or_create(user=u, defaults={"name": "QA Verify"})
```
Run the `User` half via `docker exec <cms-container> python manage.py cms shell -c "..."` and
the `UserProfile` half via the **LMS** container's `manage.py lms shell` — they share one
database, but `UserProfile` lives in an LMS-side app, so creating it from the CMS shell can
still work if `common.djangoapps.student` is installed there too; if in doubt, do it from LMS.

## Driving it with a real browser

Playwright is **not currently a devDependency of this repo**. The clean fix, if you have
write access to `package.json`, is:
```bash
npm install --save-dev playwright && npx playwright install chromium
```
If you can't install anything (e.g. a read-only or heavily sandboxed session) and another
local project on the same machine already has Playwright with browsers downloaded, you can
borrow its `node_modules/playwright` and point `executablePath` at whatever Chromium
revision is actually cached in `~/Library/Caches/ms-playwright/` — but treat this as a
last-resort, machine-specific workaround, not something to hardcode as a real dependency:
the borrowed path won't exist on any other machine or CI. If you do have to fall back to
this, `require()` the borrowed package's absolute path and pass `executablePath` explicitly;
don't assume the installed Playwright's own bundled revision matches what's cached.

Minimal working shape once you have a `chromium` launch:

```js
const browser = await chromium.launch({ headless: true /*, executablePath: '...' if borrowing */ });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
// ... login flow above ...
await page.goto('http://apps.local.openedx.io:<port>/authoring/<route>', { waitUntil: 'load', timeout: 60000 });
await page.waitForSelector('text=<something on the page>', { timeout: 30000 }); // covers the cold-build wait
await page.screenshot({ path: '<scratchpad>/out.png', fullPage: true });
```

## Seeding test data for a taxonomy/tagging page

If the page you're testing needs a taxonomy with actual nested tags (there may be none in
a fresh devstack), create one via the CMS container's Django shell rather than through the
UI — faster, and lets you deliberately seed edge cases (e.g. a tag with no `external_id`):

```python
from openedx_tagging.models import Taxonomy, Tag  # note: openedx_tagging.models, not .core.tagging.models
tax, _ = Taxonomy.objects.get_or_create(name="My Test Taxonomy", defaults=dict(export_id="my_test_taxonomy", enabled=True))
root, _ = Tag.objects.get_or_create(taxonomy=tax, value="Group A", parent=None, defaults={"external_id": "A-1"})
Tag.objects.get_or_create(taxonomy=tax, value="Leaf A1", parent=root, defaults={"external_id": "A-1.1"})
Tag.objects.get_or_create(taxonomy=tax, value="Leaf A2 (no id)", parent=root)  # deliberately no external_id
```
`Tag.save()` computes `depth`/`lineage` automatically — never set those fields by hand.
