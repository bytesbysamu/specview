"""Tests for the User SQLModel entity."""
from datetime import datetime

from modules.auth.models import User


def test_user_default_plan_is_free():
    user = User(auth_user_id="sub_abc123", email="test@example.com")
    assert user.plan == "free", "User.plan must default to 'free'"


def test_user_id_is_none_before_persist():
    user = User(auth_user_id="sub_abc123", email="test@example.com")
    assert user.id is None, "User.id must be None before database insertion"


def test_user_created_at_set_on_instantiation():
    user = User(auth_user_id="sub_abc123", email="test@example.com")
    assert isinstance(user.created_at, datetime), \
        "User.created_at must be a datetime instance"


def test_user_table_registered_in_sqlmodel_metadata():
    from sqlmodel import SQLModel
    tables = SQLModel.metadata.tables
    assert "user" in tables, \
        f"'user' table must be in SQLModel.metadata; found: {list(tables)}"


def test_user_auth_user_id_has_index():
    from sqlmodel import SQLModel
    table = SQLModel.metadata.tables["user"]
    index_cols = {
        col.name
        for idx in table.indexes
        for col in idx.columns
    }
    assert "auth_user_id" in index_cols, \
        "User.auth_user_id must be covered by a database index"
