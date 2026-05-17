import os
import json
from datetime import datetime, timezone

import requests as http_requests
from flask import (
    Flask, render_template, redirect, url_for, flash, request, abort
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from dotenv import load_dotenv

from models import db, User, Project, Bid, Message, AIRecommendation, DiscussionPost

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///collabhub.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_globals():
    unread = 0
    pending_count = 0
    if current_user.is_authenticated:
        unread = Message.query.filter_by(to_id=current_user.id, read=False).count()
        if current_user.role == "admin":
            pending_count = User.query.filter_by(status="pending").count()
    return dict(unread_count=unread, pending_user_count=pending_count)


# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))
        if user.status == "pending":
            flash("Your account is pending admin approval.", "warning")
            return redirect(url_for("login"))
        if user.status == "rejected":
            flash("Your account was not approved.", "error")
            return redirect(url_for("login"))
        login_user(user)
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for("register"))
        user = User(
            email=email,
            name=request.form.get("name", "").strip(),
            bio=request.form.get("bio", "").strip(),
            website=request.form.get("website", "").strip(),
            linkedin=request.form.get("linkedin", "").strip(),
            scholar=request.form.get("scholar", "").strip(),
        )
        user.set_password(request.form.get("password", ""))
        db.session.add(user)
        db.session.commit()
        flash("Registration submitted! An administrator will review your account.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    my_projects = Project.query.filter_by(owner_id=current_user.id).count()
    my_bids = Bid.query.filter_by(user_id=current_user.id).count()
    open_calls = Project.query.filter(
        Project.mode == "public",
        Project.status == "open",
        Project.owner_id != current_user.id,
    ).all()
    open_calls = [p for p in open_calls if not p.is_past_deadline]
    return render_template("dashboard.html", my_projects=my_projects, my_bids=my_bids, open_calls=open_calls)


# ── EXPLORE ───────────────────────────────────────────────────────────────────

@app.route("/explore/projects")
@login_required
def explore_projects():
    q = request.args.get("q", "").strip()
    query = Project.query.filter_by(mode="public").order_by(Project.created_at.desc())
    if q:
        query = query.filter(Project.title.ilike(f"%{q}%") | Project.description.ilike(f"%{q}%"))
    return render_template("explore_projects.html", projects=query.all(), q=q)


@app.route("/explore/people")
@login_required
def explore_people():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(status="approved").filter(User.role != "admin")
    if q:
        query = query.filter(User.name.ilike(f"%{q}%") | User.bio.ilike(f"%{q}%"))
    return render_template("explore_people.html", users=query.all(), q=q)


# ── PROFILE ───────────────────────────────────────────────────────────────────

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        current_user.name = request.form.get("name", "").strip() or current_user.name
        current_user.bio = request.form.get("bio", "").strip()
        current_user.website = request.form.get("website", "").strip()
        current_user.linkedin = request.form.get("linkedin", "").strip()
        current_user.scholar = request.form.get("scholar", "").strip()
        current_user.expertise_keywords = request.form.get("expertise_keywords", "").strip()
        current_user.research_interests = request.form.get("research_interests", "").strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    return render_template("edit_profile.html")


@app.route("/user/<int:user_id>")
@login_required
def view_user(user_id):
    user = db.session.get(User, user_id)
    if not user or user.status != "approved":
        abort(404)
    return render_template("view_user.html", user=user)


# ── PROJECTS ──────────────────────────────────────────────────────────────────

@app.route("/projects")
@login_required
def my_projects():
    projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.created_at.desc()).all()
    return render_template("my_projects.html", projects=projects)


@app.route("/projects/new", methods=["GET", "POST"])
@login_required
def new_project():
    if request.method == "POST":
        deadline_str = request.form.get("deadline", "").strip()
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        project = Project(
            owner_id=current_user.id,
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", "").strip(),
            mode=request.form.get("mode", "public"),
            deadline=deadline,
            expertise_keywords=request.form.get("expertise_keywords", "").strip(),
            impact_areas=request.form.get("impact_areas", "").strip(),
        )
        db.session.add(project)
        db.session.commit()
        flash("Project created!", "success")
        if project.mode == "private":
            candidates = User.query.filter(
                User.status == "approved", User.role != "admin", User.id != current_user.id
            ).all()
            _run_ai_recommendation(project, candidates)
            return redirect(url_for("project_detail", project_id=project.id))
        return redirect(url_for("my_projects"))
    return render_template("new_project.html")


