---
name: manual-testing
description: Use when asked to manually test a pull request, set up a PR for manual testing, follow a PR's testing instructions, or when the user runs /manual-testing with a PR URL, for Open edX repos (edx-platform, openedx-core, frontend-app-authoring) on the local Tutor devstack.
---

# Manual testing of a PR

Command: `/manual-testing <PR URL> [testing instructions]`. The skill checks out the PR and the branches it depends on in the clones Tutor mounts, makes the devstack run that code, seeds named test data, turns the testing steps into an exact test plan with each step's acceptance criteria quoted above it, and for backend changes runs a very simple demo script. The person then does the manual testing with everything ready.

`<artifacts>` is `/Users/jesperhodge/openedx/pr-reviews/<repo>-<n>/manual-testing/`, created with `mkdir -p` once step 2 has found manual steps. Every file the skill writes goes there. `<prefix>` is `mt_pr<n>_`. Always pass `gh` the full PR or issue URL, or `--repo`, because the clones' remotes are often forks.

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
docker exec -i tutor_main_dev-cms-1 python manage.py cms shell --no-imports < <script> 2> <artifacts>/<script name>.stderr.log
```

`--no-imports` and the stderr redirect keep the output down to the script's own prints. When the command exits nonzero, show the last 30 lines of the log.

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

When no manual step remains, stop before changing anything. Tell the person the PR has no manual testing instructions, quote what the testing section said (or that there is none), list the acceptance criteria from step 1, and ask them to give steps, to say "use the acceptance criteria", or to ask the PR author for steps.

**3. List the branches to check out.** The PR's own branch, plus one branch per dependency that is still needed. The PR body can be stale, so check each dependency's current state with `gh`:

- Merged: skip it.
- Already in the PR's branch (cherry-picked, or the PR is stacked on it): skip it. Check the PR's commits and changed files with `gh pr view <url> --json commits,files` for the dependency's work.
- Has an open PR: check that branch out. To find the PR for an issue, try `gh issue view <n> --repo <r> --json closedByPullRequestsReferences`, then `gh pr list --repo <r> --state all --search "<n>"` and pick the one whose title or branch names the issue. Prefer the real backend over mocks, even when the PR's testing steps say to mock it.
- No PR anywhere: mock it (step 6). When the issue is closed but no PR turns up, ask the person where its code is before mocking it.

Write the list as a table for the person: repo, PR, state, branch, local clone. When several needed PRs share a clone, ask the person whether to use one of them and mock the rest, or to merge them into the `manual-test/<repo>-<n>` branch in a stated order.

**4. Check each clone, then check out.** For each clone in the table:

1. Run `git -C <clone> status --porcelain --untracked-files=no` and `git -C <clone> branch --show-current`. Untracked files do not block a checkout and are left alone. When any clone has tracked changes, stop. Show the changed files and current branch per clone and wait for the person to say stash, commit, or abort.
2. When the clone's `HEAD` already equals the PR's `headRefOid`, keep it as is.
3. Otherwise record the clone's current branch in `<artifacts>/original-branches.txt`, then run `gh pr checkout <pr url> --branch manual-test/<repo>-<n>`. When `manual-test/<repo>-<n>` already exists, add `--force` only if `git log <pr head>..manual-test/<repo>-<n>` is empty. Otherwise the branch holds the person's own commits, so ask.

**5. Make the devstack run the checked-out code.** Start any stopped container with `~/.virtualenvs/tutor/bin/tutor dev start -d`. Then do what the changed files call for, and record each action for the handover:

| Changed files | Action |
| --- | --- |
| Python dependencies (`requirements/`, `pyproject.toml`, `setup.py`) | `docker exec tutor_main_dev-cms-1 pip install -e /mnt/openedx-core`, or for edx-platform `pip install -r requirements/edx/development.txt`, in both CMS and LMS |
| Any Python code in a mounted clone | `~/.virtualenvs/tutor/bin/tutor dev restart cms lms` |
| Any backend branch switch | `docker exec tutor_main_dev-cms-1 python manage.py cms showmigrations \| grep '\[ \]'`, then `python manage.py cms migrate` when anything is unapplied. CMS and LMS share one database, so run it once. |
| `package.json` or `package-lock.json` | `docker exec tutor_main_dev-authoring-1 npm ci`, then `~/.virtualenvs/tutor/bin/tutor dev restart authoring` |
| A feature flag the steps name | An MFE flag: check `.env.development` in the container and ask before editing a tracked file. A waffle flag: turn it on in the seed script. |

Then confirm each app answers: `curl -s -o /dev/null -w '%{http_code}' <url>` for Studio and for the MFE page under test. The MFE's first build after a restart takes 30 to 40 seconds, so poll before calling it broken. For the MFE's login flow and router details, the run-frontend-app-authoring skill has them.

**6. Seed the test data.** Write `<artifacts>/seed.py` and run it in the CMS. Before writing it, check every model, field, and import against the checked-out code, because PR bodies and issues often name them wrong. Earlier seed scripts (`~/openedx/*seed*.py`, `~/openedx/pr-reviews/*/manual-testing/seed.py`) show working patterns. The seed:

- Creates everything the plan needs, so the plan never depends on rows left over from earlier work. Every object's name or key starts with `<prefix>`.
- Brings those objects to the plan's starting state on every run: `get_or_create`, then reset any field a step changes, and recreate any row a step deletes. A rerun of seed then demo shows the same output.
- Creates users with a `User` and a `UserProfile` (login fails without the profile) and password `<prefix>password`. One user per role the steps mention. The permitted user gets the narrowest role that passes the view's permission check, such as `CourseStaffRole` on the demo course. The user for a 403 or hidden-control check is an active non-staff user with no course role.
- Ends by printing each object's ID and the exact URLs the plan uses.

When a frontend PR depends on a backend endpoint that has no PR to check out, write `<artifacts>/mock-browser.js`: a Playwright script that opens a headed (visible) Chromium, logs in as the seeded user, answers only the endpoints whose code is not checked out with `page.route`, opens the first page of the plan, and stays open for the person to test in. Install Playwright in `<artifacts>`, never in the repo.

**7. Write the test plan** in `<artifacts>/test-plan.md`. First match each acceptance criterion to the manual steps that prove it. One criterion can match several steps, and one step several criteria. Sharpen vague steps from the issue and the diff: the exact URL, user, button or request, and the exact status code, text, or row that proves it. Add a step only when an acceptance criterion has no step. Each step in the plan is this block, in this order:

```markdown
### Step 3: Delete a criterion that has a learner status (PR step 2)

