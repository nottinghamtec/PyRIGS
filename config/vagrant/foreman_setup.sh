#!/bin/bash

# Install and (if there's a Procfile) start foreman.
# Needs to come after the virtualenv has been set up.

# Expects three arguments:
VIRTUALENV_NAME=$1
DJANGO_SETTINGS_MODULE=$2
PROCFILE=$3

echo "=== Begin Vagrant Provisioning using 'config/vagrant/foreman_setup.sh'"

gem install foreman --no-ri --no-rdoc

if ! grep -Fq "DJANGO_SETTINGS_MODULE" /home/vagrant/.bashrc; then
    echo "export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}" >> /home/vagrant/.bashrc
fi


if [[ -f /vagrant/$PROCFILE ]]; then
    echo "Procfile found; starting foreman."

    export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"

    # Ensure the virtualenv settings in .profile are loaded:
    source /home/vagrant/.profile

    # Run with & to release the terminal.
    # Although that may also rely on the Procfile's processes having their
    # output sent to a file, not stdout/stderr.
    foreman start -f /vagrant/$PROCFILE &
else
    echo "No Procfile found; not starting foreman."
fi

echo "=== End Vagrant Provisioning using 'config/vagrant/foreman_setup.sh'"
