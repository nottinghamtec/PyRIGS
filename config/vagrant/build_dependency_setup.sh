#!/usr/bin/env bash

# Via https://github.com/kiere/vagrant-heroku-cedar-14/blob/master/config/vagrant/build_dependency_setup.sh

echo "=== Begin Vagrant Provisioning using 'config/vagrant/build_dependency_setup.sh'"

# Install build dependencies for a sane build environment
apt-get -y update
apt-get -y install autoconf bison build-essential libssl-dev libyaml-dev libreadline6-dev zlib1g-dev libncurses5-dev libffi-dev libgdbm3 libgdbm-dev

# Other things that we may need installed before anything else.
apt-get install -y libmemcached-dev
apt-get build-dep python-lxml

echo "=== End Vagrant Provisioning using 'config/vagrant/build_dependency_setup.sh'"

