Aurora Cloud Manager
======

An IaaS cloud platform to enable flexible resource management through programmability.

What is Aurora Cloud Manager?
-----------

Aurora introduces a new concept of cloud management platform where resource allocation and optimization are made flexible. This is accomplished by adding concepts of programmability to the core of the platform with a simplified object-oriented API enabling the cloud administrator to describe and run personalized programs for both application deployment and optimization. In addition, administrators can also use this API to customize metrics and configure events to trigger optimization whenever necessary. The API allows for more integrated resource management by offering high-level abstractions and operations to handle all sorts of resources (i.e., computing, storage, and networking), all at the same level of importance. Aurora supports a wide range of virtualization technologies through [Libvirt](http://libvirt.org/), advanced networking through [software-defined networking (SDN)](https://www.opennetworking.org/) with [OpenFlow](https://www.opennetworking.org/sdn-resources/onf-specifications/openflow), instantiation of virtual switches with [Open vSwitch](http://openvswitch.org/), and integration with a configurable cloud monitoring framework called [FlexACMS](http://dx.doi.org/10.1109/CNSM.2013.6727833).


Installation
-----------

Note that these installation notes are only intended to install the platform itself. Installation of nodes to be managed by the platform can vary depending on the type of technology (e.g., hypervisors) you intend to use.

The following installation steps assume you will be running the platform on Ubuntu Server 14.04. You should easily find the same required packages in any other distribution, however keep in mind that different versions of libraries and other software may cause the platform not to work as expected.

##### Clone source from Github

```
$ git clone https://github.com/ComputerNetworks-UFRGS/Aurora.git
```

##### Install dependencies

```
$ sudo apt-get update
$ sudo apt-get install apache2 libapache2-mod-wsgi mysql-server python-libvirt python-dev python-pip python-django python-pygments websockify python-mysqldb
```

*Install [Social Auth](https://github.com/omab/python-social-auth) module from pip*

```
$ sudo pip install python-social-auth
```

##### Apache configuration for mod_wsgi

```
$ sudo cp Aurora/extras/apache/aurora.conf /etc/apache2/conf-available/
$ cd /etc/apache2/conf-enabled/
$ sudo ln -s ../conf-available/aurora.conf aurora.conf
```

*Note 1: Editing aurora.conf to match your local directory settings may be required.*

*Note 2: Make sure you have an early version of django (1.6 or newer) so that the platform can be installed as a wsgi application.*

```
$ django-admin --version
```

##### Apache configuration for HTTPS access:

```
$ cd /etc/apache2/sites-enabled
$ sudo ln -s ../sites-available/default-ssl.conf 000-default-ssl.conf
```

*If ssl modules are not already enabled then:*

```
$ cd /etc/apache2/mods-enabled
$ sudo ln -s ../mods-available/ssl.conf ssl.conf
$ sudo ln -s ../mods-available/ssl.load ssl.load
$ sudo ln -s ../mods-available/socache_shmcb.load socache_shmcb.load
```

*Then restart Apache:*

```
$ sudo service apache2 restart
```

##### Setup database

Execute the following SQL code into your MySQL console to create a user and database for Aurora (replace *** with the password you want). 

```
CREATE USER 'aurora'@'localhost' IDENTIFIED BY '***';
CREATE DATABASE IF NOT EXISTS `aurora`;
GRANT ALL PRIVILEGES ON `aurora`.* TO 'aurora'@'localhost';
```

##### Configure your local_settings.py

If you want to edit local django settings and avoid conflicts when pushing back modifications, create a local_settins.py file (this file is included in .gitignore) inside the Aurora folder where the default settings.py is.

```
from settings import *
DATABASES['default']['PASSWORD'] = 'yourmysqlpwd'
STATIC_ROOT = '/home/user/Aurora/static/'
MEDIA_ROOT = '/home/user/Aurora/manager/'
LOGGING['handlers']['file']['filename'] = '/home/user/Aurora/logs/main.log'

ADMINS = (
   ('You', 'you@yoursite.com'),
)

GOOGLE_OAUTH2_CLIENT_ID = '...'
GOOGLE_OAUTH2_CLIENT_SECRET = '...'
```

##### Get permissions for system logging right

You can create log file wherever you like as you configured the variable LOGGING['handlers']['file']['filename']. In general, a logs directory can be created within the platform installation folder.

```
$ mkdir Aurora/logs
$ touch Aurora/logs/main.log
$ chmod -R a+w Aurora/logs
```

##### Sync Django database and cache table

```
$ cd Aurora
$ python manage.py syncdb
$ python manage.py createcachetable aurora_cache
```

##### Create ssh keys to manage hosts

```
$ sudo mkdir /var/www/.ssh
$ sudo ssh-keygen -t rsa -f /var/www/.ssh/id_rsa
$ sudo chown -R www-data.www-data /var/www/.ssh/
$ sudo chmod 700 /var/www/.ssh/
$ sudo chmod 600 /var/www/.ssh/id_rsa
```

*Note: Copy this key into /root/.ssh of managed hosts so the platform can execute commands on them.*

##### To work with Floodlight

The Aurora platform currently works with the [Floodlight OpenFlow Controller](http://www.projectfloodlight.org/floodlight/). By default the platform expects your installation to have a local Floodlight running. You can easily install the controller from apt:

```
$ sudo apt-get install floodlight
```

However, if you have a Floodlight controller already set up in your network, you can skip this installation step. Just configure your controller location at your local_settings.py file. The platform will use the circuit pusher application of any Floodlight installation normally.


Referencing and Citation
-----------

For academic work referencing and citation please read our paper "Resource Management in IaaS Cloud Platforms made Flexible through Programmability" published at Elsevier Computer Networks - Volume 68 (2014) http://dx.doi.org/10.1016/j.comnet.2014.02.018.


Credits
-----------

Currently the main authors are:

 * Juliano Araujo Wickboldt - http://www.inf.ufrgs.br/~jwickboldt/
 * Rafael Pereira Esteves - http://www.inf.ufrgs.br/~rpesteves/
 * Márcio Barbosa de Carvalho - http://scholar.google.com.br/citations?user=2let2n4AAAAJ&hl=pt-BR
