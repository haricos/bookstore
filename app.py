from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '1606'  # Needed for flash messages

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'books.db')


# Create the database and tables if not exist
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create books table
    c.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            image TEXT
        )
    ''')

    # Create admins table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    ''')

    # Insert default admin if not exists
    c.execute('SELECT * FROM admins WHERE username = ?', ('admin',))
    if not c.fetchone():
        hashed_pw = generate_password_hash('1234')
        c.execute('INSERT INTO admins (username, password_hash) VALUES (?, ?)', ('admin', hashed_pw))

    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/books')
def book_list():
    category = request.args.get('category')
    search = request.args.get('search')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = 'SELECT * FROM books WHERE 1=1'
    params = []

    if category:
        query += ' AND category = ?'
        params.append(category)

    if search:
        query += ' AND (title LIKE ? OR author LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    books = cursor.execute(query, params).fetchall()
    categories = cursor.execute('SELECT DISTINCT category FROM books').fetchall()
    conn.close()

    categories = [cat[0] for cat in categories if cat[0]]

    return render_template('book_list.html', books=books, categories=categories,
                           selected_category=category, search=search)

@app.route('/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        price = float(request.form['price'])
        category = request.form['category']
        image = None

        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename:
                image = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image)
                image_file.save(image_path)

        conn = sqlite3.connect(DB_PATH)
        conn.execute('INSERT INTO books (title, author, price, category, image) VALUES (?, ?, ?, ?, ?)',
                     (title, author, price, category, image))
        conn.commit()
        conn.close()

        flash('Book added successfully!', 'success')
        return redirect('/books')

    return render_template('add_book.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_book(id):
    if 'admin' not in session:
        flash("Please log in to edit books.", "warning")
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        price = float(request.form['price'])
        category = request.form['category']
        password = request.form['password']

        if password != ADMIN_PASSWORD:
            flash("Incorrect admin password.", "danger")
            return redirect(f'/edit/{id}')

        c.execute('UPDATE books SET title=?, author=?, price=?, category=? WHERE id=?',
                  (title, author, price, category, id))
        conn.commit()
        conn.close()
        flash("Book updated successfully!", "success")
        return redirect('/books')

    # 👉 GET: Fetch book and category list
    book = c.execute('SELECT * FROM books WHERE id=?', (id,)).fetchone()
    all_categories = c.execute('SELECT DISTINCT category FROM books').fetchall()
    conn.close()

    categories = [cat[0] for cat in all_categories if cat[0]]

    return render_template('edit_book.html', book=book, categories=categories)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_book(id):
    if 'admin' not in session:
        flash("Please log in to delete books.", "warning")
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    conn.execute('DELETE FROM books WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash("Book deleted.", "success")
    return redirect('/books')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        user = c.execute('SELECT password_hash FROM admins WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session['admin'] = True
            flash('You are now logged in.', 'success')
            return redirect('/books')
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash('You have been logged out.', 'info')
    return redirect('/login')

# Initialize DB even when deployed
init_db()

if __name__ == '__main__':
    app.run(debug=True)

