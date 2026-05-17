from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, default="")
    website = db.Column(db.String(300), default="")
    linkedin = db.Column(db.String(300), default="")
    scholar = db.Column(db.String(300), default="")
    expertise_keywords = db.Column(db.String(500), default="")
    research_interests = db.Column(db.String(500), default="")
    role = db.Column(db.String(20), default="user")
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    projects = db.relationship("Project", backref="owner", lazy=True)
    bids = db.relationship("Bid", backref="bidder", lazy=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def expertise_list(self):
        return [k.strip() for k in (self.expertise_keywords or "").split(",") if k.strip()]

    @property
    def research_interests_list(self):
        return [k.strip() for k in (self.research_interests or "").split(",") if k.strip()]

    @property
    def initials(self):
        return self.name[0].upper() if self.name else "?"

    @property
    def avatar_color(self):
        colors = [
            "from-violet-500 to-purple-600",
            "from-blue-500 to-cyan-500",
            "from-emerald-500 to-teal-500",
            "from-amber-500 to-orange-500",
            "from-rose-500 to-pink-500",
            "from-indigo-500 to-blue-500",
        ]
        return colors[sum(ord(c) for c in str(self.id)) % len(colors)]


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    mode = db.Column(db.String(20), default="public")
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="open")
    expertise_keywords = db.Column(db.String(500), default="")
    impact_areas = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    bids = db.relationship("Bid", backref="project", lazy=True, cascade="all, delete-orphan")
    discussion_posts = db.relationship("DiscussionPost", backref="project", lazy=True, cascade="all, delete-orphan", order_by="DiscussionPost.created_at")

    @property
    def expertise_list(self):
        return [k.strip() for k in (self.expertise_keywords or "").split(",") if k.strip()]

    @property
    def impact_areas_list(self):
        return [k.strip() for k in (self.impact_areas or "").split(",") if k.strip()]

    @property
    def is_past_deadline(self):
        if self.deadline:
            return self.deadline < datetime.now(timezone.utc).date()
        return False

    @property
    def is_closed(self):
        return self.status == "closed" or self.is_past_deadline


class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sender = db.relationship("User", foreign_keys=[from_id])
    recipient = db.relationship("User", foreign_keys=[to_id])


class DiscussionPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    author = db.relationship("User", foreign_keys=[user_id])


class AIRecommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    result_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    project = db.relationship("Project", backref="recommendations")