import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'polling_db')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD, cursor_factory=RealDictCursor
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            question_text TEXT NOT NULL,
            pub_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS options (
            id SERIAL PRIMARY KEY,
            question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
            option_text TEXT NOT NULL,
            votes INTEGER DEFAULT 0
        )
    ''')
    cur.execute("SELECT COUNT(*) FROM questions")
    if cur.fetchone()['count'] == 0:
        cur.execute("INSERT INTO questions (question_text) VALUES (%s) RETURNING id", ('Warna favorit Anda?',))
        qid = cur.fetchone()['id']
        cur.execute("INSERT INTO options (question_id, option_text) VALUES (%s, %s), (%s, %s), (%s, %s)",
                    (qid, 'Merah', qid, 'Biru', qid, 'Hijau'))
        cur.execute("INSERT INTO questions (question_text) VALUES (%s) RETURNING id", ('Hewan favorit?',))
        qid2 = cur.fetchone()['id']
        cur.execute("INSERT INTO options (question_id, option_text) VALUES (%s, %s), (%s, %s)",
                    (qid2, 'Kucing', qid2, 'Anjing'))
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions ORDER BY pub_date DESC")
    questions = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', questions=questions)

@app.route('/vote/<int:question_id>', methods=['GET', 'POST'])
def vote(question_id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        option_id = request.form.get('option')
        if option_id:
            cur.execute("UPDATE options SET votes = votes + 1 WHERE id = %s", (option_id,))
            conn.commit()
            flash('Terima kasih telah memilih!', 'success')
        return redirect(url_for('result', question_id=question_id))
    cur.execute("SELECT * FROM questions WHERE id = %s", (question_id,))
    question = cur.fetchone()
    if not question:
        return "Pertanyaan tidak ditemukan", 404
    cur.execute("SELECT * FROM options WHERE question_id = %s ORDER BY id", (question_id,))
    options = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('vote.html', question=question, options=options)

@app.route('/result/<int:question_id>')
def result(question_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions WHERE id = %s", (question_id,))
    question = cur.fetchone()
    if not question:
        return "Pertanyaan tidak ditemukan", 404
    cur.execute("SELECT * FROM options WHERE question_id = %s ORDER BY votes DESC", (question_id,))
    options = cur.fetchall()
    total_votes = sum(opt['votes'] for opt in options)
    cur.close()
    conn.close()
    return render_template('result.html', question=question, options=options, total_votes=total_votes)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)