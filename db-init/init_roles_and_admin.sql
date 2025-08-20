-- Only create roles if they don't exist
INSERT IGNORE INTO role (id, name) VALUES
  (4, 'View Only'),
  (3, 'General User'),
  (2, 'Database Administrator'),
  (1, 'System Administrator');

-- Only create admin user if it doesn't exist
INSERT INTO user (login_id, name, role_id)
SELECT * FROM (SELECT 'admin', 'Admin User', 1) AS tmp
WHERE NOT EXISTS (
    SELECT 1 FROM user WHERE login_id = 'admin'
) LIMIT 1;
