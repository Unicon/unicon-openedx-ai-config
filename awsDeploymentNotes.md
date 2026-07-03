# Initial Setup

IMPORTANT: If you intend to run the main/master branches for ongoing development instead of a specific released version of Open edX, ensure to install Tutor Main and not the regular Tutor (see Troubleshooting below).

```shell
sudo su - openedx

# Confirm tutor installed
tutor --version

tutor plugins disable indigo

# Confirm indigo disabled/uninstalled
tutor plugins list

# Assume mounts are already present
tutor mounts add ./openedx-platform
tutor mounts add ./frontend-app-authoring
tutor mounts add ./openedx-core
tutor mounts add ./openedx-events

# Confirm mounts
tutor mounts list

# Ensure permissions will work between host and containers
chmod -R 777 ~/repos

cd repos
ls
# If tutor-mfe is not already here, then
git clone https://github.com/overhangio/tutor-mfe.git

# Install tutor-mfe
pip install -e ./tutor-mfe

# Enable MFE and save
tutor plugins enable mfe
tutor config save

# Ensure HTTPS is enabled
tutor config save --set ENABLE_HTTPS=true

# Install mfe plugin
tutor plugins install mfe

# Build mfe image
tutor images build mfe

# Build openedx image
tutor images build openedx

# Create containers
tutor local launch

# Are you configuring a production platform?
Y
# Your website domain name for students (LMS)
oex.unicon.net
# Your website domain name for teachers (CMS)
studio.oex.unicon.net
# Your platform name/title
My Open edX
# Your public contact email address
contact@oex.unicon.net
# The default language code for the platform
en
# Activate SSL/TLS certificates for HTTPS access?
Y

# Create superuser - Note: You will need to be logged into this account type to access Django Admin
tutor local do createuser --staff --superuser yourusername user@email.com

# Import Demo Course
tutor local do importdemocourse

# Create student user if desired
tutor local do createuser yourusername user@email.com


```

# Troubleshooting

## Infinite 308 Redirect problem on https://studio.oex.unicon.net/

* Had to turn off https

```shell
tutor config save --set ENABLE_HTTPS=false
```

  * Had to turn off auto https in caddyfile

```shell
# put the global options header into a patch Caddyfile fragment
mkdir -p "$(tutor config printroot)/patches/caddy"

cat > "$(tutor config printroot)/patches/caddy/Caddyfile" <<'EOF'
{
  auto_https off
}
EOF

# rebuild caddy so it consumes patch
tutor local stop
tutor local start -d
```

## Error: invalid\_request Mismatching redirect URI.

* Try caddyfile override for this too as described below  
  * Maybe this is a cookie problem as I sometimes get this error incognito but not in my regular browser?

Temporary:

```shell
CADDY="$(tutor config printroot)/env/apps/caddy/Caddyfile"

perl -0777 -i -pe 's/reverse_proxy \{args\.0\} \{\s*header_up X-Forwarded-Port 80\s*\}/reverse_proxy {args.0} {\n        header_up Host {host}\n        header_up X-Forwarded-Proto https\n        header_up X-Forwarded-Port 443\n    }/s' "$CADDY"

grep -n "reverse_proxy\|X-Forwarded-Proto\|X-Forwarded-Port" "$CADDY" | sed -n '1,120p'

tutor local restart caddy
```

Permanent:

```shell
ROOT="$(tutor config printroot)"

# backup
cp -a "$ROOT/env/apps/caddy/Caddyfile" "$ROOT/env/apps/caddy/Caddyfile.bak.$(date +%s)"

# edit: add X-Forwarded-Proto
# (use sed to inject just above X-Forwarded-Port if present)
sed -i '/header_up X-Forwarded-Port/ i\        # PATCH_MARKER: x-forwarded-proto\n        header_up X-Forwarded-Proto https' \
  "$ROOT/env/apps/caddy/Caddyfile"

tutor local restart caddy
tutor local exec caddy sh -lc 'grep -n "PATCH_MARKER\|X-Forwarded-Proto\|X-Forwarded-Port" /etc/caddy/Caddyfile'
```

* Cannot create or edit a course and we notice that the redirect\_uris has http instead of https from this command:

```shell
tutor local run lms ./manage.py lms shell -c "
from oauth2_provider.models import Application
apps = Application.objects.filter(client_id='cms-sso')
for a in apps:
    print('name=', a.name)
    print('client_id=', a.client_id)
    print('redirect_uris=', repr(a.redirect_uris))
    print('skip_authorization=', a.skip_authorization)
    print('client_type=', a.client_type)
    print('authorization_grant_type=', a.authorization_grant_type)
"
```

* Solution

```shell
cd $(tutor plugins printroot)

vim studio_oauth_hardening.yml
name: studio_oauth_hardening
version: 0.1.0
patches:
  openedx-cms-common-settings: |
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

    SESSION_COOKIE_NAME = "studio_session_id"

    SOCIAL_AUTH_EDX_OAUTH2_KEY = "cms-sso"
    SOCIAL_AUTH_EDX_OAUTH2_PUBLIC_URL_ROOT = "https://oex.unicon.net"
    SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = "http://lms:8000"
wq!
tutor plugins enable studio_oauth_hardening
tutor config save
tutor local restart openedx
tutor local restart caddy
tutor local restart mfe
```

## Infinite refresh on /login\_refresh

