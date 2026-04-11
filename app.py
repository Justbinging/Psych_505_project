import sqlite3
import uuid
from flask import Flask, request, render_template, redirect, url_for, session, flash
from jinja2 import DictLoader

app = Flask(__name__)
app.secret_key = "psych_experiment_secret_key"
DATABASE = 'experiment_data.db'

# --- HARDCODED DATA ---
VIDEO_URL = "https://www.youtube.com/embed/aqz-KE-bpKQ" # Example: Big Buck Bunny
QUESTIONS = [
    {"id": 1, "q": "What color was the main character?", "options": ["Gray", "Green", "Blue", "Pink"], "correct": "Gray"},
    {"id": 2, "q": "How many characters were in the first scene?", "options": ["1", "2", "3", "4"], "correct": "1"},
    {"id": 3, "q": "What was the setting of the video?", "options": ["Forest", "City", "Ocean", "Space"], "correct": "Forest"},
    {"id": 4, "q": "Did it rain in the video?", "options": ["Yes", "No"], "correct": "No"},
    {"id": 5, "q": "What was the tone of the music?", "options": ["Happy", "Scary", "Sad", "Fast"], "correct": "Happy"},
    {"id": 6, "q": "Was there a butterfly?", "options": ["Yes", "No"], "correct": "Yes"},
    {"id": 7, "q": "Did the character eat anything?", "options": ["Yes", "No"], "correct": "No"},
    {"id": 8, "q": "Was the video animated?", "options": ["Yes", "No"], "correct": "Yes"},
    {"id": 9, "q": "Were there birds?", "options": ["Yes", "No"], "correct": "Yes"},
    {"id": 10, "q": "What was the length of the video (approx)?", "options": ["1 min", "5 min", "10 min"], "correct": "5 min"},
    {"id": 11, "q": "Did the video have dialogue?", "options": ["Yes", "No"], "correct": "No"},
]

