NetInfo
=======
NetInfo is a simple IP enrichment service to provide additional data related to an IP address. The primary utility of NetInfo is to serve as a API wrapper and management system for the PyASN library. NetInfo will automatically seek and download new route files, ensuring the database is always up-to-date. The local API queries the PyASN instance and returns back enrichment data for an IP address.

Getting Started
---------------
Grab the dependencies::

    $ apt-get install redis-server rabbitmq-server

Check out netinfo to `/opt/`::

    $ cd /opt && git clone https://github.com/9b/netinfo.git

Setup the virtualenv::

    $ virtualenv -p python3 venv3

Activate the virtualenv::

    $ source venv3/bin/activate

Install the requirements::

    $ (venv3) pip install -r requirements.txt

Install the services and start them. You can then access the API through http://localhost:7777 for more details.

Sample Output
-------------
When calling http://localhost:7777/lookup?ip=8.8.8.8::

    {
      "as_name": "GOOGLE - Google LLC, US",
      "as_num": 15169,
      "ip": "8.8.8.8",
      "netblock": "8.8.8.0/24"
    }

Unlike the standard PyASN library, NetInfo will add the AS name to the response and original IP address that was requested.

