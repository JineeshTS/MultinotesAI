## Configuration for run multinote project at local django server.

## First install mysql with the below username, password and database.
sudo apt update

sudo apt install mysql-server

sudo systemctl start mysql.service

mysql --version

sudo mysql

CREATE USER 'mzhuser'@'localhost' IDENTIFIED BY 'Jineesh@2024';

GRANT CREATE, ALTER, DROP, INSERT, UPDATE, INDEX, DELETE, SELECT, REFERENCES, RELOAD on *.* TO 'mzhuser'@'localhost' WITH GRANT OPTION;

*** login by mzhuser and create database.

mysql -u mzhuser -p

create database llmlibrarydb;

-----------------------------------------------------------------

DB_NAME='llmlibrarydb'
DB_USER='mzhuser'
DB_PASSWORD='Jineesh@2024'
DB_HOST='localhost'


## Install python dependency

sudo apt update

sudo apt install libmysqlclient-dev python3-dev

sudo apt-get install python3-dev default-libmysqlclient-dev build-essential


## Now create a folder with 'multinote' 
** Note Folder name should be 'multinote'

mkdir multinote

cd multinote

## Now clone the project inside multinote folder.

git clone --branch omnist-dev http://git.omnisttechhub.com/web-developers/commonai-backend.git

## Now install python3.10 in ubuntu.

sudo apt update && sudo apt upgrade

sudo add-apt-repository ppa:deadsnakes/ppa -y

sudo apt update

sudo apt install python3.10


## Check python installed version. Should display python3.10

python3.10 --version   

sudo apt install python3.10-dbg

sudo apt install python3.10-dev

sudo apt install python3.10-distutils

sudo apt install python3.10-lib2to3

sudo apt install python3.10-gdbm

sudo apt install libmysqlclient-dev python3-dev

sudo apt-get install python3.10-dev default-libmysqlclient-dev

sudo apt install libpq-dev python3.10-dev

sudo apt update

sudo apt install pkg-config

sudo apt install libmariadb-dev


## Now install virtualenv for python3.10

sudo apt install python3-pip    

sudo apt install virtualenv

## Now install dependency for python3.10 virtual environment:-

sudo apt install python3.10-venv

## Now create virtualenv inside multinote folder with the name 'multinote-env':-

virtualenv -p /usr/bin/python3.10 multinote-env

## Now virtual environment created and activate it by below command.

source ~/multinote/multinote-env/bin/activate


## Now install Redis and celery at the ubuntu machine.

sudo apt update

sudo apt install redis-server

sudo systemctl start redis-server

## Now we will install superwisor for run celery in deamon mode.

sudo apt update

sudo apt-get install supervisor

sudo mkdir /var/log/celery

sudo touch /var/log/celery/worker.err.log

sudo touch /var/log/celery/worker.out.log

## Now set configuration file for superwirosr.

## Create 'celery_worker.conf' at the below location.

sudo vim /etc/supervisor/conf.d/celery_worker.conf

## add below line in celery_worker.conf file.

[program:celery_worker]
command=/home/ubuntu/multinote/multinote-env/bin/celery -A backend worker -l info
directory=/home/ubuntu/multinote/commonai-backend
user=ubuntu
autostart=true
autorestart=true
stderr_logfile=/var/log/celery/celery_worker.err.log
stdout_logfile=/var/log/celery/celery_worker.out.log

## Now relaod the supervisor and check the status of superwisor.

sudo supervisorctl reload

sudo supervisorctl status

## supervisor status should be like this:-

anil@anil:~$ sudo supervisorctl status

celery_worker                    RUNNING   pid 1182, uptime 0:13:11



## Now goto commonai-backend folder.

cd commonai-backend

## Now inside commonai-backend folder run all pip package by requirements.txt file.

pip install -r requirements.txt


## All dependency will be installed. Run below migration command

python manage.py makemigrations

python manage.py migrate

## Now run final command

## Baserul will be http://ip-address:8000

python manage.py runserver 0.0.0.0:8000


