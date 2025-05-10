import os, json, csv, random
from datetime import datetime
from functools import wraps
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'dev-key'
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)
QUESTIONS_FILE = os.path.join(DATA_DIR, 'questions_clean.jsonl')
USERS_FILE = os.path.join(DATA_DIR, 'users.csv')
ANSWERS_FILE = os.path.join(DATA_DIR, 'answers.csv')
LABELS_FILE = os.path.join(DATA_DIR, 'question_labels.csv')

# Class labels
CLASS_LABELS = [
    "Spatial Configuration",
    "Lateral location (left / right / beside)",
    "Front–Back & Proximity",
    "Vertical position",
    "Motion and Trajectory",
    "Viewpoint and Visibility",
    "Causal and Motivational Reasoning",
    "Social Interaction and Relationships",
    "Physical and Environmental Context",
    "Counting"
]

# Create files if they don't exist
for file_path, headers in [
    (USERS_FILE, ['username', 'created_at']),
    (ANSWERS_FILE, ['username', 'question_id', 'selected_choice', 'correct', 'answered_at']),
    (LABELS_FILE, ['username', 'question_id', 'label', 'labeled_at'])
]:
    if not os.path.exists(file_path):
        with open(file_path, 'w', newline='') as f:
            csv.writer(f).writerow(headers)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters')
            return redirect(url_for('signup'))
        
        # Check for duplicates
        with open(USERS_FILE, 'r', newline='') as f:
            if username in [row[0] for row in csv.reader(f)][1:]:
                flash('Username already taken')
                return redirect(url_for('signup'))
        
        # Add user
        with open(USERS_FILE, 'a', newline='') as f:
            csv.writer(f).writerow([username, datetime.now().isoformat()])
        
        session['username'] = username
        return redirect(url_for('quiz'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        with open(USERS_FILE, 'r', newline='') as f:
            if username not in [row[0] for row in csv.reader(f)][1:]:
                flash('Username not found')
                return redirect(url_for('login'))
        
        session['username'] = username
        return redirect(url_for('quiz'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/import', methods=['GET', 'POST'])
@login_required
def import_questions():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        files = request.files.getlist('file')
        if not files or all(file.filename == '' for file in files):
            flash('No files selected')
            return redirect(request.url)
        
        imported = 0
        for file in files:
            if file.filename.endswith('.jsonl'):
                with open(QUESTIONS_FILE, 'a') as outfile:
                    for line in file.stream:
                        try:
                            question = json.loads(line.decode('utf-8'))
                            if all(k in question for k in ['video_id', 'question_id', 'question_text', 
                                                           'options', 'answer_choice', 'final_category']):
                                outfile.write(json.dumps(question) + '\n')
                                imported += 1
                        except json.JSONDecodeError:
                            pass
        
        flash(f'Imported {imported} questions')
        return redirect(url_for('quiz'))
    
    return render_template('import.html')

@app.route('/quiz')
@login_required
def quiz():
    # Get all questions and answered questions
    all_questions = []
    with open(QUESTIONS_FILE, 'r') as f:
        for line in f:
            try:
                all_questions.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    answered_ids = set()
    with open(ANSWERS_FILE, 'r', newline='') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row[0] == session['username']:
                answered_ids.add(row[1])
    
    # Filter unanswered questions
    unanswered = [q for q in all_questions if q['question_id'] not in answered_ids]
    
    if not unanswered:
        flash('No more questions to answer')
        return render_template('quiz.html', question=None)
    
    question = random.choice(unanswered)
    video_url = f"/static/videos/{question['video_id']}.mp4"
    
    # Get any existing label for this question by this user
    existing_label = None
    try:
        with open(LABELS_FILE, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if row[0] == session['username'] and row[1] == question['question_id']:
                    existing_label = row[2]
                    break
    except:
        pass
    
    return render_template('quiz.html', 
                          question=question, 
                          video_url=video_url, 
                          class_labels=CLASS_LABELS,
                          existing_label=existing_label)

@app.route('/submit', methods=['POST'])
@login_required
def submit_answer():
    question_id = request.form.get('question_id')
    selected_choice = request.form.get('selected_choice')
    class_label = request.form.get('class_label')
    
    # Find question
    question = None
    with open(QUESTIONS_FILE, 'r') as f:
        for line in f:
            try:
                q = json.loads(line)
                if q['question_id'] == question_id:
                    question = q
                    break
            except json.JSONDecodeError:
                continue
    
    if not question:
        flash('Question not found')
        return redirect(url_for('quiz'))
    
    # Save class label if provided
    if class_label:
        # Check if this question already has a label from this user
        existing_label = False
        existing_labels = []
        try:
            with open(LABELS_FILE, 'r', newline='') as f:
                reader = csv.reader(f)
                existing_labels = list(reader)
                for i, row in enumerate(existing_labels):
                    if i > 0 and row[0] == session['username'] and row[1] == question_id:
                        existing_label = True
                        existing_labels[i][2] = class_label  # Update label
                        existing_labels[i][3] = datetime.now().isoformat()  # Update timestamp
                        break
        except:
            pass
        
        if existing_label:
            # Write updated labels
            with open(LABELS_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(existing_labels)
        else:
            # Add new label
            with open(LABELS_FILE, 'a', newline='') as f:
                csv.writer(f).writerow([
                    session['username'],
                    question_id,
                    class_label,
                    datetime.now().isoformat()
                ])
    
    # Determine if answer is correct
    # Compare selected option with the correct answer
    is_correct = 1 if selected_choice == question['answer_choice'] else 0
    
    # Record answer
    with open(ANSWERS_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([
            session['username'],
            question_id,
            selected_choice,
            is_correct,
            datetime.now().isoformat()
        ])
    
    return redirect(url_for('result', correct=is_correct))

@app.route('/result')
@login_required
def result():
    correct = request.args.get('correct', '0')
    return render_template('result.html', correct=int(correct))

@app.route('/stats')
@login_required
def stats():
    # Load questions and categories
    questions = {}
    with open(QUESTIONS_FILE, 'r') as f:
        for line in f:
            try:
                q = json.loads(line)
                questions[q['question_id']] = q
            except json.JSONDecodeError:
                continue
    
    # Load answers
    user_stats = defaultdict(lambda: [0, 0])  # [correct, total]
    cat_stats = defaultdict(lambda: [0, 0])  # [correct, total]
    user_cat_stats = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # [correct, total]
    
    with open(ANSWERS_FILE, 'r', newline='') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            username, qid, _, correct = row[:4]
            
            # Update user stats
            user_stats[username][0] += int(correct)
            user_stats[username][1] += 1
            
            # Update category stats if question exists
            if qid in questions:
                category = questions[qid]['final_category']  # Use final_category instead of category
                cat_stats[category][0] += int(correct)
                cat_stats[category][1] += 1
                user_cat_stats[username][category][0] += int(correct)
                user_cat_stats[username][category][1] += 1
    
    # Load labels
    question_labels = defaultdict(list)  # question_id -> list of labels
    try:
        with open(LABELS_FILE, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 3:
                    question_labels[row[1]].append(row[2])
    except:
        pass
    
    # Count labels per class
    label_counts = defaultdict(int)
    for labels in question_labels.values():
        for label in labels:
            label_counts[label] += 1
    
    return render_template('stats.html', 
                          user_stats=dict(user_stats),
                          cat_stats=dict(cat_stats),
                          user_cat_stats=dict(user_cat_stats),
                          label_counts=dict(label_counts),
                          class_labels=CLASS_LABELS)

if __name__ == '__main__':
    app.run(debug=True)