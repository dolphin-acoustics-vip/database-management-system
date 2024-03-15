import os

with open(os.path.expanduser("~/.bashrc"), "a") as outfile:
    # 'a' stands for "append"  
    outfile.write("export STADOLPHINACOUSTICS_HOST=localhost")
    outfile.write("export STADOLPHINACOUSTICS_USER=js521")
    outfile.write("export STADOLPHINACOUSTICS_PASSWORD=password1")
    outfile.write("export STADOLPHINACOUSTICS_DATABASE=test_database")
