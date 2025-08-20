-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS `${MARIADB_DATABASE}`;

-- Create user if it doesn't exist and grant privileges
CREATE USER IF NOT EXISTS '${MARIADB_USER}'@'%' IDENTIFIED BY '${MARIADB_PASSWORD}';
GRANT ALL PRIVILEGES ON `${MARIADB_DATABASE}`.* TO '${MARIADB_USER}'@'%';
FLUSH PRIVILEGES;

-- Use the database
USE `${MARIADB_DATABASE}`;
