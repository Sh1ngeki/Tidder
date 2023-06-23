from flask import Flask, redirect, url_for, render_template, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_required, logout_user, LoginManager, login_user, UserMixin

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tiddertidder'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    author = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    author = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    comments = db.relationship('Comment', backref='post', passive_deletes=True)


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    posts = db.relationship('Post', backref='users', passive_deletes=True)
    comments = db.relationship('Comment', backref='users', passive_deletes=True)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password

    def get_id(self):
        return str(self.id)


with app.app_context():
    # db.session.query(Users).delete()
    # db.session.commit()
    db.create_all()


@login_manager.user_loader
def load_user(id):
    return Users.query.get(int(id))


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Users.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                flash("Logged in!", category='success')
                login_user(user, remember=True)
                return redirect(url_for('feed'))
            else:
                flash('Password is Incorrect!', category='error')
        else:
            flash('Username does not exist', category='error')
    return render_template('index.html', user=current_user)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        user_exists = Users.query.filter_by(username=username).first()
        email_exists = Users.query.filter_by(email=email).first()
        if email_exists:
            flash('Email is already in use.', category='error')
        elif user_exists:
            flash('Username is already in use.', category='error')
        elif len(username) < 3:
            flash('Username is too short.', category='error')
        elif len(password) < 8:
            flash('Password is too short, at least 8 characters.', category='error')
        elif len(email) < 10:
            flash('Email is invalid', category='error')
        else:
            new_user = Users(email=email, username=username, password=generate_password_hash(password, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            flash('User Create!')
            login_user(new_user, remember=True)
            return redirect(url_for('feed'))
    return render_template('signup.html', user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/forgotusername')
def forgot_username():
    return render_template('resetusername.html')


@app.route('/forgotpassword')
def forgot_password():
    return render_template('resetpassword.html')


@app.route('/feed')
def feed():
    posts = Post.query.all()
    return render_template('home.html', user=current_user, posts=posts)


@app.route('/createpost', methods=['GET', 'POST'])
@login_required
def createpost():
    if request.method == 'POST':
        text = request.form.get('text')
        if not text:
            flash('Post cannot be empty', category='error')
        else:
            post = Post(text=text, author=current_user.id)
            db.session.add(post)
            db.session.commit()
            flash('Post created!', category='success')
            return redirect(url_for('feed'))
    return render_template('create_post.html', user=current_user)


# using dymanic path/route
@app.route('/delete-post/<id>')
@login_required
def delete_post(id):
    post = Post.query.filter_by(id=id).first()
    if not post:
        flash("Post does not exist.", category='error')
    # elif current_user.id != post.id:
    #     flash('You do not have permission to delete this post.', category='error')
    else:
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted', category='success')
    return redirect(url_for('feed'))


@app.route('/create-comment/<post_id>')
@login_required
def create_comment(post_id):
    post_ = Post.query.filter_by(id=post_id).first()
    return render_template('comment.html', user=current_user, post_=post_)


@app.route('/write-comment/<post_id>', methods=['POST'])
@login_required
def writecomment(post_id):
    post = Post.query.filter_by(id=post_id).first()
    comment_text = request.form.get('comment-text')
    if not comment_text:
        flash('Comment cannot be empty!', category='error')
    else:
        if post:
            comment = Comment(text=comment_text, author=current_user.id, post_id=post_id)
            db.session.add(comment)
            db.session.commit()
            flash('Comment added', category='success')
        else:
            flash('Post does not exist.', category='error')
    return redirect(url_for('create_comment', post_id=post_id))


@app.route('/delete-comment/<comment_id>')
@login_required
def delete_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if not comment:
        flash('Comment does not exist', category='error')
    elif current_user.id != comment.author and current_user.id != comment.post.author:
        flash('You do not have permission to delete this comment.', category='error')
    else:
        post_id = comment.post_id
        db.session.delete(comment)
        db.session.commit()
        flash('Comment deleted', category='success')
    return redirect(url_for('create_comment', post_id=post_id))


@app.route('/profile/<username>')
@login_required
def profile(username):
    user = Users.query.filter_by(username=username).first()
    if not user:
        flash('No user with that username exists.', category='error')
        return redirect(url_for('feed'))
    posts = Post.query.filter_by(author=user.id).all()
    # posts = Users.posts
    return render_template('satestod.html', user=current_user, posts=posts, username=username)


@app.route('/react')
def react():
    pass



if __name__ == "__main__":
    app.run(debug=True)
