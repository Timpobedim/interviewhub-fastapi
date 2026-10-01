-- name: get-user-by-email(email)^
SELECT id,
       username,
       email,
       salt,
       hashed_password,
       bio,
       image,
       created_at,
       updated_at
FROM users
WHERE email = :email
LIMIT 1;


-- name: get-user-by-username(username)^
SELECT id,
       username,
       email,
       salt,
       hashed_password,
       bio,
       image,
       created_at,
       updated_at
FROM users
WHERE username = :username
LIMIT 1;


-- name: create-new-user(username, email, salt, hashed_password)<!
INSERT INTO users (username, email, salt, hashed_password)
VALUES (:username, :email, :salt, :hashed_password)
RETURNING id, created_at, updated_at;


-- name: update-user-by-username(username, new_username, new_email, new_salt, new_password, new_bio, new_image)<!
UPDATE users
SET username        = :new_username,
    email           = :new_email,
    salt            = :new_salt,
    hashed_password = :new_password,
    bio             = :new_bio,
    image           = :new_image
WHERE username = :username
RETURNING updated_at;