@app.route("/projects/<int:project_id>")
@login_required
def project_detail(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)
    if project.mode == "private" and project.owner_id != current_user.id:
        abort(403)

    is_owner = project.owner_id == current_user.id
    user_bid = Bid.query.filter_by(project_id=project.id, user_id=current_user.id).first()
    bids = project.bids if is_owner else []
    recommendation = (
        AIRecommendation.query.filter_by(project_id=project.id)
        .order_by(AIRecommendation.created_at.desc()).first()
    )
    rec_data = json.loads(recommendation.result_json) if recommendation else None

    if rec_data and "teams" in rec_data:
        for team in rec_data["teams"]:
            for member in team.get("members", []):
                mid = member.get("id", "")
                u = db.session.get(User, int(mid)) if str(mid).isdigit() else None
                member["user_obj"] = u

    discussion_posts = project.discussion_posts

    return render_template("project_detail.html", project=project, is_owner=is_owner,
                           user_bid=user_bid, bids=bids, rec_data=rec_data,
                           discussion_posts=discussion_posts)


@app.route("/projects/<int:project_id>/bid", methods=["POST"])
@login_required
def place_bid(project_id):
    project = db.session.get(Project, project_id)
    if not project or project.is_closed or project.owner_id == current_user.id:
        abort(400)
    if Bid.query.filter_by(project_id=project_id, user_id=current_user.id).first():
        flash("You already submitted interest.", "warning")
        return redirect(url_for("project_detail", project_id=project_id))
    bid = Bid(project_id=project_id, user_id=current_user.id,
              message=request.form.get("message", "").strip())
    db.session.add(bid)
    db.session.commit()
    flash("Interest submitted!", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/discuss", methods=["POST"])
@login_required
def post_discussion(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)
    if project.mode == "private" and project.owner_id != current_user.id:
        abort(403)
    text = request.form.get("text", "").strip()
    if not text:
        flash("Message cannot be empty.", "warning")
        return redirect(url_for("project_detail", project_id=project_id))
    post = DiscussionPost(project_id=project_id, user_id=current_user.id, text=text)
    db.session.add(post)
    db.session.commit()
    return redirect(url_for("project_detail", project_id=project_id) + "#discussion")


@app.route("/projects/<int:project_id>/close", methods=["POST"])
@login_required
def close_project(project_id):
    project = db.session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        abort(403)
    project.status = "closed"
    db.session.commit()
    bidders = [b.bidder for b in project.bids]
    if bidders:
        _run_ai_recommendation(project, bidders)
    flash("Project closed. AI recommendations generated.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/recommend", methods=["POST"])
@login_required
def rerun_recommendation(project_id):
    project = db.session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        abort(403)
    if project.mode == "private":
        candidates = User.query.filter(
            User.status == "approved", User.role != "admin", User.id != current_user.id
        ).all()
    else:
        candidates = [b.bidder for b in project.bids]
    _run_ai_recommendation(project, candidates)
    flash("AI recommendation refreshed.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


def _run_ai_recommendation(project, candidates):
    if not candidates:
        return
    if not ANTHROPIC_API_KEY:
        rec = AIRecommendation(
            project_id=project.id,
            result_json=json.dumps({"error": "No API key configured. Set ANTHROPIC_API_KEY in your .env file."}),
        )
        db.session.add(rec)
        db.session.commit()
        return

    cand_text = "\n".join(f"- {c.name} (ID: {c.id}): {c.bio}" for c in candidates)
    prompt = (
        f'You are a team-formation assistant. Given a project and candidates, '
        f'recommend 1-2 best team(s) of 2-4 members and explain why.\n\n'
        f'PROJECT: "{project.title}"\nDESCRIPTION: {project.description}\n\n'
        f'CANDIDATES:\n{cand_text}\n\n'
        f'Respond ONLY in this JSON format, no markdown fences:\n'
        f'{{"teams":[{{"members":[{{"id":"...","name":"...","role_in_team":"..."}}],'
        f'"rationale":"..."}}],"overall_reasoning":"..."}}'
    )
    try:
        resp = http_requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 1024,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []))
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
    except Exception as e:
        result = {"error": f"AI recommendation failed: {str(e)}"}

    rec = AIRecommendation(project_id=project.id, result_json=json.dumps(result))
    db.session.add(rec)
    db.session.commit()


