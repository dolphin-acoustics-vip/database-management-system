#!/usr/bin/env bash

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
