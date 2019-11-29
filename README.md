# api-mreport
flask api for mreport

Prerequis
----------

 $ sudo apt-get install python3-venv


Install
---------

    # clone the repository
    $ git clone https://github.com/spelhate/api-mreport.git
    $ cd api-mreport


Create a virtualenv and activate it

    $ python3 -m venv venv
    $ . venv/bin/activate


Install Flask and dependencies

    $ pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt



Configure
---------

Edit config.py and set SQLALCHEMY_DATABASE_URI



Run
---

    $ export FLASK_APP=app
    $ flask run


Deploy with apache and gunicorn
--------------------------------

In apache conf

```
<Location "/api">
	 Header set Access-Control-Allow-Origin "*"
  	 Header set Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept, Authorization"
         ProxyPass "http://127.0.0.1:5000/api/"
  	 ProxyPassReverse "http://127.0.0.1:5000/api/"
</Location>
```

logs

    $ mkdir /var/log/api-mreport
    $ sudo chown myuser /var/log/api-mreport



Test gunicorn


    $ gunicorn -c gunicorn.conf -b 0.0.0.0:5000 app:app
    
 ```Create a .service file for the api. (/etc/systemd/system/api-mreport.service):```

```
[Unit]
Description=api-mreport
After=network.target

[Service]
User=customuser
Restart=on-failure
WorkingDirectory=/home/customuser/api-mreport/
ExecStart=/home/customuser/api-mreport/venv/bin/gunicorn -c /home/customuser/api-mreport/gunicorn.conf -b 0.0.0.0:5000 app:app

[Install]
WantedBy=multi-user.target
```


```Enable and start the service```

    $ sudo systemctl daemon-reload
    $ sudo systemctl enable api-mreport
    $ systemctl start api-mreport
 
 
