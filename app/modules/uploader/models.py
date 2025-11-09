from app import db


class Uploader(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return f'Uploader<{self.id}>'
