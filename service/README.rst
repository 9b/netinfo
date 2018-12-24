Services
========
Running NetInfo as a service is the most optimal setup as it ensures a process is not killed. There are two key services, an API and a celery worker to run asynchronous tasks.

Setup
-----
Copy the files to `/etc/systemd/system/`::

    $ cp -r service/*.service /etc/systemd/system/.

Start each service::

    $ sudo systemctl start netinfo && sudo systemctl start netinfod

Enable the services::

    $ sudo systemctl enable netinfo && sudo systemctl enable netinfod

Check the status of each service to ensure it's running::

    $ service <service-name> status
