# Postman conventions for this project

Read this file in full before creating or touching anything in Postman. It describes the
structure of the project's Postman collection so a new folder reads like it was built by the
same person who built the others, not like a one-off script dump.

## Where things live

The orchestrating session gives you the names of the configured workspace and the configured
collection in your prompt. Work only in that workspace and that collection. Other workspaces
may hold copies of the collection; never read from, write to, or create collections in them.
Do not hardcode the collection's ID or the workspace's ID, because both can change if either
is ever recreated. Find them fresh each time, by name:

1. `getWorkspaces`, then pick the workspace whose name is exactly the configured workspace
   name.
2. `getCollections` with `workspace=<that workspace id>` and `name=<configured collection
   name>` to get the collection's ID. Use the collection named exactly as configured, not
   one with a suffix such as `Copy`.

If the configured workspace does not exist or holds no collection with the configured name,
do not search other workspaces or create anything. Stop and report it as a "Needs research"
item, so the orchestrating session can ask the user for the current names.

The configured collection is the root collection for this project (`openedx-core` /
Open edX). It holds one subfolder per GitHub issue worked on so far, named like
`Issue #<N>: <short title>`. Other collections in the same workspace belong to
unrelated projects: never touch them.

## Check for an existing folder before creating one

Call `getCollection` on the configured collection (the default lightweight map is enough,
because you only need the `itemRefs` names) and look for a top-level folder whose name
contains `Issue #<N>` for the ticket number you are working on. Folders in this collection
are never nested more than one level deep (issue folder, then requests), so a plain scan of
the top-level `itemRefs` names is enough.

If no matching folder exists, create one and proceed with the rest of this document.

If a matching folder already exists, **do not silently create a second one and do not
silently overwrite it.** Stop and return this as a "Needs research" item back to the
orchestrating session in your report, exactly like an open question: name the existing
folder, summarize what it already contains (request names, one line each), and ask whether
to (a) use it as-is without changes, (b) extend it with whatever requests or test cases are
missing, or (c) leave it untouched and create a separate new folder alongside it. Wait for
the answer via the continuation the orchestrating session sends you before touching Postman
further.

## Folder naming and description

Name the folder `Issue #<N>: <short title>`, matching the ticket's own title closely
enough that someone scanning the sidebar can tell which folder is which without opening it.
For example, `Issue #629: taxonomy_type passthrough on Create and Import`. For a batch of
tickets analyzed together, create one such folder per ticket, not one shared folder: each
ticket's endpoints and fixtures are its own even when some plumbing (auth, a shared
environment variable) is reused across them.

The folder's `description` is where the durable context lives. A QA engineer opening this
folder six weeks from now, with no memory of this conversation, needs to be able to run the
requests correctly from this text alone. Always include, as separate paragraphs:

1. **What this verifies and where the AC came from.** One or two sentences, plus which
   Artifact (by its title, e.g. `"#629 taxonomy_type QA Prep"`) has the fuller write-up, so
   the two stay linkable without duplicating the whole analysis into Postman.
2. **Blocking status**, if the dependency-status section of your analysis found the ticket
   isn't safe to test yet. State plainly which blocking ticket(s) must close first, and
   don't bury this in the middle of the text; it's the first thing a QA engineer about to
   press Send needs to know.
3. **Auth section.** Copy the pattern from an existing folder (see "Auth requests" below):
   the three ways to obtain `bearer_token`, in order of preference, and the exact header
   format this project's Open edX instance expects.
4. **Request to test-case mapping.** A short list naming which request corresponds to which
   test case ID from your test-case table, including any helper/setup request (see
   numbering below).
5. **Findings relevant to reading the responses.** Anything from your analysis that changes
   how a QA engineer should interpret a response (a field being `write_only` and therefore
   absent from a 201 body is the running example; don't make someone file a false bug report
   over expected behavior).

## Request naming and numbering

Number requests in the folder in the order a QA engineer would run them, starting at `0` for
any helper/setup request (e.g. a `List` endpoint used only to find an ID for a later DB
check), then `1`, `2`, `3`, ... for the actual test-case requests. Name each request
`<N>. <Verb>: <short description> (<TC-ID>)`, e.g. `1. Create: competency (TC-1)`,
`4. Create: invalid type system, 400 (TC-4)`. Keep the TC-ID in the request's own numbering,
not the folder's sequence number: the two only coincide by accident when there's no helper
request in front of TC-1. When you add edge cases beyond what's in the Acceptance Criteria
(permission regressions, case-sensitivity, boundary values), give them their own TC-ID
continuing the existing sequence and say explicitly, in that request's own `description`,
that it's an edge case you added and not from the literal AC text.

