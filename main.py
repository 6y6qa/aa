from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory, abort
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'halo_secret_here'

# --------------------------
#   UPLOAD DIRECTORIES
# --------------------------
UPLOAD_FOLDER_IMG     = 'static/uploads'
UPLOAD_FOLDER_PDF     = 'static/books'
UPLOAD_FOLDER_AUTHORS = 'static/authors'
UPLOAD_FOLDER_ADS     = 'static/reklam'
UPLOAD_FOLDER_LEKOLIN = 'static/lekolin'

ALLOWED_IMG = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_PDF = {'pdf'}

os.makedirs(UPLOAD_FOLDER_IMG,     exist_ok=True)
os.makedirs(UPLOAD_FOLDER_PDF,     exist_ok=True)
os.makedirs(UPLOAD_FOLDER_AUTHORS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_ADS,     exist_ok=True)
os.makedirs(UPLOAD_FOLDER_LEKOLIN, exist_ok=True)

# --------------------------
#   CATEGORIES & LANGUAGES
# --------------------------
CATEGORIES = [
    'رۆمان','چیرۆك','مێژوویی','ئایینی','كۆمەڵایەتی','شیعر',
    'فەلسەفی','دەروونزانی','منداڵان','زمان و ڕێزمان','قوتابی',
    'زانستی','پزیشکی','ناوداران','بادینی','تەکنەلۆجیا','فەرهەنگ',
    'سیاسی','وەرزش','هونەری'
]

LANGUAGES = ['کوردی', 'عەرەبی', 'ئینگلیزی', 'فارسی', 'تورکی']

POEM_CATEGORIES = [
    'کلاسیکی', 'نوێ', 'عاشقانە', 'نیشتیمانی', 'دینی', 'فەلسەفی'
]

WORD_CATEGORIES = [
    'ناو', 'کردار', 'هاوەڵناو', 'هاوەڵکردار', 'کاتژمێر', 'ئامراز', 'دەق'
]

