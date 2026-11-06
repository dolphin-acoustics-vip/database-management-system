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

# Database migrations are applied automatically when OCEAN starts (see ocean/app/migrations.py)

echo "Setting secret key in .env"
sed -i "s/YOUR_SECRET_KEY/$(od  -vN 32 -An -tx1 /dev/urandom | tr -d ' \n' ; echo)/" .env

echo "Setup complete."
