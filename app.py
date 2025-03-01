from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

friendship = db.Table('friendships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
)


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='_user_post_like_uc'),)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.Text, default='')
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    friends = db.relationship('User', 
                              secondary=friendship,
                              primaryjoin=(friendship.c.user_id == id),
                              secondaryjoin=(friendship.c.friend_id == id),
                              backref=db.backref('followed_by', lazy='dynamic'),
                              lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def add_friend(self, user):
        if not self.is_friend(user):
            self.friends.append(user)
            
    def remove_friend(self, user):
        if self.is_friend(user):
            self.friends.remove(user)
            
    def is_friend(self, user):
        return self.friends.filter(friendship.c.friend_id == user.id).count() > 0
    
    def friend_posts(self):
        friend_ids = [user.id for user in self.friends]
        friend_ids.append(self.id)  # Include own posts
        return Post.query.filter(Post.user_id.in_(friend_ids)).order_by(Post.timestamp.desc())
    
    def like_post(self, post):
        if not self.has_liked_post(post):
            like = Like(user_id=self.id, post_id=post.id)
            db.session.add(like)

    def unlike_post(self, post):
        if self.has_liked_post(post):
            Like.query.filter_by(user_id=self.id, post_id=post.id).delete()
            
    def has_liked_post(self, post):
        return Like.query.filter_by(user_id=self.id, post_id=post.id).count() > 0


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.relationship('Like', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    
    def likes_count(self):
        return self.likes.count()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        posts = current_user.friend_posts().all()
    else:
        posts = Post.query.order_by(Post.timestamp.desc()).limit(5).all()
    return render_template('index.html', posts=posts)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()
        
        if user_exists:
            flash('Username already exists.')
            return redirect(url_for('signup'))
        
        if email_exists:
            flash('Email already registered.')
            return redirect(url_for('signup'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully!')
        return redirect(url_for('login'))
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.timestamp.desc()).all()
    friends = user.friends.all()
    return render_template('profile.html', user=user, posts=posts, friends=friends)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.bio = request.form.get('bio')
        db.session.commit()
        flash('Your profile has been updated!')
        return redirect(url_for('profile', username=current_user.username))
    
    return render_template('editprofile.html')


@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required!')
            return redirect(url_for('create_post'))
        
        post = Post(title=title, content=content, author=current_user)
        db.session.add(post)
        db.session.commit()
        
        flash('Your post has been created!')
        return redirect(url_for('index'))
    
    return render_template('create_post.html')

@login_required
@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)


@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    current_user.like_post(post)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'likes_count': post.likes_count(),
            'liked': True
        })
    
    next_page = request.args.get('next') or url_for('index')
    return redirect(next_page)


@app.route('/unlike/<int:post_id>', methods=['POST'])
@login_required
def unlike_post(post_id):
    post = Post.query.get_or_404(post_id)
    current_user.unlike_post(post)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'likes_count': post.likes_count(),
            'liked': False
        })
    
    next_page = request.args.get('next') or url_for('index')
    return redirect(next_page)


@app.route('/users')
@login_required
def users():
    all_users = User.query.filter(User.id != current_user.id).all()
    return render_template('users.html', users=all_users)


@app.route('/add_friend/<int:user_id>')
@login_required
def add_friend(user_id):
    user = User.query.get_or_404(user_id)
    current_user.add_friend(user)
    db.session.commit()
    flash(f'You are following {user.username}!')
    return redirect(url_for('users'))


@app.route('/remove_friend/<int:user_id>')
@login_required
def remove_friend(user_id):
    user = User.query.get_or_404(user_id)
    current_user.remove_friend(user)
    db.session.commit()
    flash(f'You are no longer following {user.username}')
    return redirect(url_for('users'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)