# ── MESSAGES ──────────────────────────────────────────────────────────────────

@app.route("/messages")
@login_required
def messages_list():
    sent = db.session.query(Message.to_id).filter_by(from_id=current_user.id).distinct()
    received = db.session.query(Message.from_id).filter_by(to_id=current_user.id).distinct()
    peer_ids = set(r[0] for r in sent) | set(r[0] for r in received)
    peers = []
    for pid in peer_ids:
        peer = db.session.get(User, pid)
        if not peer:
            continue
        last_msg = Message.query.filter(
            ((Message.from_id == current_user.id) & (Message.to_id == pid)) |
            ((Message.from_id == pid) & (Message.to_id == current_user.id))
        ).order_by(Message.created_at.desc()).first()
        unread = Message.query.filter_by(from_id=pid, to_id=current_user.id, read=False).count()
        peers.append({"user": peer, "last_msg": last_msg, "unread": unread})
    peers.sort(key=lambda x: x["last_msg"].created_at if x["last_msg"] else datetime.min, reverse=True)
    return render_template("messages.html", peers=peers)


@app.route("/messages/<int:peer_id>", methods=["GET", "POST"])
@login_required
def thread(peer_id):
    peer = db.session.get(User, peer_id)
    if not peer:
        abort(404)
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if text:
            db.session.add(Message(from_id=current_user.id, to_id=peer_id, text=text))
            db.session.commit()
        return redirect(url_for("thread", peer_id=peer_id))
    Message.query.filter_by(from_id=peer_id, to_id=current_user.id, read=False).update({"read": True})
    db.session.commit()
    msgs = Message.query.filter(
        ((Message.from_id == current_user.id) & (Message.to_id == peer_id)) |
        ((Message.from_id == peer_id) & (Message.to_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()
    return render_template("thread.html", peer=peer, msgs=msgs)


@app.route("/messages/<int:peer_id>/send", methods=["POST"])
@login_required
def send_quick_message(peer_id):
    text = request.form.get("text", "").strip()
    if text:
        db.session.add(Message(from_id=current_user.id, to_id=peer_id, text=text))
        db.session.commit()
        flash("Message sent!", "success")
    return redirect(url_for("view_user", user_id=peer_id))


# ── ADMIN ─────────────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required
def admin_panel():
    if current_user.role != "admin":
        abort(403)
    pending = User.query.filter_by(status="pending").all()
    approved = User.query.filter_by(status="approved").filter(User.role != "admin").all()
    rejected = User.query.filter_by(status="rejected").all()
    return render_template("admin.html", pending=pending, approved=approved, rejected=rejected)


@app.route("/admin/approve/<int:user_id>", methods=["POST"])
@login_required
def approve_user(user_id):
    if current_user.role != "admin":
        abort(403)
    user = db.session.get(User, user_id)
    if user:
        user.status = "approved"
        db.session.commit()
        flash(f"{user.name} approved.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/reject/<int:user_id>", methods=["POST"])
@login_required
def reject_user(user_id):
    if current_user.role != "admin":
        abort(403)
    user = db.session.get(User, user_id)
    if user:
        user.status = "rejected"
        db.session.commit()
        flash(f"{user.name} rejected.", "success")
    return redirect(url_for("admin_panel"))


# ── INIT ──────────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5000)