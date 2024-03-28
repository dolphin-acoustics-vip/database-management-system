import os

with open(os.path.expanduser("~/.bashrc"), "a") as outfile:
    # note the <host> is usually localhost
    # note the <user_name> is usually root
    # note the <user_password> is updated in the MariaDB shell with
    #       mysql> ALTER USER 'user_name'@'host' IDENTIFIED BY 'user_password';
    outfile.write("export STADOLPHINACOUSTICS_HOST=<host>")
    outfile.write("export STADOLPHINACOUSTICS_USER=<user_name>")
    outfile.write("export STADOLPHINACOUSTICS_PASSWORD=<user_password>")
    outfile.write("export STADOLPHINACOUSTICS_DATABASE=<database_name>")
