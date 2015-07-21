# -*- mode: ruby -*-
# vi: set ft=ruby :
require 'yaml'

unless File.exist?('config/vagrant.yml')
  raise "There is no config/vagrant.yml file.\nCopy config/vagrant.template.yml, make any changes you need, then try again."
end

settings = YAML.load_file 'config/vagrant.yml'

$script = <<SCRIPT
echo Beginning Vagrant provisioning...
date > /etc/vagrant_provisioned_at
SCRIPT

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = '2'

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  config.vm.provision 'shell', inline: $script

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://atlas.hashicorp.com/search.
  config.vm.box = 'ubuntu/trusty64'

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  config.vm.synced_folder ".", "/vagrant"

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:5000" will access port 5000 on the guest machine.
  config.vm.network "forwarded_port", guest: 5000, host: 5000

  # PostgreSQL Server port forwarding
  config.vm.network "forwarded_port", host: 15432, guest: 5432

  # You can provision with just one of these scripts by user its name, eg:
  #   $ vagrant provision --provision-with postgresql

  config.vm.provision 'build',
            type: 'shell',
            path: 'config/vagrant/build_dependency_setup.sh'

  config.vm.provision 'git',
            type: 'shell',
            path: 'config/vagrant/git_setup.sh'

  config.vm.provision 'postgresql',
            type: 'shell',
            path: 'config/vagrant/postgresql_setup.sh',
            args: [
              settings['db']['name'],
              settings['db']['user'],
              settings['db']['password'],
            ]

  config.vm.provision 'python',
            type: 'shell',
            path: 'config/vagrant/python_setup.sh'

  config.vm.provision 'virtualenv',
            type: 'shell',
            path: 'config/vagrant/virtualenv_setup.sh',
            args: [
              settings['virtualenv']['envname'],
            ]

  # Will install foreman and, if there's a Procfile, start it:
  config.vm.provision 'foreman',
            type: 'shell',
            path: 'config/vagrant/foreman_setup.sh',
            args: [
              settings['virtualenv']['envname'],
              settings['django']['settings_module'],
              settings['foreman']['procfile'],
            ]

  # Disable automatic box update checking. If you disable this, then
  # boxes will only be checked for updates when the user runs
  # `vagrant box outdated`. This is not recommended.
  # config.vm.box_check_update = false

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # config.vm.network "forwarded_port", guest: 80, host: 8080

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  # config.vm.network "private_network", ip: "192.168.33.10"

  # Create a public network, which generally matched to bridged network.
  # Bridged networks make the machine appear as another physical device on
  # your network.
  # config.vm.network "public_network"

  # Provider-specific configuration so you can fine-tune various
  # backing providers for Vagrant. These expose provider-specific options.
  # Example for VirtualBox:
  #
  config.vm.provider "virtualbox" do |vb|
  #   # Display the VirtualBox GUI when booting the machine
  #   vb.gui = true
  #
  #   # Customize the amount of memory on the VM:
    vb.memory = "1024"
  end
  #
  # View the documentation for the provider you are using for more
  # information on available options.

  # Define a Vagrant Push strategy for pushing to Atlas. Other push strategies
  # such as FTP and Heroku are also available. See the documentation at
  # https://docs.vagrantup.com/v2/push/atlas.html for more information.
  # config.push.define "atlas" do |push|
  #   push.app = "YOUR_ATLAS_USERNAME/YOUR_APPLICATION_NAME"
  # end

  # Enable provisioning with a shell script. Additional provisioners such as
  # Puppet, Chef, Ansible, Salt, and Docker are also available. Please see the
  # documentation for more information about their specific syntax and use.
  # config.vm.provision "shell", inline: <<-SHELL
  #   sudo apt-get update
  #   sudo apt-get install -y apache2
  # SHELL
end