*  on [http://oex.unicon.net/login\_refresh](http://oex.unicon.net/login_refresh) or infinite refresh on [http://studio.oex.unicon.net/api/contentstore/v1/course\_waffle\_flags](http://studio.oex.unicon.net/api/contentstore/v1/course_waffle_flags) “Failed to load Studio home. Please try again later.”  
  * Turn https back on

```shell
tutor config save --set ENABLE_HTTPS=true
tutor local restart
```

## Django Admin returns “Forbidden (403) CSRF verification failed. Request aborted.” 

* when trying to add an Organization. This seems to point to needing the same fix as the invalid\_request Mismatching redirect URI problem. Also if you cannot enroll anyone in a course and are noting 403 from this endpoint: https://oex.unicon.net/search/course\_discovery/ as well as this endpoint: https://oex.unicon.net/change\_enrollment.

```shell
mkdir -p "$(tutor plugins printroot)"

cat > "$(tutor plugins printroot)/csrf_fix.yml" <<'YAML'
name: csrf_fix
version: 0.3.0
patches:
  openedx-lms-common-settings: |
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = sorted(set(list(CSRF_TRUSTED_ORIGINS) + [
        "https://oex.unicon.net",
	 "https://apps.oex.unicon.net",
    ]))
  openedx-cms-common-settings: |
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = sorted(set(list(CSRF_TRUSTED_ORIGINS) + [
        "https://studio.oex.unicon.net",
  "https://apps.oex.unicon.net",
    ]))
YAML
tutor plugins enable csrf_fix
tutor config save
tutor local restart openedx
```

## Python version mismatch

```shell
=> ERROR [python-requirements 3/6] RUN --mount=type=bind,from=edx-platform,source=/requirements/edx/base.txt,target=/openedx/edx-platform/requirements/edx/base.txt     --mount=type=b  0.7s
------
 > [python-requirements 3/6] RUN --mount=type=bind,from=edx-platform,source=/requirements/edx/base.txt,target=/openedx/edx-platform/requirements/edx/base.txt     --mount=type=bind,from=edx-p
latform,source=/requirements/edx/assets.txt,target=/openedx/edx-platform/requirements/edx/assets.txt     --mount=type=cache,target=/openedx/.cache/pip,sharing=shared     uv pip install -r /o
penedx/edx-platform/requirements/edx/base.txt -r /openedx/edx-platform/requirements/edx/assets.txt:
0.428 Using Python 3.11.8 environment at: /openedx/venv
0.579   × No solution found when resolving dependencies:
0.579   ╰─▶ Because the current Python version (3.11.8) does not satisfy
0.579       Python>=3.12 and code-annotations==3.0.0 depends on Python>=3.12, we can
0.579       conclude that code-annotations==3.0.0 cannot be used.
0.579       And because you require code-annotations==3.0.0, we can conclude that
0.579       your requirements are unsatisfiable.
------
Dockerfile:98
--------------------
  97 |     # Install base requirements and asset-building requirements
  98 | >>> RUN --mount=type=bind,from=edx-platform,source=/requirements/edx/base.txt,target=/openedx/edx-platform/requirements/edx/base.txt \
  99 | >>>     --mount=type=bind,from=edx-platform,source=/requirements/edx/assets.txt,target=/openedx/edx-platform/requirements/edx/assets.txt \
 100 | >>>     --mount=type=cache,target=/openedx/.cache/pip,sharing=shared \
 101 | >>>     $PIP_COMMAND install -r /openedx/edx-platform/requirements/edx/base.txt -r /openedx/edx-platform/requirements/edx/assets.txt
 102 |
--------------------
ERROR: failed to solve: process "/bin/sh -c $PIP_COMMAND install -r /openedx/edx-platform/requirements/edx/base.txt -r /openedx/edx-platform/requirements/edx/assets.txt" did not complete successfully: exit code: 1
Error: Command failed with status 1: docker buildx build --tag=docker.io/overhangio/openedx:21.0.2 --output=type=docker --cache-from=type=registry,ref=docker.io/overhangio/openedx:21.0.2-cache --build-context=edx-platform=/home/openedx/repos/openedx-platform --build-context=mnt-openedx-core=/home/openedx/repos/openedx-core --build-context=mnt-openedx-events=/home/openedx/repos/openedx-events /home/openedx/.local/share/tutor/env/build/openedx
```

The code on the main/master branches appears to be ahead of the latest tutor release.  
Attempt 1 to fix:

```shell
pip install -U tutor
tutor config save
tutor images build openedx
```

This resulted in the same error, so switching to Github tutor to get the latest tutor code.  
Attempt 2 to fix:

```shell
pip uninstall -y tutor
pip install -U setuptools wheel
python -m pip install -e "tutor[full] @ git+https://github.com/overhangio/tutor.git@main"
tutor --version
tutor plugins list
tutor plugins disable indigo
tutor config save
tutor plugins list
tutor images build --no-cache openedx
```

## Accidentally created an entirely second set of containers when switching to Tutor Main

```shell
# Stop old containers
docker compose --project-name tutor_local \
  -f /home/openedx/.local/share/tutor/env/local/docker-compose.yml \
  -f /home/openedx/.local/share/tutor/env/local/docker-compose.prod.yml \
  stop

# Restart new containers
tutor local reboot -d
```

* Actually switch Tutor Main to use original containers instead of creating a second set of containers

```shell
export TUTOR_ROOT=/home/openedx/.local/share/tutor
cp /home/openedx/.local/share/tutor/config.yml /home/openedx/.local/share/tutor/config.yml.bak
tutor plugins disable csrf_fix
tutor config save --set LOCAL_PROJECT_NAME=tutor_local
tutor config printroot
tutor config printvalue LOCAL_PROJECT_NAME
# At this point you should see
/home/openedx/.local/share/tutor
tutor_local
# Then start the old environment
tutor local start -d
docker ps --format "table {{.Names}}\t{{.Image}}"
```

## CORS error

* Go to [https://studio.oex.unicon.net/admin](https://studio.oex.unicon.net/admin)  
  * Ctrl+F and search for “cors”  
  * Click on "X domain proxy configurations"  
  * Click on "ADD X DOMAIN PROXY CONFIGURATION"  
  * Enter each of these URLs into the textbox, newline delimited:  
    * https://oex.unicon.net  
    * https://studio.oex.unicon.net  
    * https://apps.oex.unicon.net  
  * Check the box to "Enable" this setting.  
  * Click "Save".  
  * Restart the LMS and CMS using these commands  
  * `tutor local restart lms cms`  
  * This still didn’t work because the issue was [https://apps.oex.unicon.net](https://apps.oex.unicon.net) calling [https://studio.oex.unicon.net](https://studio.oex.unicon.net), so this was attempt 2 to fix it:

```shell
mkdir -p "$(tutor plugins printroot)"

cat > "$(tutor plugins printroot)/mfe_cors_fix.yml" <<'YAML'
name: mfe_cors_fix
version: 0.1.0
patches:
  openedx-cms-common-settings: |
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    CORS_ORIGIN_WHITELIST = sorted(set(list(CORS_ORIGIN_WHITELIST) + [
        "https://apps.oex.unicon.net",
    ]))

    CSRF_TRUSTED_ORIGINS = sorted(set(list(CSRF_TRUSTED_ORIGINS) + [
        "https://apps.oex.unicon.net",
        "https://studio.oex.unicon.net",
    ]))
YAML

tutor plugins enable mfe_cors_fix
tutor config save
tutor local restart cms
```

* Eventually I noticed that the CORS error was fixed incognito but not in my regular browser. I deleted all browser data related to the [oex.unicon.net](http://oex.unicon.net) and turned off all plugins and still had the problem until I deleted my last 24 hours of browsing history and restarted my browser.

## 500 error on Resume Course

* From [https://oex.unicon.net/api/courseware/course/course-v1:Unicon+CBE1+CBE1\_1?browser\_timezone=America%2FPhoenix](https://oex.unicon.net/api/courseware/course/course-v1:Unicon+CBE1+CBE1_1?browser_timezone=America%2FPhoenix)  
* From `tutor local logs lms` (ensure you have the correct TUTOR\_ROOT if you recently switched from regular Tutor to Tutor Main):

```shell
lms-1  | xblock.plugin.AmbiguousPluginError: Ambiguous entry points for course: xmodule.course_block.CourseBlock, xmodule.course_block.CourseBlock
lms-1  | [pid: 27|app: 0|req: 10/34] 172.18.0.3 () {64 vars in 3288 bytes}
```

* Turns out I had edx-platform installed twice, separately. To fix this:

```shell
cd /home/openedx/repos/openedx-platform
ls -d *.egg-info
sudo rm -rf Open_edX.egg-info
tutor local reboot -d
```

## Instructor LMS 500 Error

Steps to Reproduce:

1. Login to [https://oex.unicon.net](https://oex.unicon.net) as an admin or staff user.  
2. Open a course.  
3. Click on the “Instructor” tab.  
4. Encounter 500 Error with a URL like [https://oex.unicon.net/api/course\_home/course\_metadata/None/course-v1:Unicon+CBE1+CBE1\_1](https://oex.unicon.net/api/course_home/course_metadata/None/course-v1:Unicon+CBE1+CBE1_1) where there is `None` in the middle of the URL.

![][image1]  
**Stop Gap Solution**

1. Login as an administrator user.  
2. Go to Django Admin as an administrator user: [https://studio.oex.unicon.net/admin](https://studio.oex.unicon.net/admin)  
3. Find the Waffle Flags area: [https://studio.oex.unicon.net/admin/waffle/flag/](https://studio.oex.unicon.net/admin/waffle/flag/)  
4. Create a new Waffle Flag called `instructor.legacy_instructor_dashboard`  
5. Set “Everyone” to “Yes”  
6. Enable it for Superusers and Staff  
7. Click Save.

**Actual Solution**

1. Properly install [https://github.com/openedx/frontend-app-instructor-dashboard](https://github.com/openedx/frontend-app-instructor-dashboard)   
   1. Note: This EOR has been created to add this repo to Unicon’s Github: [https://uniconinc.atlassian.net/browse/EOR-4915](https://uniconinc.atlassian.net/browse/EOR-4915) 

# Deployment Process

NOTE: Tutor and Tutor MFE need to stay updated along with the code in order for the deployments to work.

NOTE: I have started pulling the latest from both the backend and the frontend every time I do a deployment so that we don’t get too out of date. I’m still doing database migration only when something breaks that necessitates it.

**Prerequisites:**

1. Log in to AWS and go to EC2  
2. Select the `openedx-dev-ec2` instance and connect to it.

**Backend AWS deployment steps:**  
1\. `sudo su - openedx`   
2\. Pull changes from github into the corresponding repo on the AWS host (e.g. openedx-core, openedx-platform, openedx-events)

```shell
cd ~/repos
cd openedx-platform
git fetch
git pull
cd ../openedx-core
git fetch
git pull
cd ../openedx-events
git fetch
git pull
cd ../
```

3\. `tutor images build openedx --no-cache`  
4\. `tutor local reboot -d cms lms`  
**Note:** If making changes related to Meilisearch, Meilisearch is in a separate container, so you will probably want to run `tutor local reboot -d` as well as the weird steps that follow outlined below in the Backend Database migration steps to pull those changes in.

**Backend Database migration steps:**

1. `tutor local run cms ./manage.py cms migrate`  
2. `tutor local run lms ./manage.py lms migrate` \# not sure if this is needed  
3. `tutor local reboot -d`  
4. The reboot command seems to necessitate going back and fixing the redirect loop problem:  
   1. `tutor config save --set ENABLE_HTTPS=false`  
   2. `tutor local stop`  
   3. `tutor local start -d`  
   4. Which in turn causes the login\_refresh problem that needs to be fixed with these steps:  
      1. `tutor config save --set ENABLE_HTTPS=true`  
      2. `tutor local restart`

**Frontend AWS deployment steps:**  
1\. `sudo su - openedx`  
2\. Pull changes from github into frontend-app-authoring on the AWS host

```shell
cd ~/repos
cd frontend-app-authoring
git fetch
git pull
```

3\. `tutor images build mfe --no-cache`  
4\. `tutor local reboot -d mfe`  
5\. In Chrome, press Cmd+Shift+R or right click on refresh button in Chrome browser \> Empty Cache and Hard Reload

# Smoke Testing Steps

1. Login to [https://studio.unicon.net](https://studio.unicon.net) as a superuser.  
2. Confirm that the top left of the screen has 2 gray circles instead of purple arrows. This means that the indigo plugin is disabled, and we want it to be disabled.  
3. Click on Taxonomies and test out downloading the templates and importing them.  
4. Go to [https://studio.unicon.net/admin/](https://studio.unicon.net/admin/) in another tab.  
5. Do Ctrl+F or Cmd+F and search for “Organizations”.  
6. Click on “Organizations”.  
7. There must be an organization in the system or tagging will not function. If the Unicon Organization is not there, add it. If you want to test adding some other organization, that’s okay too. Click “Add Organization \+”.  
8. If you did not see the Unicon Organization on the previous screen, enter “Unicon” for “Name” and for “Short Name”. Otherwise, enter whatever you want to test adding an organization.  
9. Click “SAVE”. No errors should occur on the screen.  
10. Go back to your Studio tab.  
11. Refresh the page. (This is important so that your new Organization shows up.)  
12. For your newly imported taxonomy, click on the 3 dots icon.  
13. Click “Manage Organizations”.  
14. Click on the “Search for an organization” box and ensure you can see your new organization there.  
15. Click away and then check the box for “Assign to all organizations”.  
16. Click “Save”.  
17. Click on the two gray circles in the upper left.  
18. Click on the “Open edX Demo Course”.  
19. For any piece of content in this course, click on the 3 dots icon.  
20. Click on “Manage tags”.  
21. Your newly imported Taxonomy should be visible. Click on the down arrow to open it.  
22. Click on “Add tags”.  
23. Check one or more boxes to add tags.  
24. Click “Add tags”.  
25. Click “Save” in the bottom right.  
26. Click “Close”.  
27. Notice that the tag icon appears for your tags.  
28. Go to [https://oex.unicon.net](https://oex.unicon.net)  
29. Confirm that it looks something like this:

![][image2]

30. Logout and create yourself an account to test a student user.  
31. You will need to go into Django Admin to enable/activate your student user because SMTP is not setup.  
32. Return to [https://oex.unicon.net](https://oex.unicon.net) and log in as your new student user.  
33. Confirm that you can enroll in a course and view its content.

[image1]: <data:image/png;base64,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QoOGzzYFMdAc0BzQHMgEc0Cv11qvNAeOyhwI/e/kKqYgBpoDmgOaA5oDmgOaA5oDsXMgxO+gKeRwvw0nDuJwlOaA5lsOzTXNNc0BzYGMOwdC/n+mEBKDkBjo70BzQHNAc0BzQHPAzQHP88zzFDzvMBiojOaO5oDmgOaA5oDmQNTNAX1aLbofuFfvREAEREAEROCwCGTlQhJHWXn01XcREAEREAEREIFDCEgcHYJEESIgAiIQTQTUFxEQgdQSkDhKLTHlFwEREAEREAERiGoCEkdRPbzqXDQRUF9EQAREQASODgGJo6PDWa2IgAiIgAiIgAhkEgISR0d9oNSgCIiACIiACIhARiYgcZSRR0e2iYAIiIAIiEBmIhAltkocRclAqhsiIAIiIAIiIAJpQ0DiKG04qhYREAERiCYC6osIZGkCEkdZevjVeREQAREQAREQgfgEJI7iE9G9CEQTAfVFBERABEQg1QQkjlKNTAVEQAREQAREQASimYDEUeYYXVkpAiIgAiIgAiJwlAhIHB0l0GpGBERABERABEQgIQIZL07iKOONiSwSAREQAREQARE4hgQkjo4hfDUtAiIgAtFEQH0RgWghIHEULSOpfoiACIiACIiACKQJAYmjNMGoSkQgmgioLyIgAiKQtQlIHGXt8VfvRUAEREAEREAE4hGQOIoHJJpu1RcREAEREAEREIHUE5A4Sj0zlRABH7J1TQAAEABJREFUERABERABETi2BNK1dYmjdMWrykVABERABERABDIbAYmjzDZislcEREAEoomA+iICGZCAxFEGHBSZJAIiIAIiIAIicOwISBwdO/ZqWQSiiYD6IgIiIAJRQ0DiKGqGUh0RAREQAREQARFICwISR2lBMZrqUF9EQAREQAREIIsTkDjK4hNA3RcBERABERCBrEIgpf2UOEopKeUTAREQAREQARHIEgQkjrLEMKuTIiACIhBNBNQXEUhfAhJH6ctXtYuACIiACIiACGQyAhJHmWzAZK4IRBMB9UUEREAEMiIBiaOMOCqySQREQAREQARE4JgRkDg6ZuijqWH1RQREQAREQASih4DEUfSMpXoiAiIgAiIgAiKQBgTiiKM0qE9ViIAIiIAIiIAIiECmJiBxlKmHT8aLgAiIgAikkICyiUCKCUgcpRiVMoqACIiACIiACGQFAhJHWWGU1UcRiCYC6osIiIAIpDMBiaN0BqzqRUAEREAEREAEMhcBiaPMNV7RZK36IgIiIAIiIAIZkoDEUYYcFhklAiIgAiIgAiJwrAgcuTg6VparXREQAREQAREQARFIBwISR+kAVVWKgAiIgAhEBwH1ImsSkDjKmuOuXouACIiACIiACCRCQOIoETCKFgERiCYC6osIiIAIpJyAxFHKWSlnBiOwa9cu27p1qx04cCDNLNu/f79t27bN9u7de9h1UpY69u3bd9h1qGDKCOzcudONV8pyR1eurNz36BpJ9SYjEpA4yoijIpviEJg2bZr99ttvLkyYMMGmTp1q48aNsz///NPuuOMO2717d5z8R3KDqHnyySdt5syZh13N+vXr7fHHH7d58+Yddh0qmDiBSDE8fvx469u3b+KZE0hBVE+cONF+/vlnQ2AEWbZv3+7iJk+enGLBvXLlShs1apSNHTv2qIu033//3e68805n/pQpU5zt/G3Ah/Mvv/xiCxcudOk6iIAIpI6AxFHqeCn3MSDw7bff2nHHHWd79uyxOXPmWJMmTWz69OlWpUoVK168eJpalD9/fmvbtu0R1VmiRAmrVq3aEdVxJIVZHIMQWQ8eLTxjkXFcJxZPWkYMX375pRPG2HbSSSdZ9uzZuUxxyJkzp+XIkcMXND/Z/Pnzw+XGjBljn3zyiTVt2tQ8zwvHJ3QB35dfftl5Lk855RRr37693X777W6OJpQ/PeKqV69uxYoVc1U3aNDA2c688zzP8FpWqlTJqlat6tJ1EAERSB2BYySOUmekcmdtAtdff73lzp07DoTLLrvM8ubN6+K2bNliLGxssRHBwrV48WLnXSKOxX/WrFn2999/G++2g7gZM2YYXikWEspFBuImTZpk//77bzh6xYoV9t133xnegiCSuMCLFcQFZzxaeCf++eefsCcCrxL5ly1b5rJhK3YRh107duywGb5dtIGXDHtdxogDeciP14TyEUnOiwavIGAD6R9//LFj9Pbbb9vs2bOJcja9++67htdjwIABNnfuXBcfeYDtr7/+6tjRFrbCcunSpbZgwQInLhCsxAf9pG8//vijwYa6li9f7rx9GzZscGfigoB9eGrwfDBOxOO1W7t2rcGfeNolngCjdevWGe3THnGE1atXO88J9XGPCMQ+bMcjRFxkwEPYrFnT8PgyzoisQGzAP6gfu7ApsjziHLGOGAni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X3DNmXTmBG1xT70EbPK8WJaISviTriACmZFAKBMZLVNFQASSIXDmmWca3ii8Jnhgksmu5AQI8Km1bt26GVuWeElY9BPIlmAU23GwxyOZYAZFioAIZAoCEkeZYphkpAiknACLefCuPuWllDMgAD88I3gVU8sRjxnbcXh4gvp0FoGUEVCujERA4igjjYZsEQEREPDTKQkAABAASURBVAEREAEROOYEJI6O+RDIABEQgWgioL6IgAhkfgISR5l/DNUDERABERABERCBNCQgcZSGMFVVNBFQX0RABERABLIqAYmjrDry6rcIiIAIiIAIiECCBKJeHCXYa0WKgAiIgAiIgAiIQCIEJI4SAaNoERABERABEcjgBGReOhGQOEonsKpWBERABERABEQgcxKQOMqc4yarRUAEoomA+iICIpChCEgcZajhkDEiIAIiIAIiIALHmoDE0bEeAbUfTQTUFxEQAREQgSggIHEUBYOoLoiACIiACIiACKQdAYmjhFgqTgREQAREQAREIMsSkDjKskOvjouACIiACGRFAupz8gQkjpJnpBwiIAIiIAIiIAJZiIDEURYabHVVBEQgmgioLyIgAulFQOIovciqXhEQAREQAREQgUxJQOIoUw6bjI4mAuqLCIiACIhAxiIgcZSxxkPWiIAIiIAIiIAIHGMCEkdpNgCqSAREQAREQAREIBoISBxFwyiqDyIgAiIgAiKQngSyWN0SR1lswNOquzt37rStW7emVXXpXs+BAwcyjL3Ysm3bNtuxY8cR9zuoi/oSqow2tmzZklDSEcXt27fPqJdzSisib2Jl6AfziXNK61M+ERABEUgvAhJH6UU2iupdvny5DRw40L744gv75ptvjPs333zTevTocdR7+e2339qAAQNcu4kJApcY7/Dyyy/blVdeaUuWLImXcvRvESx33nmnPf7440fcOCL1/vvvtwceeCBOXZs3b3b3b731lp177rnuOi0PixYtso4dO9pff/2V4mr//fdfV2b+/PnhMvv377ddu3bZnj177Mwzz7RVq1aF03SRLgRUqQiIQAoISBylAFJWz1KmTBljQStSpIiVKlXKLrzwwsMSRmnhFTj11FOtV69ebkguvvhid07usH79epswYYJ99NFHVrFixeSyp3t6njx57Oqrr06TdnLnzm0IrcjK8NA0btzYRd14442WLVs2d52Wh+rVq9uJJ56YqiorVapk3bt3j1NmxYoV9s4771iOHDmsa9eucdJ0IwIiIALHioDE0bEin8naDYVip0revHkte/bsYesRPEOGDLHrr7/eHnnkEecBYLG+7rrr7IMPPjDS8ZBcfvnlbhFn66R379521VVX2cqVK8P14IV69dVX3dbXzz//bGPGjHF58FT16dPHLrroItu+fbvhJUHkfPjhh7Zw4UJ78MEHw3X8+eefdtNNN9kFF1xgCKIg4amnnrLFixfbu+++a1OmTDEEwy233GIzZ860c845x37//XejTTxRffv2tYcfftgVxavB/aWXXmoff/yxkX7zzTc7YfPPP/+4Nujrtddeaxs2bLDvv//eqBcbuH/++eedPddcc43dddddBoupU6e69p977jnXxu7du117CL3PP//cxXGg/9Rz2WWX2d69e412b7/9didMX3zxRTM/07Rp0xx3bPRvw/8eeugh1xZsaBPvEn3GToTTggULXDnGYNOmTc6jhmcNT9CIESPC9cyaNct5ehhXmEyaNMn154477nBjEWRcunSpi6eNiRMnGu2RB0/dsGHDDI6DBg1ybLgPyuEtYmxGjhxp77//voum36eddpr98ssv7v6zzz5zddNHbCfy66+/tpNPPtmI6+6LrTVr1hierNtuu83+97//GYILLxX9P++88+zWW291Y3XvvfcaDMaPH081CiIgAiKQKIHYFS/RZCWIwH8EWMAeffRRe+2118KRiAREB4v35MmTjcW+dOnSbvF95ZVX3EKJmEHgnHTSScZizwLFQobQCSq65JJLLFeuXEaZu+++2+rXr+8EwcaNG93izQKLGMK7wJYR3iu8QAiBoA4EUc+ePa1BgwY2bty4INrZUrVqVSewEGaE8uXL27JlywxbS5QoYf369bNnnnnGmjZtGt6ioi8//fSTE2S1a9c2RA52stiy8Hbr1s3oR8OGDQ2hx+JLHdiAgEHQISrhhSBZu3atEwhPP/20O2Mg21Is7GyL1apViygXEJHUjdeHfiEe8dy9/fbbTqghFPE+wQuR4AodPGCb53n2kC+SPM+zmJgYe+mll2zGjBkGOzxvjAPepdGjR1uzZs2sod8HhAvbpQersXr16lnBggWdSL3iiiucuEUEI5C/++67IJsTqIhEhA6iCHFUs2ZNo8xAfzuWcfvyyy8NQYgYDQoispk3HTp0cGNDfLt27ZzIpA/cM99uuOEGYxxgTNzZZ5/tRDi8GRNYr1692olixg+BNnjwYGvVqpW1b9/eWrRoYdyXK1fO6DssqEdBBERABBIjIHGUGJmjE5+pWmGxZ5FBaASGs0gXKFDA2Gb56quvnJeDs+d5LkvOnDmNhRHPyRtvvGF4d8jL4snC7jL5B7wF3BctWtTYumNxrFKliuGVYCFm+8jPFucfXpHICBZPvFiFChUyz4ttPzKdZ1uwh/YROLSJwECk4R0ZPny4e64qKMNWz7PPPuu8DfRhzpw5Vq1aNcP2119/3XmSEG3UQTxCAjFEOQQN9SBuOBOH5wMvENfEEWCJ4EIwIgCII+C1GTVqlCGIuCdQF0KHftMXxAXxyQXKkAfbOOOxoQ8Ii06dOhHleAXpLiLiQLtsrWI/7BBjCJQgC8IE5uTDu4Y4wuMTtIvQY0yD/PHP9CeIow6uEabEU442f/zxR8MG0iJDpUqVnFcIGz755BMn5kiHJ0Jy3bp11rlzZ0NkI3CbN28e9lJRP3kVREAERCA+AYmj+ER0fwgBHiBm6wIvEWKADGzHEM+CxUO006dPNxYnxAyLDukIAdIQEmzbIHBeeOEFwxOAtwRvDXUFAWF0xhlnGJ4jFsVcvieJLZBGjRq57Ta2S7CDQN0seLNnz3bbNtTx22+/OS/BYn8LjYfGiSOwxcUCzTV14clCiOBhYOFFiOBxwIOBaCIfgf7hDcP7gRDBK4Q3B09I//79ja0wvEIIPupDyCCg4IBni76zOOOtQURiB14aHmxnS49+sG2IBwsPSaRoCjw6POvFFhF1kZ9+IG4QHhUqVHAeMvpNnmBssN3zPMNbRTk4IaZghvfqhBNOcGP1xx9/OI8McdjAmXFD3FAHZbAb0cl9y5YtnQcG23744QcnOKgfDxrbnGy74alhnuTLl8+oD4bMETxkcGOezJs3j+pcwAuFl48ytEMe6oQZ/UGQMU7UjwByhQ4e/v77b2O7DtGOeDr++OPd9hr1sFUKe0TqNyO/sdNPP9092wRP5iLCEy/Ywap0EgERSBcCmbdSiaPMO3ZHzXJEDSKA7aLAu1C5cmW3/YG3ZOzYscZC3b17d6tbt67xDAkLKc/xsG31xBNPGHXwDBLPiuAhYsHEOxTZCTw3ZcuWdVtbbJmQhpBo2LChW8xbt25tCBieYUIc8IwP3qXApieffNI9i4JwQZxQnnDcccc5jxALNp4gvB4IhDZt2lj+/PmdQCAfz9VgP9cEFm6em8Ezds899xhbPnDAdrbB8LzgEatRo4adcsophtcKHn379jU8FNTFliPl8TzhuUActm3b1j07RF08E3P++ee7LSyey6JdAn1j2/DTTz816ud5ILbjChcu7J6bwm6egyKN/tB2wAHvC8KHMSpZsqQhLvCYIV4Qg2x/MVbYw1YnfeNZnWLFihkiA1GKDZSBP9tr3MO3S5cujgMilmeqKI844Tkv+gtfRAr9ZqzwIGEDgoo5QJ8jt9aKFy/utlKZP4wrY0x+xCP9gANjTP3EY0cQeLAd25lrbNnRHnONeTp06FC3jceW20cff+TmJTaxhcqzXMxDygR16SwCIiACkQQkjiJp6PqwCeD1CQqzaHEdLLKe5x2yPRSkkS8IeGeC62Ch5x6REnnmmkAdLLhcBwFxwjWChHNCAZHkeV44KfDYeN5/cUGi53kWtE8cdkW2iQ0INdIICKfIfhAXPyAIqId4z/MMERLZBvEIA/pAPoQQcQmF+IIhyINd1BHcxz/TXqTd8dMTu8emhMpRH8ItKAdjroO5QD9gw5n4yACPyPv41wgaz/tvbObOnWt4lPAQRrLGNsrSdiV/u41nqPBa1qlTx4lgeATzw/NiuZNfIXkCyiECWY1AKKt1WP0VARHI3AR4XurXX381PH+J9YQHw++77z73yUK8fInlU7wIiIAIJERA4ighKooTgagkoE6JgAiIgAikhIDEUUooKY8IiIAIiIAIiECWISBxlAmHWiaLgAiIgAiIgAikHwGJo/Rjq5pFQAREQAREQARSRyBD5JY4yhDDICNEQAREQAREQAQyCgGJo4wyErJDBERABKKJgPoiApmYgMRRJh48mS4CIiACIiACIpD2BCSO0p6pahSBaCKgvoiACIhAliMgcZTlhlwdFgEREAEREAERSIqAxFFSdKIpTX0RAREQAREQARFIEQGJoxRhUiYREAEREAEREIGMSiCt7ZI4Smuiqk8EREAEREAERCBTE5A4ytTDJ+NFQAREIJoIqC8ikDEISBxljHGQFSIgAiIgAiIgAhmEgMRRBhkImSEC0URAfREBERCBzExA4igzj55sFwEREAEREAERSHMCEkdpjjSaKlRfREAEREAERCDrEZA4ynpjrh6LgAiIgAiIgAgkQUDiKAk4ShIBERABERABEch6BCSOst6Yq8ciIAIiEE0E1BcRSHMCEkdpjlQVioAIiIAIiIAIZGYCEkeZefRkuwhEEwH1RQREQAQyCAGJowwyEDJDBERABERABEQgYxCQOMoY4xBNVqgvIiACIiACIpCpCUgcZerhk/EiIAIiIAIiIAJpTSBxcZTWLak+ERABERABERABEcgEBCSOMsEgyUQREAEREIG0JaDaRCApAhJHSdFRmgiIgAiIgAiIQJYjIHGU5YZcHRaBaCKgvoiACIhA2hOQOEp7pqpRBERABERABEQgExOQOMrEgxdNpqsvIiACIiACIpBRCEgcZZSRkB0iIAIiIAIiIAIZgkAai6MM0ScZIQIiIAIiIAIiIAKHTUDi6LDRqaAIiIAIiECWIqDOZhkCEkdZZqjVUREQAREQAREQgZQQkDhKCSXlEQERiCYC6osIiIAIJElA4ihJPEoUAREQAREQARHIagQkjrLaiEdTf9UXERABERABEUgHAhJH6QBVVYqACIiACIiACGReAhlBHGVeerJcBERABERABEQg6ghIHEXdkKpDIiACIiACGYeALMmMBCSOMuOoyWYREAEREAEREIF0IyBxlG5oVbEIiEA0EVBfREAEsg4BiaOsM9bqqQiIgAiIgAiIQAoIhPbv328KYpB15oDGWmOtOaA5oDmgOZD0HAjt2bPHFMRAc0BzQHNAc0BzQHNAcyB2DoR27dplmTHIZo2b5oDmgOaA5oDmgOZAesyBUPbs2U1BDDQHNAc0BzQHNAcyzBzQunyMtUkod+7cpiAGmgOaA5oDmgOaA5oDmgOxc0CfVkvBU+vKIgIiIAKHRUCFREAEMiUBiaNMOWxqh6v/AAAQAElEQVQyWgREQAREQAREIL0ISBylF1nVG00E1BcREAEREIEsREDiKAsNtroqAiIgAiIgAiKQPIGsJY6S56EcIiACIiACIiACWZyAxFEWnwDqvgiIgAiIQHQQUC/SjoDEUdqxVE0iIAIiIAIiIAJRQEDiKAoGUV0QARGIJgLqiwiIwLEmIHF0rEdA7YuACIiACIiACGQoAhJHGWo4ZEw0EVBfREAEREAEMicBiaPMOW6yWgREQAREQAREIJ0ISBwlC1YZREAEREAEREAEshIBiaOsNNrqqwiIgAiIgAhEEtB1ggQkjhLEokgREAEREAEREIGsSiD0yy+/HFbfDxw4YISUFP7000/tk08+sZEjR9qWLVtckbvuust27tzpro/0gB2TJk2ywYMH22effWZbt25NcZWpsWHPnj0p6jN9pL/0e/LkybZjx44U25NYxl27diWWpHgREAEREAEREIE0JBDauHHjYVU3ZcoU27BhQ4rKPvfcc9akSRPLmTOnXXTRRU5gzJ071/bv359oeQRPoonxEt5//30bMWKEtW7d2kqWLGnZs2ePlyPhW9rv0KFDwokJxN5zzz1hcZdAcjgKLnPmzLHatWvbjBkz7MorrzSEVThDKi/27dtn5557bipLKbsIiIAIiIAIiMDhEAiNHj3aevfubXhy8HDgoejXr5/dcMMN9uSTTzoB8+GHH9qaNWtc/W+99ZZt3rzZnnnmGSPfqFGjXHxyh2rVqlm7du1s9+7dThwF+WfNmmW333673XTTTYbgIv7xxx+3G2+80Tp27GhDhgwhKtGwd+9e+/LLL+2hhx6yqlWrWps2bZwIwyN266232m233WYLFy40+tW9e3fXTwTauHHj7Oeff3bx999/v7OJ8zXXXGMPP/yw6/eSJUuMOhA3s2fPdvY98sgjtnz58kTtCRIKFSpkdevWdcKoYcOGTiQhRO+77z67/vrrDY7kxcP0wgsv2OWXX+5sI27RokWuXWz5/fffjTHatGmT6yNC6YEHHnD1IjrJrxBFBNQVERABEUgHAs8O+NgGvPO5ff3dr7Z12w578qUP7KmXP7Bdu/dY3yfedi1edUt/d37ihfetT99X7LlXP7afxs+wB/u/5a7HjJtqw/3yT/vlXnh9iP34yzR7yq/ntXe/8HeCdruyM2fNt37PD7aX3vzUlq9YY9//+Jvt8dfpDz/93qVnlkOoQoUK9uKLL1rLli1t2LBhNnbsWOd9efnll61KlSo2ZswY2759u7Eo0ym2rPLkyWNnnnmm3X333XbKKacQnWy488477ZxzznGiJxQKhfOz0BOef/55J7bYklq/fr3RfuXKlZ03KJw5gYt169ZZmTJlzPO8cCpCCPH27LPPGoIHO/FErVq1yvr3728DBgwwBFirVq2ckELweJ7nRBHxCCvquOKKK1zcm2++6YROsWLFXH20F24sBRf16tWzv/76yz744APH7ZVXXnFic4kvvrZt22alS5e2t99+2/UB8Qj3xx57zIkobEXwFSxY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9wkF6tqwYYMREkpXnAiIgAiIgAiIgAiklMBOXwC1bdHA2rVqdEThjFNapLRJl889c+Su4h327t0bFkZBEr+MO3XqVNuxI1aJBfHxz3iPAlEVP033IiACIiACIpACAsoiAu7nRN5//UE70lC7RqVU0UxQHOEB2rXr0G+ipGaeN5ozZw6XSQYe2k4ygxJFQAREQAREQAREIAMSSFAc7d+/3/ASJWYvn1TDs5RYOvGkE7hWEAERyMIE1HUREAERyGQEEhRHyYkavEop+WTapk2bMhkOmSsCIiACIiACIpDVCSQojvAcJQWGbTc+xZZUHtL03BEUoiaoIyIgAiIgAiKQJQgkKI4QP8n1nmePksuTnMhKrrzSRUAEREAEREAERCD9CcRtIUFx5Hle3FwJ3OXNmzeB2LhR2bJlixuhOxEQAREQAREQARHI4AQSFEf82m1SdpOeP3/+pLK4tBw5crizDiIgAiIgAiJwNAioDRFICwIJiqOYmJgk686ZM6elxHNUoECBJOtRogiIgAiIgAiIgAhkNAKhhAzCM5TUllilSpUsqXTqzJ49uyUnssinIAIiIAKHElCMCIiACBw7AgmKI8/zDO9QQmbly5fPatasmVBSOM7zPCtbtmz4XhciIAIiIAIiIAIikFkIhBIzFK9PfIFEXLNmzRIVTkFdxYoVk9cogJHFz+q+CIiACIiACGQ2AiHPS/yTaYgjAp3i3LZtWytRogS3CQbP8wxhVLBgwQTTFSkCIiACIiACIiACGZ1AqH379la4cOFEnyFC6DRo0MDOPvtsK1myZIL94Rml3LlzW5kyZaxQoUIJ5lGkCIiACIiACIiACGQGAqF69erZ//73PzvrrLOsSZMmVqNGDatcubLVrVvXEE5du3a1jh07unieIypatKjxMf48efIYn0YrUqSIE0WkIZAyQ6dlowiIgAiIgAiECehCBOIRcM8c8X1EFStWtFatWlmHDh2cGDrppJPsuOOOc14lynieZ7ly5XL3eJDwErHFhjgi3vSfCIiACIiACIiACEQBgVAU9EFdEAEREAEIKIiACIhAmhCQOEoTjKpEBERABERABEQgWghIHEXLSEZTP9QXERABERABETiGBCSOjiF8NS0CIiACIiACIpDxCKSnOMp4vZVFIiACIiACIiACIpAMAYmjZAApWQREQAREQAQOJaCYaCYgcRTN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>

[image2]: <data:image/png;base64,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>