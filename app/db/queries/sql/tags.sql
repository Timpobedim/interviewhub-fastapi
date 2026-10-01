-- name: get-all-tags()
SELECT tag
FROM tags
ORDER BY tag;


-- name: create-new-tags*!
INSERT INTO tags (tag)
VALUES (:tag)
ON CONFLICT DO NOTHING;
