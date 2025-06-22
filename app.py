from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = '1606'  # Needed for flash messages

# 🔐 Admin password (you can change this)
ADMIN_PASSWORD = "Hara1606"

# Create the database and table if not exist
def init_db():
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()

# 🏠 Home route
@app.route('/')
def home():
    return render_template('home.html')

# 📚 Book list with optional category filter
@app.route('/books')
def book_list():
    category = request.args.get('category')

    conn = sqlite3.connect('books.db')
    cursor = conn.cursor()

    if category:
        books = cursor.execute('SELECT * FROM books WHERE category = ?', (category,)).fetchall()
    else:
        books = cursor.execute('SELECT * FROM books').fetchall()

    categories = cursor.execute('SELECT DISTINCT category FROM books').fetchall()
    conn.close()

    categories = [cat[0] for cat in categories if cat[0]]

    return render_template('book_list.html', books=books, categories=categories, selected_category=category)

# ➕ Add new book
@app.route('/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        price = float(request.form['price'])
        category = request.form['category']

        conn = sqlite3.connect('books.db')
        conn.execute(
            'INSERT INTO books (title, author, price, category) VALUES (?, ?, ?, ?)',
            (title, author, price, category)
        )
        conn.commit()
        conn.close()

        flash("Book added successfully.", "success")
        return redirect('/books')

    return render_template('add_book.html')

# 📝 Edit existing book
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_book(id):
    conn = sqlite3.connect('books.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        password = request.form.get('password')
        if password != ADMIN_PASSWORD:
            flash("Incorrect admin password. Changes not saved.", "danger")
            return redirect(f'/edit/{id}')

        title = request.form['title']
        author = request.form['author']
        price = float(request.form['price'])
        category = request.form['category']

        cursor.execute('''
            UPDATE books
            SET title = ?, author = ?, price = ?, category = ?
            WHERE id = ?
        ''', (title, author, price, category, id))

        conn.commit()
        conn.close()
        flash("Book updated successfully.", "success")
        return redirect('/books')

    # GET: show form
    book = cursor.execute('SELECT * FROM books WHERE id = ?', (id,)).fetchone()
    categories = cursor.execute('SELECT DISTINCT category FROM books').fetchall()
    conn.close()

    categories = [cat[0] for cat in categories if cat[0]]

    return render_template('edit_book.html', book=book, categories=categories)

# 🗑️ Delete book (with admin password)
@app.route('/delete/<int:id>', methods=['POST'])
def delete_book(id):
    password = request.form.get('password')
    if password != ADMIN_PASSWORD:
        flash("Incorrect admin password. Book not deleted.", "danger")
        return redirect('/books')

    conn = sqlite3.connect('books.db')
    conn.execute('DELETE FROM books WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Book deleted successfully.", "success")
    return redirect('/books')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
