from unittest.mock import Mock

from service import UserService


def test_create_calls_repo():
    repo = Mock()
    service = UserService(repo)

    service.create("a@example.com")

    repo.save.assert_called_once()


def test_create_persists_user():
    class FakeRepo:
        def __init__(self):
            self.rows = []

        def save(self, user):
            self.rows.append(user)
            return user

    repo = FakeRepo()
    service = UserService(repo)

    user = service.create("a@example.com")

    assert repo.rows == [{"email": "a@example.com"}]
    assert user["email"] == "a@example.com"


def test_create_does_not_raise():
    UserService(Mock()).create("a@example.com")
