from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import os
from rq import Queue
from redis import Redis
# from tasks import process_file
import logging

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.secret_key = 'supersecretkey'  # Diperlukan untuk menggunakan flash messages

# Redis configuration
app.config['redis_url'] = 'redis://localhost:6379/0'
conn = Redis.from_url(app.config['redis_url'])

# Initialize RQ Queue
q = Queue(connection=conn)

ALLOWED_EXTENSIONS = {'xlsx'}

# Setup logging
logging.basicConfig(level=logging.INFO)

# dummy account
users = {
    "user1": generate_password_hash("password123"),
    "user2": generate_password_hash("mypassword")
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if 'username' not in request.form or 'password' not in request.form:
            flash('Form is incomplete', 'danger')
            return redirect(url_for('login'))

        username = request.form['username']
        password = request.form['password']

        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        task = q.enqueue(process_file, file.filename)
        logging.info(f"Task ID: {task.id}")
        return redirect(url_for('task_status', task_id=task.id))
    else:
        flash('Allowed file type is .xlsx')
        return redirect(request.url)

@app.route('/status/<task_id>')
def task_status(task_id):
    task = q.fetch_job(task_id)
    logging.info(f"Task status requested: {task_id}, state: {task.get_status()}")
    if task.get_status() == 'queued':
        response = {
            'state': task.get_status(),
            'current': 0,
            'total': 1,
            'status': 'Pending...',
            'result_url': None
        }
    elif task.get_status() == 'started':
        response = {
            'state': task.get_status(),
            'current': task.meta.get('current', 0),
            'total': task.meta.get('total', 1),
            'status': task.meta.get('status', ''),
            'result_url': None
        }
    elif task.get_status() == 'finished':
        response = {
            'state': task.get_status(),
            'current': 1,
            'total': 1,
            'status': 'Task completed!',
            'result_url': url_for('result', task_id=task_id)
        }
    else:
        response = {
            'state': task.get_status(),
            'current': 1,
            'total': 1,
            'status': str(task.exc_info),
            'result_url': None
        }
    logging.info(f"Task status response: {response}")
    return jsonify(response)

@app.route('/result/<task_id>')
def result(task_id):
    task = q.fetch_job(task_id)
    result_data = task.result
    return render_template('result.html', result=result_data)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
