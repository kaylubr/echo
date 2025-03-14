from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config.update(
    SECRET_KEY='231B',
    SQLALCHEMY_DATABASE_URI='sqlite:///blog.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

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
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    friends = db.relationship(
        'User', 
        secondary=friendship,
        primaryjoin=(friendship.c.user_id == id),
        secondaryjoin=(friendship.c.friend_id == id),
        backref=db.backref('followed_by', lazy='dynamic'),
        lazy='dynamic'
    )
    
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
        friend_ids = [user.id for user in self.friends] + [self.id]
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
    edited = db.Column(db.Boolean, default=False)
    edited_timestamp = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    likes = db.relationship('Like', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    
    def likes_count(self):
        return self.likes.count()
        
    def comments_count(self):
        return self.comments.count()


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    edited = db.Column(db.Boolean, default=False)
    edited_timestamp = db.Column(db.DateTime, nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Helper functions
def is_ajax_request():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def handle_content_validation(content_type, form_data):
    """Validates form content based on content type"""
    if content_type == 'post':
        title, content = form_data.get('title'), form_data.get('content')
        if not title or not content:
            flash(f'Title and content are required!')
            return False
    elif content_type == 'comment':
        content = form_data.get('content')
        if not content:
            flash('Comment cannot be empty!')
            return False
    return True


def handle_edit_timestamps(item):
    """Updates timestamps for edited items"""
    item.edited = True
    item.edited_timestamp = datetime.utcnow()


# Routes
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
        
        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            field = 'Username' if existing_user.username == username else 'Email'
            flash(f'{field} already exists.')
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
        if not handle_content_validation('post', request.form):
            return redirect(url_for('create_post'))
        
        post = Post(
            title=request.form.get('title'),
            content=request.form.get('content'),
            author=current_user
        )
        db.session.add(post)
        db.session.commit()
        
        flash('Your post has been created!')
        return redirect(url_for('index'))
    
    return render_template('create_post.html')


@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.timestamp.asc()).all()
    return render_template('post.html', post=post, comments=comments)


@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if post.author != current_user:
        flash('You can only edit your own posts!')
        return redirect(url_for('post', post_id=post.id))
    
    if request.method == 'POST':
        if not handle_content_validation('post', request.form):
            return redirect(url_for('edit_post', post_id=post.id))
        
        title = request.form.get('title')
        content = request.form.get('content')
        
        if post.title != title or post.content != content:
            post.title = title
            post.content = content
            handle_edit_timestamps(post)
            db.session.commit()
            flash('Your post has been updated!')
        else:
            flash('No changes were made to your post.')
            
        return redirect(url_for('post', post_id=post.id))
    
    return render_template('edit_post.html', post=post)


@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if post.author != current_user:
        flash('You can only delete your own posts!')
        return redirect(url_for('post', post_id=post.id))
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Your post has been deleted!')
    return redirect(url_for('index'))


@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    current_user.like_post(post)
    db.session.commit()
    
    if is_ajax_request():
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
    
    if is_ajax_request():
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
    
    if is_ajax_request():
        users_data = [{
            'id': user.id,
            'username': user.username,
            'join_date': user.join_date.strftime('%B %d, %Y'),
            'is_friend': current_user.is_friend(user)
        } for user in all_users]
        return jsonify({'users': users_data})
    
    return render_template('users.html', users=all_users)


@app.route('/search_users')
@login_required
def search_users():
    query = request.args.get('q', '')
    users = User.query.filter(
        User.id != current_user.id,
        User.username.ilike(f'%{query}%')
    ).all()
    
    users_data = [{
        'id': user.id,
        'username': user.username,
        'join_date': user.join_date.strftime('%B %d, %Y'),
        'is_friend': current_user.is_friend(user)
    } for user in users]
    
    return jsonify({'users': users_data})


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


@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    
    if not handle_content_validation('comment', request.form):
        return redirect(url_for('post', post_id=post_id))
    
    comment = Comment(
        content=request.form.get('content'),
        user_id=current_user.id,
        post_id=post_id
    )
    db.session.add(comment)
    db.session.commit()
    
    flash('Your comment has been added!')
    return redirect(url_for('post', post_id=post_id))


@app.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != current_user.id:
        flash('You can only edit your own comments!')
        return redirect(url_for('post', post_id=comment.post_id))
    
    if request.method == 'POST':
        if not handle_content_validation('comment', request.form):
            return redirect(url_for('edit_comment', comment_id=comment_id))
        
        content = request.form.get('content')
        
        if comment.content != content:
            comment.content = content
            handle_edit_timestamps(comment)
            db.session.commit()
            flash('Your comment has been updated!')
        else:
            flash('No changes were made to your comment.')
            
        return redirect(url_for('post', post_id=comment.post_id))
    
    return render_template('edit_comment.html', comment=comment)


@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != current_user.id:
        flash('You can only delete your own comments!')
        return redirect(url_for('post', post_id=comment.post_id))
    
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    
    flash('Your comment has been deleted!')
    return redirect(url_for('post', post_id=post_id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)