# --------------------------
#   DATABASE INIT
# --------------------------
def init_db():
    with sqlite3.connect("books.db") as conn:

        # Books
        conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image TEXT,
            pdf TEXT,
            category TEXT,
            language TEXT,
            download_link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Authors
        conn.execute("""
        CREATE TABLE IF NOT EXISTS nusar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image TEXT,
            zhyannama TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Book Info
        conn.execute("""
        CREATE TABLE IF NOT EXISTS book_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            pages INTEGER,
            publisher TEXT,
            year INTEGER,
            isbn TEXT,
            description TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
        """)

        # Ads
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image TEXT NOT NULL,
            link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Research / لێکۆڵینەوە
        conn.execute("""
        CREATE TABLE IF NOT EXISTS lekolin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            content TEXT,
            image TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Poetry / هۆنراوە
        conn.execute("""
        CREATE TABLE IF NOT EXISTS honraw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            content TEXT NOT NULL,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Dictionary / فەرهەنگ
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ferheng (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            transliteration TEXT,
            definition TEXT NOT NULL,
            example TEXT,
            category TEXT,
            language_origin TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()

init_db()

# --------------------------
#   ADMIN CREDENTIALS
# --------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

# ==========================
#   HOME PAGE
# ==========================
@app.route('/')
def index():
    query    = request.args.get('q', '')
    category = request.args.get('category', '')
    language = request.args.get('language', '')

    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        sql    = "SELECT * FROM books WHERE 1=1"
        params = []

        if query:
            sql += " AND title LIKE ?"
            params.append(f'%{query}%')
        if category:
            sql += " AND category = ?"
            params.append(category)
        if language:
            sql += " AND language = ?"
            params.append(language)

        sql += " ORDER BY created_at DESC"
        books = conn.execute(sql, params).fetchall()
        ads   = conn.execute("SELECT * FROM ads ORDER BY created_at DESC LIMIT 3").fetchall()

    return render_template("index.html",
                           books=books,
                           ads=ads,
                           query=query,
                           categories=CATEGORIES,
                           languages=LANGUAGES,
                           selected_category=category,
                           selected_language=language)

# ==========================
#   AUTHORS PAGE
# ==========================
@app.route('/nusaran')
def nusar():
    query = request.args.get('q', '')
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        sql    = "SELECT * FROM nusar WHERE 1=1"
        params = []
        if query:
            sql += " AND title LIKE ?"
            params.append(f'%{query}%')
        sql += " ORDER BY created_at DESC"
        authors = conn.execute(sql, params).fetchall()

    return render_template("nusaran.html", books=authors, query=query)

# ==========================
#   BOOK DETAIL
# ==========================
@app.route('/book/<int:book_id>')
def book_detail(book_id):
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        info = None
        if book:
            info = conn.execute("SELECT * FROM book_info WHERE book_id = ?", (book_id,)).fetchone()

    if not book:
        flash('کتێب نەدۆزرایەوە', 'danger')
        return redirect(url_for('index'))

    return render_template('book_detail.html', book=book, info=info)

# ==========================
#   READ PDF (IFRAME)
# ==========================
@app.route('/read/<int:book_id>')
def read_book(book_id):
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if not book:
        abort(404, description="کتێب نەدۆزرایەوە")

    pdf_path = os.path.join(UPLOAD_FOLDER_PDF, book["pdf"])
    if not os.path.isfile(pdf_path):
        abort(404, description="PDF نەدۆزرایەوە")

    return render_template("read_book.html", book=book)

@app.route("/pdf/<filename>")
def serve_pdf(filename):
    if not filename.endswith(".pdf"):
        abort(403)
    return send_from_directory(UPLOAD_FOLDER_PDF, filename, as_attachment=False)

# ==========================
#   DOWNLOAD PDF (ADMIN)
# ==========================
@app.route('/download/<int:book_id>')
def download_book(book_id):
    if not session.get("logged_in"):
        flash("تەنها بەڕێوەبەر دەتوانێ دابەزاندن بکات", "warning")
        return redirect(url_for('login'))

    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if not book:
        flash("کتێب بوونی نییە", "danger")
        return redirect(url_for('index'))

    if book['pdf']:
        pdf_path = os.path.join(UPLOAD_FOLDER_PDF, book["pdf"])
        return send_file(pdf_path, as_attachment=True, download_name=f"{book['title']}.pdf")
    else:
        flash("PDF فایل نەدۆزرایەوە", "warning")
        return redirect(url_for('book_detail', book_id=book_id))

# ==========================
#   LOGIN / LOGOUT
# ==========================
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            flash("بەخێربێیت بەڕێوەبەر!", "success")
            return redirect(url_for("admin_panel"))
        else:
            flash("ناوی بەکارهێنەر یان وشەی نهێنی هەڵەیە!", "danger")

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    flash("بە سەرکەوتوویی چوویتە دەرەوە", "info")
    return redirect(url_for('index'))

# ==========================
#   ADMIN PANEL
# ==========================
@app.route('/admin')
def admin_panel():
    if not session.get("logged_in"):
        flash("دەستگەیشتن تەنها بۆ بەڕێوەبەرە", "warning")
        return redirect(url_for("login"))

    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        total_books   = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        total_authors = conn.execute("SELECT COUNT(*) FROM nusar").fetchone()[0]
        total_lekolin = conn.execute("SELECT COUNT(*) FROM lekolin").fetchone()[0]
        total_poems   = conn.execute("SELECT COUNT(*) FROM honraw").fetchone()[0]
        total_words   = conn.execute("SELECT COUNT(*) FROM ferheng").fetchone()[0]
        books         = conn.execute("SELECT * FROM books ORDER BY created_at DESC").fetchall()
        ads           = conn.execute("SELECT * FROM ads ORDER BY created_at DESC").fetchall()

    return render_template('admin_panel.html',
                           total_books=total_books,
                           total_authors=total_authors,
                           total_lekolin=total_lekolin,
                           total_poems=total_poems,
                           total_words=total_words,
                           books=books,
                           ads=ads,
                           categories=CATEGORIES,
                           languages=LANGUAGES,
                           poem_categories=POEM_CATEGORIES,
                           word_categories=WORD_CATEGORIES)

# ==========================
#   ADD BOOK
# ==========================
@app.route('/add_book', methods=["POST"])
def add_book():
    if not session.get("logged_in"):
        flash("دەستگەیشتن تەنها بۆ بەڕێوەبەرە", "warning")
        return redirect(url_for("login"))

    title         = request.form.get("title", "").strip()
    category      = request.form.get("category", "").strip()
    language      = request.form.get("language", "").strip()
    download_link = request.form.get("download_link", "").strip()
    image         = request.files.get("image")
    pdf           = request.files.get("pdf")

    if not title or not category or not language:
        flash("هەموو خانە پێویستەکان پڕبکەرەوە", "danger")
        return redirect(url_for("admin_panel"))

    img_name = None
    if image and image.filename:
        ext = image.filename.split('.')[-1].lower()
        if ext in ALLOWED_IMG:
            img_name = secure_filename(image.filename)
            image.save(os.path.join(UPLOAD_FOLDER_IMG, img_name))
        else:
            flash("جۆری وێنە پەسەند نەکراوە", "danger")
            return redirect(url_for("admin_panel"))

    pdf_name = None
    if pdf and pdf.filename:
        ext = pdf.filename.split('.')[-1].lower()
        if ext in ALLOWED_PDF:
            pdf_name = secure_filename(pdf.filename)
            pdf.save(os.path.join(UPLOAD_FOLDER_PDF, pdf_name))
        else:
            flash("تەنها فایلی PDF پەسەند کراوە", "danger")
            return redirect(url_for("admin_panel"))

    try:
        with sqlite3.connect("books.db") as conn:
            conn.execute("""
            INSERT INTO books (title, image, pdf, category, language, download_link)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (title, img_name, pdf_name, category, language, download_link))
            conn.commit()
        flash("کتێب بە سەرکەوتوویی زیادکرا!", "success")
    except Exception as e:
        flash(f"هەڵەیەک ڕوویدا: {str(e)}", "danger")

    return redirect(url_for('admin_panel'))

# ==========================
#   ADD AUTHOR
# ==========================
@app.route('/add_author', methods=["POST"])
def add_author():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    author_name  = request.form.get("author_name")
    author_bio   = request.form.get("author_bio", "")
    author_image = request.files.get("author_image")

    if not author_name:
        flash("ناوی نووسەر پێویستە", "danger")
        return redirect(url_for("admin_panel"))

    img_name = None
    if author_image and author_image.filename:
        ext = author_image.filename.split('.')[-1].lower()
        if ext in ALLOWED_IMG:
            img_name = secure_filename(author_image.filename)
            author_image.save(os.path.join(UPLOAD_FOLDER_AUTHORS, img_name))

    with sqlite3.connect("books.db") as conn:
        conn.execute("""
        INSERT INTO nusar (title, image, zhyannama) VALUES (?, ?, ?)
        """, (author_name, img_name, author_bio))
        conn.commit()

    flash("نووسەر بە سەرکەوتوویی زیادکرا!", "success")
    return redirect(url_for('admin_panel'))

# ==========================
#   ADD BOOK INFO
# ==========================
@app.route('/add_book_info', methods=["POST"])
def add_book_info():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    book_id     = request.form.get("book_id")
    pages       = request.form.get("pages")
    publisher   = request.form.get("publisher", "")
    year        = request.form.get("year")
    isbn        = request.form.get("isbn", "")
    description = request.form.get("description", "")

    if not book_id:
        flash("کتێبێک هەڵبژێرە", "danger")
        return redirect(url_for("admin_panel"))

    with sqlite3.connect("books.db") as conn:
        existing = conn.execute("SELECT * FROM book_info WHERE book_id = ?", (book_id,)).fetchone()
        if existing:
            conn.execute("""
            UPDATE book_info SET pages=?, publisher=?, year=?, isbn=?, description=?
            WHERE book_id=?
            """, (pages, publisher, year, isbn, description, book_id))
        else:
            conn.execute("""
            INSERT INTO book_info (book_id, pages, publisher, year, isbn, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (book_id, pages, publisher, year, isbn, description))
        conn.commit()

    flash("زانیاری کتێب بە سەرکەوتوویی زیادکرا!", "success")
    return redirect(url_for('admin_panel'))

# ==========================
#   UPLOAD AD
# ==========================
@app.route('/upload_ad', methods=["POST"])
def upload_ad():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    ad_image = request.files.get("ad_image")
    ad_link  = request.form.get("ad_link", "")

    if not ad_image or not ad_image.filename:
        flash("وێنەی ڕێکلام پێویستە", "danger")
        return redirect(url_for("admin_panel"))

    ext = ad_image.filename.split('.')[-1].lower()
    if ext in ALLOWED_IMG or ext == 'gif':
        img_name = secure_filename(ad_image.filename)
        ad_image.save(os.path.join(UPLOAD_FOLDER_ADS, img_name))
    else:
        flash("جۆری وێنە پەسەند نەکراوە", "danger")
        return redirect(url_for("admin_panel"))

    with sqlite3.connect("books.db") as conn:
        conn.execute("INSERT INTO ads (image, link) VALUES (?, ?)", (img_name, ad_link))
        conn.commit()

    flash("ڕێکلام بە سەرکەوتوویی زیادکرا!", "success")
    return redirect(url_for('admin_panel'))

# ==========================
#   DELETE BOOK
# ==========================
@app.route('/delete_book/<int:book_id>')
def delete_book(book_id):
    if not session.get("logged_in"):
        flash("تەنها بەڕێوەبەر دەتوانێ", "warning")
        return redirect(url_for("login"))

    with sqlite3.connect("books.db") as conn:
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if book:
            if book[2]:
                path = os.path.join(UPLOAD_FOLDER_IMG, book[2])
                if os.path.exists(path): os.remove(path)
            if book[3]:
                path = os.path.join(UPLOAD_FOLDER_PDF, book[3])
                if os.path.exists(path): os.remove(path)
            conn.execute("DELETE FROM book_info WHERE book_id = ?", (book_id,))
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
            flash("کتێب بە سەرکەوتوویی سڕایەوە", "success")
        else:
            flash("کتێب نەدۆزرایەوە", "danger")

    return redirect(url_for('admin_panel'))

# ==========================
#   DELETE AD
# ==========================
@app.route('/delete_ad/<int:ad_id>')
def delete_ad(ad_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    with sqlite3.connect("books.db") as conn:
        ad = conn.execute("SELECT * FROM ads WHERE id = ?", (ad_id,)).fetchone()
        if ad:
            if ad[1]:
                path = os.path.join(UPLOAD_FOLDER_ADS, ad[1])
                if os.path.exists(path): os.remove(path)
            conn.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
            conn.commit()
            flash("ڕێکلام سڕایەوە", "success")

    return redirect(url_for('admin_panel'))

# ==========================
#   DELETE AUTHOR
# ==========================
@app.route('/delete_author/<int:author_id>')
def delete_author(author_id):
    if not session.get("logged_in"):
        flash("تەنها بەڕێوەبەر دەتوانێ", "warning")
        return redirect(url_for("login"))

    with sqlite3.connect("books.db") as conn:
        author = conn.execute("SELECT * FROM nusar WHERE id = ?", (author_id,)).fetchone()
        if author:
            if author[2]:
                path = os.path.join(UPLOAD_FOLDER_AUTHORS, author[2])
                if os.path.exists(path): os.remove(path)
            conn.execute("DELETE FROM nusar WHERE id = ?", (author_id,))
            conn.commit()
            flash("نووسەر بە سەرکەوتوویی سڕایەوە", "success")
        else:
            flash("نووسەر نەدۆزرایەوە", "danger")

    return redirect(url_for('nusar'))

# ==========================
#   AUTHOR DETAIL
# ==========================
@app.route('/author/<int:author_id>')
def author_detail(author_id):
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        author = conn.execute("SELECT * FROM nusar WHERE id = ?", (author_id,)).fetchone()

    if not author:
        flash('نووسەر نەدۆزرایەوە', 'danger')
        return redirect(url_for('nusar'))

    return render_template('author_detail.html', author=author)

# ==========================================
#   LEKOLIN — لێکۆڵینەوە
# ==========================================
@app.route('/lekolin')
def lekolin():
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        adabi  = conn.execute(
            "SELECT * FROM lekolin WHERE category='ئەدەبی'  ORDER BY created_at DESC"
        ).fetchall()
        honari = conn.execute(
            "SELECT * FROM lekolin WHERE category='هونەری' ORDER BY created_at DESC"
        ).fetchall()
        zansti = conn.execute(
            "SELECT * FROM lekolin WHERE category='زانستی' ORDER BY created_at DESC"
        ).fetchall()

    return render_template("lekolin.html",
                           adabi_articles=adabi,
                           honari_articles=honari,
                           zansti_articles=zansti)


@app.route('/lekolin/<int:article_id>')
def lekolin_detail(article_id):
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        article = conn.execute("SELECT * FROM lekolin WHERE id = ?", (article_id,)).fetchone()

    if not article:
        flash("توێژینەوەکە نەدۆزرایەوە", "danger")
        return redirect(url_for('lekolin'))

    return render_template("lekolin_detail.html", article=article)


@app.route('/add_lekolin', methods=["POST"])
def add_lekolin():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    title    = request.form.get("lekolin_title", "").strip()
    summary  = request.form.get("lekolin_summary", "").strip()
    content  = request.form.get("lekolin_content", "").strip()
    category = request.form.get("lekolin_category", "").strip()
    image    = request.files.get("lekolin_image")

    if not title or not category:
        flash("ناو و پۆل پێویستن", "danger")
        return redirect(url_for("admin_panel"))

    img_name = None
    if image and image.filename:
        ext = image.filename.split('.')[-1].lower()
        if ext in ALLOWED_IMG:
            img_name = secure_filename(image.filename)
            image.save(os.path.join(UPLOAD_FOLDER_LEKOLIN, img_name))

    with sqlite3.connect("books.db") as conn:
        conn.execute(
            "INSERT INTO lekolin (title, summary, content, image, category) VALUES (?,?,?,?,?)",
            (title, summary, content, img_name, category)
        )
        conn.commit()

    flash("توێژینەوە بە سەرکەوتوویی زیادکرا!", "success")
    return redirect(url_for('admin_panel'))


@app.route('/delete_lekolin/<int:article_id>')
def delete_lekolin(article_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    with sqlite3.connect("books.db") as conn:
        article = conn.execute("SELECT * FROM lekolin WHERE id = ?", (article_id,)).fetchone()
        if article:
            if article[4]:  # image column index
                path = os.path.join(UPLOAD_FOLDER_LEKOLIN, article[4])
                if os.path.exists(path): os.remove(path)
            conn.execute("DELETE FROM lekolin WHERE id = ?", (article_id,))
            conn.commit()
            flash("توێژینەوە سڕایەوە", "success")
        else:
            flash("توێژینەوە نەدۆزرایەوە", "danger")

    return redirect(url_for('lekolin'))

# ==========================================
#   HONRAW — هۆنراوە
# ==========================================
@app.route('/honraw')
def honraw():
    query = request.args.get('q', '')
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        sql    = "SELECT * FROM honraw WHERE 1=1"
        params = []
        if query:
            sql += " AND (title LIKE ? OR author LIKE ? OR content LIKE ?)"
            params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
        sql += " ORDER BY created_at DESC"
        poems = conn.execute(sql, params).fetchall()

    return render_template("honraw.html", poems=poems, query=query)


@app.route('/honraw/<int:poem_id>')
def poem_detail(poem_id):
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        poem = conn.execute("SELECT * FROM honraw WHERE id = ?", (poem_id,)).fetchone()

    if not poem:
        flash("هۆنراوە نەدۆزرایەوە", "danger")
        return redirect(url_for('honraw'))

    return render_template("poem_detail.html", poem=poem)


@app.route('/add_poem', methods=["POST"])
def add_poem():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    title    = request.form.get("poem_title", "").strip()
    author   = request.form.get("poem_author", "").strip()
    content  = request.form.get("poem_content", "").strip()
    category = request.form.get("poem_category", "").strip()

    if not title or not content:
        flash("ناو و دەق پێویستن", "danger")
        return redirect(url_for("admin_panel"))

    with sqlite3.connect("books.db") as conn:
        conn.execute(
            "INSERT INTO honraw (title, author, content, category) VALUES (?,?,?,?)",
            (title, author, content, category)
        )
        conn.commit()

    flash("هۆنراوە بە سەرکەوتوویی زیادکرا!", "success")
    return redirect(url_for('admin_panel'))


@app.route('/delete_poem/<int:poem_id>')
def delete_poem(poem_id):
    if not session.get("logged_in"):
        flash("تەنها بەڕێوەبەر دەتوانێ", "warning")
        return redirect(url_for("login"))

    with sqlite3.connect("books.db") as conn:
        conn.execute("DELETE FROM honraw WHERE id = ?", (poem_id,))
        conn.commit()
        flash("هۆنراوە سڕایەوە", "success")

    return redirect(url_for('honraw'))

# ==========================================
#   FERHENG — فەرهەنگ
# ==========================================
@app.route('/ferheng')
def ferheng():
    query = request.args.get('q', '')
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        sql    = "SELECT * FROM ferheng WHERE 1=1"
        params = []
        if query:
            sql += " AND (word LIKE ? OR definition LIKE ? OR example LIKE ?)"
            params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
        sql += " ORDER BY word ASC"
        words = conn.execute(sql, params).fetchall()

    return render_template("ferheng.html", words=words, query=query)


@app.route('/ferheng/<int:word_id>')
def word_detail(word_id):
    with sqlite3.connect("books.db") as conn:
        conn.row_factory = sqlite3.Row
        word = conn.execute("SELECT * FROM ferheng WHERE id = ?", (word_id,)).fetchone()

    if not word:
        flash("وشە نەدۆزرایەوە", "danger")
        return redirect(url_for('ferheng'))

    return render_template("word_detail.html", word=word)


@app.route('/add_word', methods=["POST"])
def add_word():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    word            = request.form.get("word", "").strip()
    transliteration = request.form.get("transliteration", "").strip()
    definition      = request.form.get("definition", "").strip()
    example         = request.form.get("example", "").strip()
    category        = request.form.get("word_category", "").strip()
    lang_origin     = request.form.get("language_origin", "").strip()

    if not word or not definition:
        flash("وشە و مانا پێویستن", "danger")
        return redirect(url_for("admin_panel"))

    with sqlite3.connect("books.db") as conn:
        conn.execute(
            """INSERT INTO ferheng
               (word, transliteration, definition, example, category, language_origin)
               VALUES (?,?,?,?,?,?)""",
            (word, transliteration, definition, example, category, lang_origin)
        )
        conn.commit()

    flash("وشە بە سەرکەوتوویی زیادکرا!", "success")
    return redirect(url_for('admin_panel'))


@app.route('/delete_word/<int:word_id>')
def delete_word(word_id):
    if not session.get("logged_in"):
        flash("تەنها بەڕێوەبەر دەتوانێ", "warning")
        return redirect(url_for("login"))

    with sqlite3.connect("books.db") as conn:
        conn.execute("DELETE FROM ferheng WHERE id = ?", (word_id,))
        conn.commit()
        flash("وشە سڕایەوە", "success")

    return redirect(url_for('ferheng'))

# --------------------------
#   RUN
# --------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)