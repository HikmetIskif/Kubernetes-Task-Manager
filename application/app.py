from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
import os, base64, hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://${{ secrets.DB_USERNAME }}:${{ secrets.DB_PASSWORD }}@postgres-srv/${{ secrets.DB_NAME }}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database models
class UserInfo(db.Model):
    __tablename__ = 'user_info'
    user_number = db.Column(db.String(30), primary_key=True)
    username = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(64), nullable=False)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_number = db.Column(db.String(30), db.ForeignKey('user_info.user_number'), nullable=False)
    task_name = db.Column(db.String(100), nullable=False)
    task_description = db.Column(db.String(100), nullable=False)
    task_date = db.Column(db.Date, nullable=False)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_number = base64.b64encode(os.urandom(20)).decode('utf-8')

        existing_user = UserInfo.query.filter_by(username=username).first()
        if existing_user:
            return "Username already taken!"
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        new_user = UserInfo(username=username, password=hashed_password, user_number=user_number)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        user = UserInfo.query.filter_by(username=username, password=hashed_password).first()
        if user:
            session['user_number'] = user.user_number
            session['username'] = user.username
            return redirect(url_for('tasks'))
        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if 'user_number' in session:
        user_number = session['user_number']
        if request.method == 'POST':
            task_name = request.form['task_name']
            task_description = request.form['task_description']
            task_date = request.form['task_date']

            if len(task_name) > 100 or len(task_description) > 100:
                return "Task name and description must be 100 characters or less.", 400
            
            if Task.query.filter_by(user_number=session['user_number']).count() >= 100:
                return "Users can have a maximum of 100 tasks.", 400

            task_id = Task.query.count() + 1
            new_task = Task(id=task_id, user_number=user_number, task_name=task_name, task_description=task_description, task_date=task_date)
            db.session.add(new_task)
            db.session.commit()
            return redirect(url_for('tasks'))
        tasks = Task.query.filter_by(user_number=user_number).order_by(Task.task_date.asc()).all()
        return render_template('tasks.html', tasks=tasks)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_number', None)
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    task = Task.query.get(task_id)
    if task and 'user_number' in session and task.user_number == session['user_number']:
        db.session.delete(task)
        db.session.commit()

        max_id = Task.query.count() + 1
        if max_id != task_id:
            task2 = Task.query.get(max_id)
            task2.id = task_id
            db.session.commit()


    return redirect(url_for('tasks'))

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    task = Task.query.get(task_id)
    if task and 'user_number' in session and task.user_number == session['user_number']:
        if request.method == 'POST':
            task.task_name = request.form['task_name']
            task.task_description = request.form['task_description']
            task.task_date = request.form['task_date']
            db.session.commit()
            return redirect(url_for('tasks'))
        return render_template('edit_task.html', task=task)
    return redirect(url_for('tasks'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
