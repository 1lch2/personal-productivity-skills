class UserRepository:
    def __init__(self):
        self.rows = []

    def save(self, user):
        self.rows.append(user)
        return user


class UserService:
    def __init__(self, repo):
        self.repo = repo

    def create(self, email):
        return self.repo.save({"email": email})
