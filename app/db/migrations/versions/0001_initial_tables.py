"""initial tables

Revision ID: 0001_initial_tables
Revises:
Create Date: 2026-09-11 10:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import func

revision = "0001_initial_tables"
down_revision = None
branch_labels = None
depends_on = None


def create_updated_at_trigger() -> None:
    op.execute(
        """
        CREATE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS
        $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """,
    )


def add_updated_at_trigger(table: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER update_{table}_modtime
            BEFORE UPDATE
            ON {table}
            FOR EACH ROW
        EXECUTE PROCEDURE update_updated_at_column();
        """,
    )


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )


def create_users_table() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.Text, unique=True, nullable=False, index=True),
        sa.Column("email", sa.Text, unique=True, nullable=False, index=True),
        sa.Column("salt", sa.Text, nullable=False),
        sa.Column("hashed_password", sa.Text),
        sa.Column("bio", sa.Text, nullable=False, server_default=""),
        sa.Column("image", sa.Text),
        *timestamps(),
    )
    add_updated_at_trigger("users")


def create_followers_to_followings_table() -> None:
    op.create_table(
        "followers_to_followings",
        sa.Column(
            "follower_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "following_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_primary_key(
        "pk_followers_to_followings",
        "followers_to_followings",
        ["follower_id", "following_id"],
    )
    op.create_index("ix_followers_following_id", "followers_to_followings", ["following_id"])


def create_questions_table() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.Text, unique=True, nullable=False, index=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("grade", sa.Text, nullable=False),
        sa.Column("company", sa.Text),
        sa.Column(
            "author_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *timestamps(),
        sa.CheckConstraint("grade IN ('junior', 'middle', 'senior')", name="ck_questions_grade"),
    )
    op.create_index("ix_questions_author_id", "questions", ["author_id"])
    op.create_index("ix_questions_grade", "questions", ["grade"])
    op.create_index("ix_questions_created_at", "questions", [sa.text("created_at DESC")])
    add_updated_at_trigger("questions")


def create_tags_table() -> None:
    op.create_table("tags", sa.Column("tag", sa.Text, primary_key=True))


def create_questions_to_tags_table() -> None:
    op.create_table(
        "questions_to_tags",
        sa.Column(
            "question_id",
            sa.Integer,
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tag",
            sa.Text,
            sa.ForeignKey("tags.tag", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_primary_key("pk_questions_to_tags", "questions_to_tags", ["question_id", "tag"])
    op.create_index("ix_questions_to_tags_tag", "questions_to_tags", ["tag"])


def create_favorites_table() -> None:
    op.create_table(
        "favorites",
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer,
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_primary_key("pk_favorites", "favorites", ["user_id", "question_id"])
    op.create_index("ix_favorites_question_id", "favorites", ["question_id"])


def create_comments_table() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column(
            "author_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer,
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *timestamps(),
    )
    op.create_index("ix_comments_question_id", "comments", ["question_id"])
    add_updated_at_trigger("comments")


def upgrade() -> None:
    create_updated_at_trigger()
    create_users_table()
    create_followers_to_followings_table()
    create_questions_table()
    create_tags_table()
    create_questions_to_tags_table()
    create_favorites_table()
    create_comments_table()


def downgrade() -> None:
    op.drop_table("comments")
    op.drop_table("favorites")
    op.drop_table("questions_to_tags")
    op.drop_table("tags")
    op.drop_table("questions")
    op.drop_table("followers_to_followings")
    op.drop_table("users")
    op.execute("DROP FUNCTION update_updated_at_column")
