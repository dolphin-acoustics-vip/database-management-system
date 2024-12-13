### Installing Maria DB v10.5.23 on Linux

Maria DB 10.5.23 is an old version that is used to maintain compatability with the intended production environment of OCEAN. The best way to set up your test environment with this version is to use a container such as Docker. See details below on how to install the required MariaDB version using Docker.

Note that this guide was made using Ubuntu 22.04 (Jammy)

Ensure all current MariaDB servers are removed

`sudo apt-get purge mariadb-server*`

Install Docker

`sudo apt-get update`
`sudo apt-get install docker.io`

Pull the MariaDB image

`sudo docker pull mariadb:10.5.23`

Start a Maria DB container using the image and persist it

`docker run --name mariadb-10.5.23 -e MYSQL_ROOT_PASSWORD=<Password> -v </my/own/datadir>:/var/lib/mysql -p 3306:3306 -d mariadb:10.5.23`

Note: replace <Password> with the password that will be used to access the database.
Note: replace </my/own/datadir> with the desired persistent container location on your drive (this will be mapped to the SQL path, /var/lib/mysql).

Access the MariaDB server environment

`sudo docker exec -it mariadb-10.5.23 mysql -u root -p`
Note: you will be prompted to enter the password you made above.
