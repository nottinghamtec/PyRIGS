# TEC PA & Lighting - PyRIGS #
![Build Status](https://github.com/nottinghamtec/PyRIGS/workflows/Django%20CI/badge.svg)
[![Coverage Status](https://coveralls.io/repos/github/nottinghamtec/PyRIGS/badge.svg)](https://coveralls.io/github/nottinghamtec/PyRIGS)
[![Maintainability](https://api.codeclimate.com/v1/badges/79ca3b8106911a1d143f/maintainability)](https://codeclimate.com/github/nottinghamtec/PyRIGS/maintainability)

Welcome to TEC PA & Lighting's PyRIGS program. This is a reimplementation of the previous Rig Information Gathering System (RIGS) that was developed using Ruby on Rails. PyRIGS is our in house app for the centralisation of information on our events and now assets.

For setup information and other such helpful stuff check the [Wiki](https://github.com/nottinghamtec/PyRIGS/wiki)

# Apps
- PyRIGS: Base app, stores 'global' information
- RIGS: Rigboard stuff - event calendar etc
- assets: Database of our kit, testing data etc
- training: Logs in-house training within various "departments" (sound, lighting etc).
- versioning: Our custom logic built on top of django-reversion. Semi-modular.
- users: Our custom logic for registration and profiles. Semi-modular.

# Running locally
The compose stack runs the app behind a plain-HTTP nginx (`nginx/default.dev.conf`) on port 80.

1. Copy `.env.example` to `.env` and fill it in. For local use set at least:
2. Start the stack (migrations run automatically on start):
   ```
   docker compose up -d --build
   ```
3. Open <http://localhost/>.

## Creating a user
```
docker compose exec pyrigs python manage.py createsuperuser
```

## Sample data
Load sample users, events, assets and training data (run once on a fresh database):
```
docker compose exec pyrigs python manage.py generateSampleData
```
The individual commands (`generateSampleUserData`, `generateSampleRIGSData`, `generateSampleAssetsData`, `generateSampleTrainingData`) can be run separately, but run the user one first. To remove the sample data again (requires `DEBUG=true`):
```
docker compose exec pyrigs python manage.py deleteSampleData
```

The sample data creates these logins (the password is the same as the username):

| Username | Password | Access |
|---|---|---|
| `superuser` | `superuser` | Superuser |
| `finance` | `finance` | Finance and Keyholders groups |
| `hs` | `hs` | H&S and Keyholders groups |
| `keyholder` | `keyholder` | Keyholders group |
| `basic` | `basic` | Approved user, no groups |

It also creates a number of generic profiles (e.g. `AmyPond`, `RoryWilliams`) which have no password set, so they can't be logged into.


[![forthebadge](https://forthebadge.com/images/badges/built-with-resentment.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/contains-technical-debt.svg)](https://forthebadge.com)
