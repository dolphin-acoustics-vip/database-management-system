#!/usr/bin/env bash

source .env

env_dir="env"

if [ -d $env_dir ]; then
    echo "Virtual env already exists."
else
    echo "Creating virtual env."
    python3 -m venv $env_dir
fi

echo "Activating virtual env."
source "./$env_dir/bin/activate"

echo "Making sure pip is up-to-date."
pip install -U pip

echo "Installing requirements."
pip install -r requirements.txt

echo "Deactivating virtual env."
deactivate

DB_HOST=$DEV_STADOLPHINACOUSTICS_HOST
DB_USER=$DEV_STADOLPHINACOUSTICS_USER
DB_PASSWORD=$DEV_STADOLPHINACOUSTICS_PASSWORD
DB_NAME=$DEV_STADOLPHINACOUSTICS_DATABASE
if [ -z "$DB_PASSWORD" ]
then
    DB_HOST=$PROD_STADOLPHINACOUSTICS_HOST
    DB_USER=$PROD_STADOLPHINACOUSTICS_USER
    DB_PASSWORD=$PROD_STADOLPHINACOUSTICS_PASSWORD
    DB_NAME=$PROD_STADOLPHINACOUSTICS_DATABASE
fi
echo "Updating database ${DB_NAME} on ${DB_HOST} as ${DB_USER} with script_run.sql"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < script_run.sql

echo "Setting secret key in .env"
sed -i "s/YOUR_SECRET_KEY/$(od  -vN 32 -An -tx1 /dev/urandom | tr -d ' \n' ; echo)/" .env

echo "Setup complete."
