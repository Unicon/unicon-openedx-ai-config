---
name: manual-testing
description: Use when asked to manually test a pull request, set up a PR for manual testing, follow a PR's testing instructions, or when the user runs /manual-testing with a PR URL, for Open edX repos (edx-platform, openedx-core, frontend-app-authoring) on the local Tutor devstack.
---

# Manual testing of a PR

Command: `/manual-testing <PR URL> [testing instructions]`. The skill checks out the PR and the branches it depends on in the clones Tutor mounts, makes the devstack run that code, seeds named test data, and for backend changes runs a very simple demo script of the PR's testing steps. The person then follows those testing steps with everything ready, and the skill cleans up once they say they are done.

`<clones>` is the parent directory of the clone that `~/.virtualenvs/tutor/bin/tutor mounts list` reports for the PR's repo. `<artifacts>` is `<clones>/pr-reviews/<repo>-<n>/manual-testing/`, created with `mkdir -p` once step 2 has found manual steps. Every file the skill writes goes there. Write the scripts and notes with the file-writing tool, because the shell may have `noclobber` set, which can make `>` and `>>` fail. `<prefix>` is `mt_pr<n>_`. Always pass `gh` the full PR or issue URL, or `--repo`, because the clones' remotes are often forks.

## Local setup

These facts held when the skill was written. Re-check them with the commands shown, and ask the person if one no longer holds instead of guessing.

| What | Value | Check |
| --- | --- | --- |
| Venv with `tutor` | `~/.virtualenvs/tutor`, called as `~/.virtualenvs/tutor/bin/tutor` | `~/.virtualenvs/tutor/bin/tutor --version` |
| Containers | `tutor_main_dev-cms-1`, `-lms-1`, `-authoring-1`, `-mysql-1` | `docker ps --format '{{.Names}}'` |
| Mounted clones | `~/openedx/edx-platform` and `~/openedx/openedx-core` into CMS and LMS, `~/openedx/frontend-app-authoring` into authoring | `~/.virtualenvs/tutor/bin/tutor mounts list` |
| URLs | LMS `http://local.openedx.io:8000`, Studio `http://studio.local.openedx.io:8001`, authoring MFE `http://apps.local.openedx.io:2001/authoring/` | `docker ps` port column |
| Demo course | `course-v1:OpenedX+DemoX+DemoCourse`, the course fixture for any step that needs a course | `CourseOverview.objects.filter(id=...)` in the CMS shell |

Only the mounted clones reach the containers. A worktree or another copy of the repo does not. When the PR's repo has no mounted clone, stop and tell the person that it needs `tutor mounts add` and an image rebuild, and do that only after they say yes. Mounted clones that no PR in step 3 needs stay on their current branch.

Run a Python script in the CMS with:

```bash
docker exec -i tutor_main_dev-cms-1 python manage.py cms shell --no-imports < <script> 2>| <artifacts>/<script name>.stderr.log
```

`--no-imports` and the stderr redirect keep the output down to the script's own prints. `2>|` lets a rerun overwrite the log when the shell has `noclobber` set. When the command exits nonzero, show the last 30 lines of the log.

## Steps

**1. Read the PR and its issues.**

```bash
gh pr view <url> --json number,title,body,url,headRefName,headRefOid,baseRefName,files,closingIssuesReferences
gh issue view <n> --repo <owner/repo> --json number,title,body
```

The issues this PR closes are those in `closingIssuesReferences` plus any `Closes`, `Fixes`, or `Resolves` line in the body. That line is the only record when the issue lives in another repo, as in `Closes openedx/openedx-core#672`, so read it with `--repo` set to that repo. Also read any issue or PR the body says it depends on, is blocked by, or builds on. Copy every acceptance criterion of the closed issues word for word into `<artifacts>/acceptance-criteria.md`, numbered AC1 to ACn across all closed issues, each with its issue number: `AC2 (#674): <criterion text>`. A criterion is one bullet or numbered item, or one Gherkin scenario. A Gherkin scenario is copied whole, from its `Scenario:` line through its last step, as one criterion. When a closed issue has no acceptance criteria section, record that in the file and in the handover.