## Auth requests: copy this pattern into every new folder

Every existing folder in this collection carries its own copies of the same three
authentication requests, rather than sharing them from one central place. This is
deliberate, so a folder is self-contained and a QA engineer doesn't have to go hunting in
another folder to log in. Copy this pattern into any new folder:

- **`Login step 1: get CSRF cookie`**: `GET {{lms_base_url}}/api/user/v2/account/login_session/`.
  The test script reads the `csrftoken` cookie from the response and saves it to the
  environment:
  ```js
  const csrftoken = pm.cookies.get('csrftoken');
  if (csrftoken) {
      pm.environment.set('csrftoken', csrftoken);
  } else {
      console.error('csrftoken cookie was not received: check the response and that base_url is correct');
  }
  ```
- **`Login step 2: get session and JWT cookies`**: `POST
  {{lms_base_url}}/api/user/v2/account/login_session/`, urlencoded body
  `email_or_username={{studio_username}}`, `password={{studio_password}}`, header
  `X-CSRFToken: {{csrftoken}}` and `Referer: {{lms_base_url}}/`. The test script reads the
  JWT cookies and assembles `bearer_token`:
  ```js
  if (pm.response.code === 200) {
      const headerPayload = pm.cookies.get('edx-jwt-cookie-header-payload');
      const signature = pm.cookies.get('edx-jwt-cookie-signature');
      if (headerPayload && signature) {
          pm.environment.set('bearer_token', headerPayload + '.' + signature);
      }
  }
  ```
- **`Get JWT access token (OAuth2, run first)`**: the manual-fallback path, for when a QA
  engineer prefers OAuth2 password grant over the Postman-native login flow above. `POST
  {{lms_base_url}}/oauth2/access_token`, urlencoded body with `grant_type=password`,
  `client_id={{oauth_client_id}}`, `client_secret={{oauth_client_secret}}`,
  `username={{studio_username}}`, `password={{studio_password}}`, `token_type=jwt`. The test
  script sets `bearer_token` from `response.access_token`.

Every request that hits the actual API under test carries the header
`Authorization: JWT {{bearer_token}}`. The prefix is **`JWT`, not `Bearer`**
(`JWT_AUTH_HEADER_PREFIX='JWT'` in openedx-platform). For endpoints that might see
session-cookie auth instead, the request also carries an `X-CSRFToken: {{csrftoken}}` header
as a fallback. JSON request bodies also carry `Content-Type: application/json`;
multipart/form-data requests carry no explicit content-type header (Postman sets the
boundary itself).

If a test case needs a second user without the tested role (a permissions-regression case
like a "regular_user, 403" request), say so plainly in that request's description: the QA
engineer must switch `studio_username`/`studio_password` to that second account and redo the
login steps before running it. Don't assume the environment is pre-populated with a second
identity.

## Environment and variables

Use the configured environment named in your prompt, and do not create a new one. The
first-time Postman setup in `SKILL.md` already created its base variables: `base_url`,
`lms_base_url`, `studio_username`, `studio_password`, `oauth_client_id`, and
`oauth_client_secret` (the last two only needed for the OAuth2 auth path), plus
`bearer_token` and `csrftoken`, which the login requests' own test scripts write. If a
variable this ticket's requests need is missing from the environment, add it rather than
assuming it's already there. To add one, read the environment first (`getEnvironment`),
write back the full list of values (every existing variable unchanged, plus the new ones)
with `putEnvironment`, and read it again afterwards to confirm nothing was lost. A missing
variable that holds a password or a secret is created with an empty value and type `secret`;
name it in the report so the user fills it in directly in Postman.

For fixture data that's specific to one ticket (a course ID, a library ID, an object ID
under test) rather than shared login plumbing, add it as a **collection-level** variable
(the `variable` array on the configured collection itself, via `getCollection` /
`putCollection`), prefixed with a short lowercase tag plus the issue number, e.g.
`ct795_course_a_object_id` for issue #795. This keeps fixture variables from different
tickets from colliding by name inside the one shared collection.

Both `patchCollection` and `putCollection` replace the collection's whole `variable` array
with the list you send, even though the `patchCollection` schema calls it "add or update".
Sending only the new variable deletes every other ticket's fixture variables. So always
read the current array first (`getCollection` with `model: minimal`), send the full merged
list (every existing variable unchanged, plus the new ones), and read the collection again
afterwards to confirm that nothing was lost.

## What actually needs to exist in Postman

Only build a Postman folder when at least one test case's verification method is Postman.
Check the "Verification method" column of your own test-case table (task 1 of the main
instructions). A ticket verified purely through UI steps needs no Postman folder at all;
say so plainly in your report instead of creating an empty or placeholder folder.
