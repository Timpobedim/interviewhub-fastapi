-- name: get-comments-for-question-by-slug(slug)
SELECT c.id,
       c.body,
       c.created_at,
       c.updated_at,
       u.username AS author_username,
       u.bio      AS author_bio,
       u.image    AS author_image
FROM comments c
         INNER JOIN users u ON u.id = c.author_id
WHERE c.question_id = (SELECT id FROM questions WHERE slug = :slug)
ORDER BY c.created_at, c.id;


-- name: get-comment-by-id-and-slug(comment_id, question_slug)^
SELECT c.id,
       c.body,
       c.created_at,
       c.updated_at,
       u.username AS author_username,
       u.bio      AS author_bio,
       u.image    AS author_image
FROM comments c
         INNER JOIN users u ON u.id = c.author_id
WHERE c.id = :comment_id
  AND c.question_id = (SELECT id FROM questions WHERE slug = :question_slug);


-- name: create-new-comment(body, question_slug, author_username)<!
WITH author_subquery AS (
    SELECT id, username, bio, image
    FROM users
    WHERE username = :author_username
)
INSERT
INTO comments (body, author_id, question_id)
VALUES (:body,
        (SELECT id FROM author_subquery),
        (SELECT id FROM questions WHERE slug = :question_slug))
RETURNING
    id,
    body,
    created_at,
    updated_at,
    (SELECT username FROM author_subquery) AS author_username,
    (SELECT bio FROM author_subquery)      AS author_bio,
    (SELECT image FROM author_subquery)    AS author_image;


-- name: delete-comment-by-id(comment_id, author_username)!
DELETE
FROM comments
WHERE id = :comment_id
  AND author_id = (SELECT id FROM users WHERE username = :author_username);