**2. Find the manual testing steps.** Use the steps the person gave in the command when there are any. "Use the acceptance criteria as the steps" counts as steps given. Otherwise use the PR body section under a heading about testing (testing instructions, test plan, how to test, steps to test). Sort each step into one of three groups:

- **Automated.** Running pytest, jest, linters, type checks, `make test`, "CI should be green", or anything else CI runs. Skip these steps and never run them. List them in the handover as skipped.
- **Setup.** Installing dependencies, turning on a flag, creating data. Steps 4 to 6 cover these, and they are not checks.
- **Manual.** Everything a person does against a running app and then looks at: clicking through a page, calling an endpoint, checking a database row.

A manual step is too vague to be meaningful when it does not say which behavior it checks, such as "test the feature", "make sure everything works", or "check the UI". A step that names the behavior but leaves out the exact URL, user, or expected value is concrete enough, and for backend PRs step 8 fills those details in. The testing steps are a few steps that confirm the most important part of the happy path, not a full test, so missing edge cases, or acceptance criteria that no step covers, do not make them too vague.

When no manual step remains, or no manual step names a behavior to check, stop before changing anything. Tell the person the PR has no usable manual testing steps, quote what the testing section said (or that there is none), list the acceptance criteria from step 1, and ask them to give steps, to say "use the acceptance criteria", or to ask the PR author for steps. For too-vague steps, also quote each one and say why.

When only some manual steps are too vague, continue with the rest and list the vague ones in the handover.

**3. List the branches to check out.** The PR's own branch, plus one branch per dependency that is still needed. The PR body can be stale, so check each dependency's current state with `gh`:

- Merged: skip it.
- Already in the PR's branch (cherry-picked, or the PR is stacked on it): skip it. Check the PR's commits and changed files with `gh pr view <url> --json commits,files` for the dependency's work.
- Has an open PR: check that branch out. To find the PR for an issue, try `gh issue view <n> --repo <r> --json closedByPullRequestsReferences`, then `gh pr list --repo <r> --state all --search "<n>"` and pick the one whose title or branch names the issue. Prefer the real backend over mocks, even when the PR's testing steps say to mock it.
- No PR anywhere: the steps that need that dependency run only on a stand-in that the testing steps themselves describe, such as mock data the PR ships. When the testing steps describe none, list those steps in the handover as not runnable. When the issue is closed but no PR turns up, ask the person where its code is before treating it as missing.

Write the list as a table for the person: repo, PR, state, branch, local clone. When several needed PRs share a clone, ask the person whether to use only one of them, or to merge them into the `manual-test/<repo>-<n>` branch in a stated order.

**4. Check each clone, then check out.** For each clone in the table:

1. Run `git -C <clone> status --porcelain --untracked-files=no` and `git -C <clone> branch --show-current`. Untracked files do not block a checkout and are left alone. When any clone has tracked changes, stop. Show the changed files and current branch per clone and wait for the person to say stash, commit, or abort.
2. When the clone's `HEAD` already equals the PR's `headRefOid`, keep it as is.
3. Otherwise record one line `<pr headRefOid> manual-test/<repo>-<n> <original branch> <clone path>` in `<artifacts>/original-branches.txt`, with the clone path last because it may contain spaces, then run `gh pr checkout <pr url> --branch manual-test/<repo>-<n>`. When `manual-test/<repo>-<n>` already exists, add `--force` only if `git log <pr head>..manual-test/<repo>-<n>` is empty. Otherwise the branch holds the person's own commits, so ask. For a detached HEAD, where `git branch --show-current` prints nothing, record the output of `git -C <clone> rev-parse HEAD` in place of the original branch. When the clone is already on `manual-test/<repo>-<n>`, keep the line already recorded for that clone and record no new one.

**5. Make the devstack run the checked-out code.** Start any stopped container with `~/.virtualenvs/tutor/bin/tutor dev start -d`. Then compare each clone's original branch with its checked-out branch, do what the files that differ call for, and record each action for the handover:

| Changed files | Action |
| --- | --- |
| Python dependencies (`requirements/`, `pyproject.toml`, `setup.py`) | `docker exec tutor_main_dev-cms-1 pip install -e /mnt/openedx-core`, or for edx-platform `pip install -r requirements/edx/development.txt`, in both CMS and LMS |
| Any Python code in a mounted clone | `~/.virtualenvs/tutor/bin/tutor dev restart cms lms` |
| Any backend branch switch | `docker exec tutor_main_dev-cms-1 python manage.py cms showmigrations \| grep '\[ \]'`, then `python manage.py cms migrate` when anything is unapplied. CMS and LMS share one database, so run it once. |
| `package.json` or `package-lock.json` | `docker exec tutor_main_dev-authoring-1 npm ci`, then `~/.virtualenvs/tutor/bin/tutor dev restart authoring` |
| A feature flag the steps name | An MFE flag: check `.env.development` in the container and ask before editing a tracked file. A waffle flag: turn it on in the seed script. |

Then confirm each app answers: `curl -sL -o /dev/null -w '%{http_code}' <url>` for Studio and for the MFE page under test. For a frontend PR, also check that the served `app.js` contains a string the PR adds, because the page answers 200 before the new code is built. The MFE's first build after a restart takes 30 to 40 seconds, so poll before calling it broken. For the MFE's login flow and router details, the run-frontend-app-authoring skill has them.

**6. Seed the test data.** Write `<artifacts>/seed.py` and run it in the CMS. Before writing it, check every model, field, and import against the checked-out code, because PR bodies and issues often name them wrong. Earlier seed scripts (`<clones>/*seed*.py`, `<clones>/pr-reviews/*/manual-testing/seed.py`) show working patterns. The seed:

- Creates everything the testing steps need, so they never depend on rows left over from earlier work. Every object's name or key starts with `<prefix>`. In a key with a fixed format, such as a usage key, the last part (for a usage key, the block ID) starts with it instead.
- Brings those objects to the testing steps' starting state on every run: `get_or_create`, then reset any field a step changes, and recreate any row a step deletes. A rerun of seed then demo shows the same output.
- Creates users with a `User`, a `UserProfile` (login fails without the profile), the email `<username>@example.com` (the login form asks for the email), and password `<prefix>password`. One user per role the steps mention. The permitted user gets the narrowest role that passes the view's permission check, such as `CourseStaffRole` on the demo course. The user for a 403 or hidden-control check is an active non-staff user with no course role.
- Ends by printing each object's ID and the exact URLs the testing steps use.

Write `<artifacts>/cleanup.py` together with `seed.py`; it runs in the CMS with the same command. It deletes every seeded object with one `delete()` per model, in reverse creation order with users last, filtering the name, key, or username field the seed set with `startswith` on `<prefix>` (`contains` for a fixed-format key). It prints one line per model with the deleted count, so a second run deletes nothing and prints zeros.

**7. Frontend PRs: add what the person needs to the testing steps.** The person tests by following the PR's testing steps in the browser. Copy the steps as written. Add a line under a step only when the person cannot follow or judge that step without it, and only for one of these two needs:

- where to click to reach the seeded data, such as which course, unit, or library to open;
- which concrete thing to look for, when the step as written could pass without proving the acceptance criterion it relates to. Name that criterion by its AC number from `acceptance-criteria.md`.

Start each added line with `Added:` so the person can tell it apart from the PR's own text. Most steps need no added line. The handover carries the annotated steps.

**8. Backend PRs: write and run the demo script.** Write `<artifacts>/demo.py`. It shows the outcome of each manual step as plain terminal output that a person can check at a glance, reading the script top to bottom once. The script has two parts:

- **Setup**: imports, then one assignment per seeded object, user, and API client, each with a full descriptive name (`criterion_a`, `outsider_client`).
- **Blocks**: one block per manual testing step from step 2, in the PR's order.

The blocks track the testing steps and add no checks of their own, because the script is not a full test. When a step is vague, its block runs a concrete version of it, taken from the issue and the diff: the exact endpoint, user, and request, and an expected result that is an exact status code, value, or row.

Each block is:

1. one `print` per acceptance criterion the step relates to, copied word for word from `acceptance-criteria.md`, and none when it relates to no criterion,
2. a `print` naming the step and the expected result,
3. the one action the step describes, against the seeded objects,
4. one labeled `print` per value the expected result names, such as `print("Status code:", response.status_code)` or `print("Row still exists:", CompetencyCriterion.objects.filter(id=criterion_a.id).exists())`.

Every line holds one statement. A step with two actions, such as two requests, is two blocks. Before running the script, check it: when its code outside string literals contains `def`, `lambda`, `for`, `;`, or a name shorter than three letters, rewrite those parts as plain repeated lines. Repetition is the point, because the person reads each block on its own.

When the steps describe an HTTP endpoint, call that endpoint, not the Python function behind it. Use DRF's `APIClient` with `force_authenticate` (the CMS shell has no login session, so `Client.force_login` fails there). The level of simplicity:

```python
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from openedx_tagging.models import Tag
from openedx_learning.applets.cbe.models import CompetencyCriterion

BLOCK_A = "block-v1:OpenedX+DemoX+DemoCourse+type@sequential+block@mt_pr879_block_a"
author = get_user_model().objects.get(username="mt_pr879_author")
tag = Tag.objects.get(value="mt_pr879_competency")
criterion_a = CompetencyCriterion.objects.get(object_tag__object_id=BLOCK_A)
client = APIClient()
client.force_authenticate(user=author)

print()
print("AC1 (#674): <criterion text, word for word>")
print("Step 2: delete a criterion with no learner status. Expect 200 and archived false.")
response = client.delete(f"/api/cbe/v1/competencies/{tag.id}/criteria/{criterion_a.id}/")
print("Status code:", response.status_code)
print("Response:", response.json())
```

Run the seed, then the demo, with the command from Local setup. The rerun command in the handover runs both, in that order. When the output shows the setup is wrong rather than the PR, such as the permitted user getting a 403, fix the seed and run both again before handing over.

**9. Hand over.** End with one message that holds:

- the branch table from step 3, and the path to `original-branches.txt`, which lists the branch or commit each clone goes back to in step 10;
- what step 5 changed (installs, migrations, restarts) and the health check results;
- the seeded logins, objects, and URLs;
- for frontend PRs, the testing steps with the lines step 7 added;
- for backend PRs, the demo output pasted verbatim and the one-line rerun command;
- the skipped automated steps;
- anything that failed or cannot be covered, stated plainly: the manual steps that step 2 found too vague, and the steps that cannot run because a dependency has no PR (step 3). When a step failed, the handover still goes out, with the failing command and its error;
- as the last line of the handover, a request that the person say when they are done testing, so that step 10 can clean up.

**10. Clean up after the person's testing.** Wait for the person to say they are done testing. Never start cleanup before that, and skip it when they ask to keep the setup. Then, in this order:

1. Run `cleanup.py` in the CMS with the command from Local setup. Run it before switching any branch, because it imports models that may exist only in the PR's code.
2. Go through each line of `original-branches.txt`, if the file exists.
   - When the clone has tracked changes, or `git -C <clone> branch --show-current` does not print the recorded `manual-test/<repo>-<n>` branch, leave that clone alone and tell the person.
   - Otherwise check out the recorded original branch or commit.
   - Then delete the branch with `git -C <clone> branch -D manual-test/<repo>-<n>`, but only when `git -C <clone> log <recorded PR head>..manual-test/<repo>-<n>` is empty, which is the same check step 4 uses. Otherwise leave the branch and say that it holds commits beyond the PR head.
3. Run the step 5 actions again for the files that differ between each restored branch and the PR branch, so the devstack runs the original code. Then repeat step 5's health checks. Migrations that step 5 applied stay applied; name them for the person.
4. Leave `<artifacts>` in place for a later rerun, and say so.

End with one short message that says what was cleaned up and what was left in place, and why.

## Rules

- Never post to GitHub, push, or change the PR.
- Never run the automated test steps, even when they are the first steps listed.
- Never stash, reset, or discard someone's uncommitted changes or commits without them saying so.
