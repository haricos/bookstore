from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from uuid import uuid4
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '1606'  # Change this later before real online deployment.

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'books.db')

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            description TEXT,
            image TEXT
        )
    """)

    # If the database was created before description existed, add it safely.
    c.execute("PRAGMA table_info(books)")
    columns = [column[1] for column in c.fetchall()]
    if "description" not in columns:
        c.execute("ALTER TABLE books ADD COLUMN description TEXT")

    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    c.execute("SELECT * FROM admins WHERE username = ?", ("admin",))
    if not c.fetchone():
        hashed_pw = generate_password_hash("1234")
        c.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ("admin", hashed_pw)
        )

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/books")
def book_list():
    category = request.args.get("category")
    search = request.args.get("search")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, title, author, price, category, description, image
        FROM books
        WHERE 1=1
    """
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR author LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY id DESC"

    books = cursor.execute(query, params).fetchall()
    categories = cursor.execute(
        "SELECT DISTINCT category FROM books WHERE category IS NOT NULL AND category != '' ORDER BY category"
    ).fetchall()
    conn.close()

    categories = [cat[0] for cat in categories]

    return render_template(
        "book_list.html",
        books=books,
        categories=categories,
        selected_category=category,
        search=search
    )


@app.route("/add", methods=["GET", "POST"])
def add_book():
    if "admin" not in session:
        flash("Please log in to add books.", "warning")
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        price = float(request.form["price"])
        category = request.form["category"]
        description = request.form.get("description", "")

        image = None
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = f"{uuid4().hex}_{secure_filename(image_file.filename)}"
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(image_path)
            image = filename

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO books (title, author, price, category, description, image)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, author, price, category, description, image)
        )
        conn.commit()
        conn.close()

        flash("Book added successfully!", "success")
        return redirect("/books")

    return render_template("add_book.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_book(id):
    if "admin" not in session:
        flash("Please log in to edit books.", "warning")
        return redirect("/login")

    conn = get_db_connection()
    c = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        price = float(request.form["price"])
        category = request.form["category"]
        description = request.form.get("description", "")

        image = None
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = f"{uuid4().hex}_{secure_filename(image_file.filename)}"
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(image_path)
            image = filename

        if image:
            c.execute(
                """
                UPDATE books
                SET title=?, author=?, price=?, category=?, description=?, image=?
                WHERE id=?
                """,
                (title, author, price, category, description, image, id)
            )
        else:
            c.execute(
                """
                UPDATE books
                SET title=?, author=?, price=?, category=?, description=?
                WHERE id=?
                """,
                (title, author, price, category, description, id)
            )

        conn.commit()
        conn.close()

        flash("Book updated successfully!", "success")
        return redirect("/books")

    book = c.execute(
        """
        SELECT id, title, author, price, category, description, image
        FROM books
        WHERE id=?
        """,
        (id,)
    ).fetchone()

    categories = c.execute(
        "SELECT DISTINCT category FROM books WHERE category IS NOT NULL AND category != '' ORDER BY category"
    ).fetchall()
    conn.close()

    if not book:
        flash("Book not found.", "danger")
        return redirect("/books")

    categories = [cat[0] for cat in categories]

    return render_template("edit_book.html", book=book, categories=categories)


@app.route("/delete/<int:id>", methods=["POST"])
def delete_book(id):
    if "admin" not in session:
        flash("Please log in to delete books.", "warning")
        return redirect("/login")

    conn = get_db_connection()
    conn.execute("DELETE FROM books WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Book deleted.", "success")
    return redirect("/books")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        c = conn.cursor()
        user = c.execute(
            "SELECT password_hash FROM admins WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session["admin"] = True
            flash("You are now logged in.", "success")
            return redirect("/books")

        flash("Invalid credentials.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("You have been logged out.", "info")
    return redirect("/login")


init_db()

if __name__ == "__main__":
    app.run(debug=True)