# --- DATABASE SETUP ---
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS participants (
            id TEXT PRIMARY KEY,
            pid TEXT,
            time_group TEXT,
            reward_group TEXT,
            age TEXT,
            major TEXT,
            ethnicity TEXT,
            score INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0
        )''')
    conn.close()

init_db()

# --- HTML TEMPLATES (Inline for single-file requirement) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Psych Experiment</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { padding: 50px; background-color: #f8f9fa; }
        .container { max-width: 800px; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .timer { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

ADMIN_HTML = """
{% extends "base" %}
{% block content %}
    <h2>Admin: Generate Experiment Link</h2>
    <form method="POST">
        <div class="mb-3">
            <label>Participant Number (PID):</label>
            <input type="text" name="pid" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>Time Group:</label>
            <select name="time_group" class="form-select">
                <option value="unlimited">Unlimited Time</option>
                <option value="limited">Limited Time (15s per question)</option>
            </select>
        </div>
        <div class="mb-3">
            <label>Reward Group:</label>
            <select name="reward_group" class="form-select">
                <option value="no reward">No Reward</option>
                <option value="reward">Reward</option>
            </select>
        </div>
        <button type="submit" class="btn btn-primary">Generate Link</button>
    </form>
    {% with messages = get_flashed_messages() %}
      {% for message in messages %}
        <div class="mt-4 alert alert-success">
            <strong>Link Generated:</strong> <br>
            <a href="{{ message }}">{{ message }}</a>
        </div>
      {% endfor %}
    {% endwith %}
    <hr>
    <h3>Results</h3>
    <table class="table">
        <thead>
            <tr><th>PID</th><th>Time</th><th>Reward</th><th>Age</th><th>Major</th><th>Ethnicity</th><th>Score</th><th>Status</th></tr>
        </thead>
        <tbody id="participant-table-body">
            {% include "admin_table_rows" %}
        </tbody>
    </table>
    <hr>
    <form action="{{ url_for('clear_data') }}" method="POST" onsubmit="return confirm('Are you sure you want to delete ALL participant data? This cannot be undone.');">
        <button type="submit" class="btn btn-danger">Clear All Data</button>
    </form>

    <script>
        function updateTable() {
            fetch("{{ url_for('admin_table_data') }}")
                .then(response => response.text())
                .then(html => {
                    document.getElementById('participant-table-body').innerHTML = html;
                });
        }
        setInterval(updateTable, 3000); // Update every 3 seconds
    </script>
{% endblock %}
"""

ADMIN_TABLE_ROWS_HTML = """
{% for p in participants %}
<tr>
    <td>{{ p[1] }}</td><td>{{ p[2] }}</td><td>{{ p[3] }}</td>
    <td>{{ p[4] }}</td><td>{{ p[5] }}</td><td>{{ p[6] }}</td>
    <td>{{ p[7] }}/11</td><td>{{ 'Done' if p[8] else 'In Progress' }}</td>
</tr>
{% endfor %}
"""

DEMOGRAPHICS_HTML = """
{% extends "base" %}
{% block content %}
    <h2>Page 1: Demographics</h2>
    <form method="POST">
        <div class="mb-3"><label>Age:</label><input type="number" name="age" class="form-control" required></div>
        <div class="mb-3"><label>Major:</label><input type="text" name="major" class="form-control" required></div>
        <div class="mb-3"><label>Ethnicity:</label><input type="text" name="ethnicity" class="form-control" required></div>
        <button type="submit" class="btn btn-primary">Next</button>
    </form>
{% endblock %}
"""

INSTRUCTIONS_HTML = """
{% extends "base" %}
{% block content %}
    <h2>Page 2: Instructions</h2>
    <p>In this experiment, you will watch a short video and answer a series of questions based on its details.</p>
    {% if reward == 'reward' %}
    <p>Completing this accurately qualifies you for a reward.</p>
    {% endif %}
    <a href="{{ next_url }}" class="btn btn-primary">Next</a>
{% endblock %}
"""

VIDEO_HTML = """
{% extends "base" %}
{% block content %}
    <h2>Page 3: Watch Video</h2>
    <div class="ratio ratio-16x9 mb-3">
        <iframe src="{{ video_url }}" allowfullscreen></iframe>
    </div>
    <a href="{{ next_url }}" class="btn btn-primary">Next</a>
{% endblock %}
"""

QUESTION_HTML = """
{% extends "base" %}
{% block content %}
    <h2>Page {{ page_num }}: Question</h2>
    <p class="lead">{{ question['q'] }}</p>
    {% if time_limit %}
    <p class="timer">Time remaining: <span id="timer">15</span> seconds</p>
    {% endif %}
    <form id="q-form" method="POST">
        {% for opt in question['options'] %}
        <div class="form-check">
            <input class="form-check-input" type="radio" name="answer" value="{{ opt }}" id="opt{{ loop.index }}">
            <label class="form-check-label" for="opt{{ loop.index }}">{{ opt }}</label>
        </div>
        {% endfor %}
        <button type="submit" class="btn btn-primary mt-3">Next</button>
    </form>

    <script>
        {% if time_limit %}
        var seconds = 15;
        var timerDisplay = document.getElementById('timer');
        var countdown = setInterval(function() {
            seconds--;
            timerDisplay.textContent = seconds;
            if (seconds <= 0) {
                clearInterval(countdown);
                document.getElementById('q-form').submit();
            }
        }, 1000);
        {% endif %}
    </script>
{% endblock %}
"""

FINAL_HTML = """
{% extends "base" %}
{% block content %}
    <h2>Page 15: Experiment Complete</h2>
    <p>Your final score is: <strong>{{ score }} / 11</strong></p>
    <form method="POST">
        <button type="submit" class="btn btn-success">Finish</button>
    </form>
{% endblock %}
"""

THANKS_HTML = """
{% extends "base" %}
{% block content %}
    <h2>Experiment Complete</h2>
    <p>Thank you for participating! Your data has been saved successfully.</p>
    <p>You may now close this window.</p>
{% endblock %}
"""

# --- JINJA SETUP ---
app.jinja_loader = DictLoader({
    "base": BASE_HTML,
    "admin": ADMIN_HTML,
    "admin_table_rows": ADMIN_TABLE_ROWS_HTML,
    "demographics": DEMOGRAPHICS_HTML,
    "instructions": INSTRUCTIONS_HTML,
    "video": VIDEO_HTML,
    "question": QUESTION_HTML,
    "final": FINAL_HTML,
    "thanks": THANKS_HTML
})

# --- ROUTES ---

@app.route('/admin', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        uid = str(uuid.uuid4())
        pid = request.form['pid']
        tg = request.form['time_group']
        rg = request.form['reward_group']
        
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("INSERT INTO participants (id, pid, time_group, reward_group) VALUES (?,?,?,?)",
                         (uid, pid, tg, rg))
        flash(url_for('start_experiment', token=uid, _external=True))
        return redirect(url_for('admin'))
    
    with sqlite3.connect(DATABASE) as conn:
        participants = conn.execute("SELECT * FROM participants").fetchall()
        
    return render_template('admin', participants=participants)

@app.route('/admin/table_data')
def admin_table_data():
    with sqlite3.connect(DATABASE) as conn:
        participants = conn.execute("SELECT * FROM participants").fetchall()
    return render_template('admin_table_rows', participants=participants)

@app.route('/admin/clear', methods=['POST'])
def clear_data():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM participants")
    return redirect(url_for('admin'))

@app.route('/exp/<token>/page1', methods=['GET', 'POST'])
def start_experiment(token):
    if request.method == 'POST':
        age = request.form['age']
        major = request.form['major']
        eth = request.form['ethnicity']
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("UPDATE participants SET age=?, major=?, ethnicity=? WHERE id=?", (age, major, eth, token))
        return redirect(url_for('page_instructions', token=token))
    return render_template('demographics')

@app.route('/exp/<token>/page2')
def page_instructions(token):
    with sqlite3.connect(DATABASE) as conn:
        res = conn.execute("SELECT reward_group FROM participants WHERE id=?", (token,)).fetchone()
    if not res: return "Invalid Token", 404
    return render_template('instructions', 
                                  reward=res[0], 
                                  next_url=url_for('page_video', token=token))

@app.route('/exp/<token>/page3')
def page_video(token):
    return render_template('video', 
                                  video_url=VIDEO_URL, 
                                  next_url=url_for('page_question', token=token, q_idx=0))

@app.route('/exp/<token>/q/<int:q_idx>', methods=['GET', 'POST'])
def page_question(token, q_idx):
    if q_idx >= len(QUESTIONS):
        return redirect(url_for('page_final', token=token))

    with sqlite3.connect(DATABASE) as conn:
        user = conn.execute("SELECT time_group FROM participants WHERE id=?", (token,)).fetchone()
    
    if request.method == 'POST':
        answer = request.form.get('answer')
        if answer == QUESTIONS[q_idx]['correct']:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("UPDATE participants SET score = score + 1 WHERE id=?", (token,))
        return redirect(url_for('page_question', token=token, q_idx=q_idx + 1))

    return render_template('question', 
                                  page_num=q_idx + 4, 
                                  question=QUESTIONS[q_idx], 
                                  time_limit=(user[0] == 'limited'))

@app.route('/exp/<token>/final', methods=['GET', 'POST'])
def page_final(token):
    with sqlite3.connect(DATABASE) as conn:
        res = conn.execute("SELECT score FROM participants WHERE id=?", (token,)).fetchone()
    
    if request.method == 'POST':
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("UPDATE participants SET completed = 1 WHERE id=?", (token,))
        return render_template('thanks')

    return render_template('final', score=res[0])

if __name__ == '__main__':
    app.run(debug=True)