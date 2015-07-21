#!/bin/bash

# Install python and required python modules.
# pip and virtualenv are in virtualenv_setup.sh

# Initial part of this via
# https://github.com/torchbox/vagrant-django-base/blob/master/install.sh

echo "=== Begin Vagrant Provisioning using 'config/vagrant/python_setup.sh'"

apt-get update -y

# Python dev packages
apt-get install -y python python-dev python-setuptools python-pip

# Dependencies for image processing with Pillow (drop-in replacement for PIL)
# supporting: jpeg, tiff, png, freetype, littlecms
apt-get install -y libjpeg-dev libtiff-dev zlib1g-dev libfreetype6-dev liblcms2-dev

# lxml dependencies
apt-get install -y libxml2-dev libxslt1-dev python-dev

echo "=== End Vagrant Provisioning using 'config/vagrant/python_setup.sh'"
