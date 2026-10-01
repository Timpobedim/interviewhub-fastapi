-- name: is-user-following-for-another-user(follower_username, following_username)$
SELECT EXISTS(
    SELECT 1
    FROM followers_to_followings f
    WHERE f.follower_id = (SELECT id FROM users WHERE username = :follower_username)
      AND f.following_id = (SELECT id FROM users WHERE username = :following_username)
);


-- name: subscribe-user-to-another(follower_username, following_username)!
INSERT INTO followers_to_followings (follower_id, following_id)
VALUES ((SELECT id FROM users WHERE username = :follower_username),
        (SELECT id FROM users WHERE username = :following_username))
ON CONFLICT DO NOTHING;


-- name: unsubscribe-user-from-another(follower_username, following_username)!
DELETE
FROM followers_to_followings
WHERE follower_id = (SELECT id FROM users WHERE username = :follower_username)
  AND following_id = (SELECT id FROM users WHERE username = :following_username);


-- name: get-followed-usernames-among(follower_username, usernames)
-- Пакетная проверка подписок: одна выборка вместо запроса на каждого автора в списке.
SELECT u.username
FROM followers_to_followings f
         INNER JOIN users u ON u.id = f.following_id
WHERE f.follower_id = (SELECT id FROM users WHERE username = :follower_username)
  AND u.username = ANY (CAST(:usernames AS text[]));
