-- name: get-question-by-slug(slug)^
SELECT q.id,
       q.slug,
       q.title,
       q.summary,
       q.answer,
       q.grade,
       q.company,
       q.created_at,
       q.updated_at,
       u.username AS author_username,
       u.bio      AS author_bio,
       u.image    AS author_image
FROM questions q
         INNER JOIN users u ON u.id = q.author_id
WHERE q.slug = :slug
LIMIT 1;


-- name: create-new-question(slug, title, summary, answer, grade, company, author_username)<!
WITH author_subquery AS (
    SELECT id, username, bio, image
    FROM users
    WHERE username = :author_username
)
INSERT
INTO questions (slug, title, summary, answer, grade, company, author_id)
VALUES (:slug, :title, :summary, :answer, :grade, :company, (SELECT id FROM author_subquery))
RETURNING
    id,
    slug,
    title,
    summary,
    answer,
    grade,
    company,
    created_at,
    updated_at,
    (SELECT username FROM author_subquery) AS author_username,
    (SELECT bio FROM author_subquery)      AS author_bio,
    (SELECT image FROM author_subquery)    AS author_image;


-- name: add-tags-to-question*!
INSERT INTO questions_to_tags (question_id, tag)
VALUES ((SELECT id FROM questions WHERE slug = :slug),
        (SELECT tag FROM tags WHERE tag = :tag))
ON CONFLICT DO NOTHING;


-- name: remove-all-tags-from-question(slug)!
DELETE
FROM questions_to_tags
WHERE question_id = (SELECT id FROM questions WHERE slug = :slug);


-- name: update-question(slug, author_username, new_slug, new_title, new_summary, new_answer, new_grade, new_company)<!
UPDATE questions
SET slug    = :new_slug,
    title   = :new_title,
    summary = :new_summary,
    answer  = :new_answer,
    grade   = :new_grade,
    company = :new_company
WHERE slug = :slug
  AND author_id = (SELECT id FROM users WHERE username = :author_username)
RETURNING updated_at;


-- name: delete-question(slug, author_username)!
DELETE
FROM questions
WHERE slug = :slug
  AND author_id = (SELECT id FROM users WHERE username = :author_username);


-- name: add-question-to-favorites(username, slug)!
INSERT INTO favorites (user_id, question_id)
VALUES ((SELECT id FROM users WHERE username = :username),
        (SELECT id FROM questions WHERE slug = :slug))
ON CONFLICT DO NOTHING;


-- name: remove-question-from-favorites(username, slug)!
DELETE
FROM favorites
WHERE user_id = (SELECT id FROM users WHERE username = :username)
  AND question_id = (SELECT id FROM questions WHERE slug = :slug);


-- name: get-tags-for-questions(question_ids)
-- Пакетная загрузка тегов для страницы вопросов (без N+1 запросов).
SELECT question_id, tag
FROM questions_to_tags
WHERE question_id = ANY (CAST(:question_ids AS integer[]))
ORDER BY tag;


-- name: get-favorites-counts-for-questions(question_ids)
SELECT question_id, count(*) AS favorites_count
FROM favorites
WHERE question_id = ANY (CAST(:question_ids AS integer[]))
GROUP BY question_id;


-- name: get-favorited-question-ids-for-user(username, question_ids)
SELECT question_id
FROM favorites
WHERE user_id = (SELECT id FROM users WHERE username = :username)
  AND question_id = ANY (CAST(:question_ids AS integer[]));


-- name: get-questions-for-feed(follower_username, limit, offset)
SELECT q.id,
       q.slug,
       q.title,
       q.summary,
       q.answer,
       q.grade,
       q.company,
       q.created_at,
       q.updated_at,
       u.username AS author_username,
       u.bio      AS author_bio,
       u.image    AS author_image
FROM questions q
         INNER JOIN followers_to_followings f ON f.following_id = q.author_id
         INNER JOIN users u ON u.id = q.author_id
WHERE f.follower_id = (SELECT id FROM users WHERE username = :follower_username)
ORDER BY q.created_at DESC, q.id DESC
LIMIT :limit OFFSET :offset;


-- name: count-questions-for-feed(follower_username)$
SELECT count(*)
FROM questions q
         INNER JOIN followers_to_followings f ON f.following_id = q.author_id
WHERE f.follower_id = (SELECT id FROM users WHERE username = :follower_username);
