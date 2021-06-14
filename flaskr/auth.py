import functools
from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from datetime import timezone, datetime, timedelta
import pytz
from flaskr.db import get_db
import re
from werkzeug.utils import secure_filename
import os
from os.path import join, dirname, realpath
import uuid

bp = Blueprint("auth", __name__, url_prefix="/auth")



def login_required(view):
    """View decorator that redirects anonymous users to the login page."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        )


@bp.route("/register", methods=("GET", "POST"))
def register():
    """Register a new user.

    Validates that the username is not already taken. Hashes the
    password for security.
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        useremail = request.form.get("useremail")

        db = get_db()
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        elif not useremail:
            error = "Email is required."
        
        elif (
            db.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
            is not None
        ):
            error = f"User {username} is already registered."

        if error is None:
            # the name is available, store it in the database and go to
            # the login page
            db.execute(
                "INSERT INTO user (username, password,useremail) VALUES (?, ?,?)",
                # (username, generate_password_hash(password)),
                (username, generate_password_hash(password),useremail),
            )
            db.commit()
            return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Log in a registered user by adding the user id to the session."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        time=datetime.now(pytz.timezone('America/New_York'))
        db = get_db()
        error = None
        user = db.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()
        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user["password"], password):
            error = "Incorrect password."
        
        if error is None:
            # store the user id in a new session and return to the index
            session.clear()
            # update login time
            session["user_id"] = user["id"]
            db.execute(
                "UPDATE user SET last_login=? WHERE id=?",
                (time,user['id']),
            )
            db.commit()
            
            if user['user_type'] == 'admin':
      
                return redirect(url_for("auth.admin"))
            # db.execute(
            # "UPDATE user SET user_type='admin' WHERE username='admin'",
            # )
           
            # db.commit()

            return redirect(url_for("blog.index"))

        flash(error)

    return render_template("auth/login.html")

UPLOAD_FOLDER = './static/upload'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/update", methods=("GET", "POST"))
@login_required
def update():
    """update user information"""
    user_id = session.get("user_id")
    if request.method == "POST":
        nickname = request.form["nickname"]
        aboutme = request.form["aboutme"]
        website = request.form["website"]
        if not re.match("https?://.*",website):
            website="http://"+website 
        # time=datetime.now(pytz.timezone('America/New_York'))
        
        db = get_db()
        pfp=db.execute("SELECT pfp FROM user WHERE id=?",(user_id,)).fetchone()[0]

        if 'file' not in request.files:
            flash('No file part')
            print('No file part')
            # return render_template("auth/edit.html")
        else:
            file = request.files['file']
            # if user does not select file, browser also
            # submit a empty part without filename
            if file.filename == '':
                flash('No selected file')
                print('No selected file')
                return render_template("auth/edit.html")
            if file and allowed_file(file.filename):
                filename = secure_filename(str(user_id)+"-"+str(uuid.uuid4())+file.filename)
                # file.save(os.path.join(UPLOAD_FOLDER, filename))
                UPLOADS_PATH = join(dirname(realpath(__file__)), 'static/upload/pfp')
                file.save(os.path.join(UPLOADS_PATH, filename))
                pfp='/static/upload/pfp/'+filename
        db = get_db()
        error = None
        # if not title:
        #     error = "Title is required."
        
        print(pfp)
        if error is not None:
            flash(error)
        else:
            
            db.execute(
                "UPDATE user SET nickname = ?, website = ?, About = ? , pfp = ?  WHERE id = ?", (nickname, website,aboutme, pfp, user_id )
            )
            db.commit()
            return redirect(url_for("index"))
    return render_template("auth/edit.html")

@bp.route("/<int:id>/follow", methods=("GET", "POST"))
@login_required
def follow(id):
    """follow another user"""
    user_id = session.get("user_id")
    if request.method == "POST":
        db = get_db()
        # current user (user_id) follows profile user (id)
        check = db.execute(
           " SELECT * FROM follow WHERE user_id = ? AND follows_id = ?", (user_id ,id,),
        ).fetchone()
        if not check:
            db.execute(
                "INSERT INTO follow (user_id, follows_id) VALUES (?, ?) ",(user_id ,id,),
            )
            db.commit()
        return redirect(url_for("blog.profile",id=id))

@bp.route("/<int:id>/unfollow", methods=("GET", "POST"))
@login_required
def unfollow(id):
    """follow another user"""
    user_id = session.get("user_id")
    if request.method == "POST":
        db = get_db()
        # current user (user_id) follows profile user (id)
        # delete this relationship
        check = db.execute(
           " SELECT * FROM follow WHERE user_id = ? AND follows_id = ?", (user_id ,id,),
        ).fetchone()
        if check:
            db.execute(
                "DELETE FROM follow WHERE user_id=? AND follows_id=? ",(user_id ,id,),
            )
            db.commit()
        return redirect(url_for("blog.profile",id=id))  

@bp.route("/<int:id>/following", methods=("GET", "POST"))
@login_required
def following(id):
    """show this user's following other user"""
    db = get_db()
    # current user (user_id) follows profile user (id)
    follows=db.execute(
        " SELECT * "
        " FROM follow f JOIN user u ON f.follows_id=u.id"
        " WHERE f.user_id = ? ", (id,),
        ).fetchall()
    
    return render_template("auth/following.html",follows=follows)

@bp.route("/<int:id>/followers", methods=("GET", "POST"))
@login_required
def followers(id):
    """show this user's followers"""
    db = get_db()
    # current user (user_id) follows profile user (id)
    followers=db.execute(
        " SELECT * "
        " FROM follow f JOIN user u ON f.user_id=u.id"
        " WHERE f.follows_id = ? ", (id,),
        ).fetchall()

    return render_template("auth/followers.html",followers=followers)


@bp.route("/logout")
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()
    return redirect(url_for("index"))

@bp.route("/admin")
def admin():
    return render_template("admin/index.html")

@bp.route("/adminusers")
def adminusers():
    db=get_db()
    users=db.execute("SELECT * FROM user").fetchall()
    return render_template("admin/users.html",users=users)

@bp.route("/adminposts")
def adminposts():
    return render_template("admin/posts.html")