import sqlite3
import uuid
from flask import Flask, request, render_template, redirect, url_for, session, flash
from jinja2 import DictLoader

app = Flask(__name__)
app.secret_key = "psych_experiment_secret_key"
DATABASE = 'experiment_data.db'

# --- HARDCODED DATA ---
VIDEO_URL = "https://www.youtube.com/embed/aqz-KE-bpKQ"

QUESTIONS = [
    {"id": 1, "q": "The main character began the video alone in the opening scene.", "correct": "True"},
    {"id": 2, "q": "The environment shown in the video was primarily natural rather than urban.", "correct": "True"},
    {"id": 3, "q": "The main character interacted with at least one distinct object in the environment.", "correct": "True"},
    {"id": 4, "q": "The sequence of events in the video followed a strictly repetitive pattern.", "correct": "False"},
    {"id": 5, "q": "The emotional tone of the video shifted at least once during playback.", "correct": "True"},
    {"id": 6, "q": "The video contained elements that suggested cause-and-effect relationships between events.", "correct": "True"},
    {"id": 7, "q": "The main character showed no observable change in behavior throughout the video.", "correct": "False"},
    {"id": 8, "q": "The background environment remained visually consistent throughout the entire video.", "correct": "False"},
    {"id": 9, "q": "There were multiple distinct visual events that required attention to notice.", "correct": "True"},
    {"id": 10, "q": "The video contained at least one element that could be interpreted as intentional action by the character.", "correct": "True"},
    {"id": 11, "q": "The overall structure of the video resembled a simple loop rather than a progression of events.", "correct": "False"},
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

# --- HTML TEMPLATES (UNCHANGED) ---
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
        setInterval(updateTable, 3000);
    </script>
{% endblock %}
"""

ADMIN_TABLE_ROWS_HTML = """
{% for p in participants %}
<tr>
    <td>{{ p[1] }}</td><td>{{ p[2] }}</td><td>{{ p[3] }}</td>
    <td>{{ p[4] }}</td><td>{{ p[5] }}</td><td>{{ p[6] }}</td>
    <td>{{ p[7] }}/22</td><td>{{ 'Done' if p[8] else 'In Progress' }}</td>
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
    <form method="POST">
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
        let seconds = 15;
        const timer = document.getElementById('timer');
        const countdown = setInterval(() => {
            seconds--;
            timer.textContent = seconds;
            if (seconds <= 0) {
                clearInterval(countdown);
                document.querySelector('form').submit();
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
    <p>Your final score is: <strong>{{ score }} / 22</strong></p>
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

@app.route('/exp/<token>/q/<int:q_idx>', methods=['GET', 'POST'])
def page_question(token, q_idx):
    if q_idx >= len(QUESTIONS):
        return redirect(url_for('page_final', token=token))

    if request.method == 'POST':
        answer = request.form.get('answer')

        if answer == QUESTIONS[q_idx]['correct']:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("UPDATE participants SET score = score + 2 WHERE id=?", (token,))

        return redirect(url_for('page_question', token=token, q_idx=q_idx + 1))

    return render_template('question',
                           page_num=q_idx + 4,
                           question=QUESTIONS[q_idx],
                           time_limit=False)

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
