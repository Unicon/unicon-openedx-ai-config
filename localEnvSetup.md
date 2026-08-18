# Steps:
```
/usr/local/bin/python3.12 -m venv env
source env/bin/activate
python --version  # Should be Python 3.12.x
git clone https://github.com/openedx/openedx-platform # Fork and then clone your fork
git clone https://github.com/overhangio/tutor # Doesn't need fork
cd tutor
git checkout main # Fixes error
pip install -e .
```
Set Docker Desktop to use 16GB of RAM in Settings>Resources>Advanced>Resource Allocation:Memory limit
```
cd ../
tutor mounts add ./openedx-platform
tutor plugins disable indigo
tutor images build openedx-dev
git clone https://github.com/overhangio/tutor-mfe.git  # Doesn't need fork
pip install -e ./tutor-mfe
tutor plugins enable mfe
tutor config save
tutor dev launch
```
Update your `/etc/hosts` file to point 127.0.0.1 to each domain in the build output.
LMS will be accessible at http://local.openedx.io:8000.
CMS will not be accessible at http://studio.local.openedx.io:8001.

To create an administrator user for the platform, run the following command:
```
tutor dev do createuser --staff --superuser yourusername user@email.com
```
To create a student user for the platform, run the following command:
```
tutor dev do createuser yourusername user@email.com
```
To import the demo course, run the following command:
```
tutor dev do importdemocourse
```

To make the CMS fully functional, also do the following:
```
git clone https://github.com/openedx/frontend-app-authoring.git # Fork and then clone your fork
```
Ensure your Node version matches the one mentioned in the .nvmrc file of the `frontend-app-authoring` repository using `node --version`.
```
tutor dev stop
tutor mounts add ./frontend-app-authoring
tutor plugins install mfe
tutor plugins enable mfe
tutor images build mfe
tutor dev start lms cms mfe
cd frontend-app-authoring && npm ci # Probably not necessary?
npm run dev # Probably not necessary?
```
CMS is actually accessible at: http://apps.local.openedx.io:2001/course-authoring/home

If you're going to do development on openedx-core:
```
tutor dev stop
git clone https://github.com/openedx/openedx-core.git # Fork and then clone your fork
tutor mounts add ./openedx-core
tutor images build openedx-dev
tutor dev launch
```

If you're going to do development on openedx-events (Skip this):
```
tutor dev stop
git clone https://github.com/openedx/openedx-events.git
tutor mounts add ./openedx-events
tutor images build openedx-dev
tutor dev start -d
```

Resolve CORS issue:
1. Go to http://studio.local.openedx.io:8001/admin
2. Ctrl+F and search for "cors"
3. Click on "X domain proxy configurations"
4. Click on "ADD X DOMAIN PROXY CONFIGURATION"
5. Enter each of these URLs into the textbox, newline delimited:
```
http://local.openedx.io:8000
http://studio.local.openedx.io:8001
http://apps.local.openedx.io:2001
```
6. Check the box to "Enable" this setting.
7. Click "Save".
8. Restart the LMS and CMS using these commands
```
tutor dev restart lms cms
```

# Daily Development Commands
Start Docker Containers:
```
source env/bin/activate
tutor dev start -d
```
Stop Docker Containers:
```
tutor dev stop
```
Database Migration Local:
```
cd openedx-core

# Prerequisite
pip install -r requirements/dev.txt

# Any future updates
python manage.py makemigrations
python manage.py migrate
```
Database Migration Docker:
```
tutor dev exec cms bash
# inside container:
python manage.py makemigrations
python manage.py migrate
```

Update code dependencies:
```
tutor images build openedx-dev --no-cache
tutor dev reboot -d
```

Update frontend:
```
tutor images build mfe --no-cache
tutor dev reboot -d mfe
```

## Pytest
Prerequisites:
```
brew install python@3.12
deactivate
/usr/local/bin/python3.12 -m venv env
source env/bin/activate
python --version  # Should be Python 3.12.x
cd openedx-platform
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements/edx/development.txt -c requirements/constraints.txt
```
Example test commands:
```
cd openedx-platform
python -m pytest lms/djangoapps/grades/tests/test_events.py -k persistent_subsection
python -m pytest openedx/core/djangoapps/content/search/tests/test_api.py --ds=cms.envs.test -rs -vv
```

### openedx-core / openedx-core
```
cd openedx-core
python -m pip install -r requirements/test.txt
python -m pip install -e .
python -m pytest tests/openedx_tagging/test_models.py
```

## Frontend tests
Example test command:
```
cd frontend-app-authoring
npm test -- TagListTable.test.jsx
```

## Commands for Working with Forks
```
git remote -v
git fetch origin master
git pull --rebase origin master
git push --force-with-lease
```

# Connect to DBs in GUI
1. Find the MySQL DB password by running `tutor config printvalue OPENEDX_MYSQL_PASSWORD`
2. MySQL DB username is `openedx`
3. MySQL DB name is `openedx`
4. In your terminal, print the value of the tutor root directory `tutor config printroot`.
5. Open the port by creating this file in `$TUTOR_ROOT/env/dev/docker-compose.override.yml` with this content making sure that spaces in the path are accounted for appropriately:
```
services:
  mysql:
    ports:
      - "3306:3306"
  mongodb:
    ports:
      - "27017:27017"
```
6. `tutor dev stop`
7. `tutor dev start -d`
8. Create connection using this info.

# Expose Redis Host
1. In your terminal, print the value of the tutor root directory `tutor config printroot`.
2. Open the port by creating this file in `$TUTOR_ROOT/env/dev/docker-compose.override.yml` with this content making sure that spaces in the path are accounted for appropriately:
```
services:
  redis:
    ports:
      - "6379:6379"
```

# Troubleshooting:
If you see no errors and only warnings but are unable to access the site, run `tutor dev stop` and `tutor dev launch` and this should fix it.

# Sources:
* https://docs.tutor.edly.io/install.html
* https://docs.tutor.edly.io/tutorials/openedx-platform.html#openedx-platform
* https://discuss.openedx.org/c/development/11
* https://docs.tutor.edly.io/dev.html
* https://docs.tutor.edly.io/local.html#common-tasks
* https://github.com/openedx/frontend-app-authoring?tab=readme-ov-file
* https://training.openedx.io/courses/course-v1:OpenedX+OEX-Dev101+2024/about
