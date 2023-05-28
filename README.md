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


[![forthebadge](https://forthebadge.com/images/badges/built-with-resentment.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/contains-technical-debt.svg)](https://forthebadge.com)