> AC2 (#674): <criterion text, word for word>

- Precondition: logged in as mt_pr879_author; criterion on mt_pr879 block B has a learner status.
- Do: <exact click, URL, or request>
- Expect: <exact status code, text on screen, or database row>
```

The quote lines are the matching criteria, copied word for word from `acceptance-criteria.md`, one quote block per criterion (a Gherkin scenario keeps all its lines). Never summarize a criterion or merge two into one quote. When the PR built something the criterion names differently, such as another URL or permission, keep the quote word for word and add a `Note:` line under it that states the difference. A step that matches no criterion gets the line `> No acceptance criterion; from the PR's testing steps.` instead. For frontend PRs, this plan is the click-through checklist the person follows in the browser. The plan ends with a list of any criteria that no step covers.

**8. Backend PRs: write and run the demo script.** Write `<artifacts>/demo.py`. It shows the outcome of each manual step as plain terminal output that a person can check at a glance, reading the script top to bottom once. The script has two parts:

- **Setup**: imports, then one assignment per seeded object, user, and API client, each with a full descriptive name (`criterion_a`, `outsider_client`).
- **Blocks**: one per plan step, in plan order.

Each block is:

1. one `print` per matching acceptance criterion, with the same text as the step's `>` lines in the test plan,
2. a `print` naming the step and the expected result,
3. the one action the step describes, against the seeded objects,
4. one labeled `print` per value the expected result names, such as `print("Status code:", response.status_code)` or `print("Row still exists:", CompetencyCriterion.objects.filter(id=criterion_a.id).exists())`.

Every line holds one statement. A step that sends two requests is two blocks. Before running the script, check it: when it contains `def`, `lambda`, `for`, `;`, or a name shorter than three letters, rewrite those parts as plain repeated lines. Repetition is the point, because the person reads each block on its own.

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

- the branch table from step 3, and the path to `original-branches.txt`, with an offer to switch every clone back;
- what step 5 changed (installs, migrations, restarts) and the health check results;
- the seeded logins, objects, and URLs;
- the test plan path and the plan itself, including any acceptance criteria no step covers;
- for backend PRs, the demo output pasted verbatim and the one-line rerun command;
- the skipped automated steps;
- anything that failed or that the plan cannot cover, stated plainly. When a step failed, the handover still goes out, with the failing command and its error.

## Rules

- Never post to GitHub, push, or change the PR.
- Never run the automated test steps, even when they are the first steps listed.
- Never stash, reset, or discard someone's uncommitted changes or commits without them saying so.
