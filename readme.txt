# Minimal Video QA Evaluation Tool

A minimalist Flask application for evaluating video questions.

## Setup

1. Create required directories:
```
mkdir -p data static/videos
```

2. Install Flask:
```
pip install flask
```

3. Run the application:
```
export FLASK_APP=app.py
flask run
```

## Features

- User authentication (signup/login)
- Import questions from JSONL files
- Answer video-based questions
- View statistics by user and category

## Data Files

- Questions are stored in `data/questions.jsonl`
- Users are stored in `data/users.csv`
- Answers are stored in `data/answers.csv`

## Video Files

Place your MP4 videos in the `static/videos` directory. The filename should match the `video_id` in your questions (e.g., `v001.mp4`).

## Sample Questions

Sample questions are provided in `sample_questions.jsonl`. Import them through the web interface after logging in.
