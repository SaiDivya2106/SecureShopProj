from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from database import get_db_connection, init_db

app = Flask(__name__)

# Security Misconfiguration: Hardcoded weak secret key & Debug mode enabled
app.config['SECRET_KEY'] = 'secureshop_secret_123'
app.config['DEBUG'] = True

# Session Weakness: Cookie missing HttpOnly flag
app.config['SESSION_COOKIE_HTTPONLY'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Automatically ensure DB exists on startup
DB_FILE = os.path.join(os.path.dirname(__file__), 'secureshop.db')
if not os.path.exists(DB_FILE):
    init_db()

# --- Helper Functions ---
def get_cart_count():
    if 'user_id' not in session:
        return 0
    conn = get_db_connection()
    count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_id = ?", (session['user_id'],)).fetchone()[0]
    conn.close()
    return count if count else 0

# --- Public Routes ---
@app.route('/')
def index():
    conn = get_db_connection()
    category = request.args.get('category', '')
    if category:
        products = conn.execute("SELECT * FROM products WHERE category = ?", (category,)).fetchall()
    else:
        products = conn.execute("SELECT * FROM products").fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM products").fetchall()
    conn.close()
    return render_template('index.html', products=products, categories=categories, current_category=category, cart_count=get_cart_count())

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('index'))
    return render_template('product_detail.html', product=product, cart_count=get_cart_count())

# Vulnerability 2: SQL Injection in Search
@app.route('/search')
def search():
    query = request.args.get('q', '')
    conn = get_db_connection()
    products = []
    if query:
        # Intentionally vulnerable query concatenation for OWASP ZAP testing
        sql = f"SELECT * FROM products WHERE name LIKE '%{query}%' OR description LIKE '%{query}%' OR category LIKE '%{query}%'"
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            products = cursor.fetchall()
        except sqlite3.Error as e:
            # Verbose error exposure (Security Misconfiguration)
            flash(f"Database Error in query: {e}", "error")
    else:
        products = conn.execute("SELECT * FROM products").fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM products").fetchall()
    conn.close()
    return render_template('index.html', products=products, categories=categories, query=query, cart_count=get_cart_count())

# --- Auth Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        address = request.form.get('address', '').strip()

        # Vulnerability 4: Weak authentication/password validation
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template('register.html')

        conn = get_db_connection()
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash("Username already exists.", "error")
            conn.close()
            return render_template('register.html')

        # Vulnerability 4: Plaintext password storage
        conn.execute(
            "INSERT INTO users (username, email, password, role, full_name, address) VALUES (?, ?, ?, 'user', ?, ?)",
            (username, email, password, full_name, address)
        )
        conn.commit()
        conn.close()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html', cart_count=get_cart_count())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        conn = get_db_connection()
        # Vulnerability 4: Plaintext password comparison
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f"Welcome back, {user['username']}!", "success")
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials.", "error")

    return render_template('login.html', cart_count=get_cart_count())

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

# --- User & Order Routes ---
# Vulnerability 1: Broken Access Control / IDOR in Profile
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please log in to view your profile.", "error")
        return redirect(url_for('login'))

    # IDOR: Accepts an optional user_id parameter without verifying ownership or admin status
    target_id = request.args.get('id', session['user_id'])
    conn = get_db_connection()
    user = conn.execute("SELECT id, username, email, role, full_name, address FROM users WHERE id = ?", (target_id,)).fetchone()
    conn.close()

    if not user:
        flash("User profile not found.", "error")
        return redirect(url_for('index'))

    return render_template('profile.html', user=user, cart_count=get_cart_count())

@app.route('/profile/edit', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    full_name = request.form.get('full_name', '')
    address = request.form.get('address', '')
    email = request.form.get('email', '')

    conn = get_db_connection()
    conn.execute("UPDATE users SET full_name = ?, address = ?, email = ? WHERE id = ?",
                 (full_name, address, email, session['user_id']))
    conn.commit()
    conn.close()
    flash("Profile updated successfully!", "success")
    return redirect(url_for('profile'))

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash("Please log in to view cart.", "error")
        return redirect(url_for('login'))

    conn = get_db_connection()
    items = conn.execute("""
        SELECT c.id as cart_id, p.id as product_id, p.name, p.price, p.image_url, c.quantity, (p.price * c.quantity) as subtotal
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    """, (session['user_id'],)).fetchall()
    
    total = sum(item['subtotal'] for item in items)
    conn.close()
    return render_template('cart.html', items=items, total=total, cart_count=get_cart_count())

@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash("Please log in to add items to cart.", "error")
        return redirect(url_for('login'))

    quantity = int(request.form.get('quantity', 1))
    conn = get_db_connection()
    existing = conn.execute("SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?",
                             (session['user_id'], product_id)).fetchone()
    if existing:
        conn.execute("UPDATE cart SET quantity = quantity + ? WHERE id = ?", (quantity, existing['id']))
    else:
        conn.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
                     (session['user_id'], product_id, quantity))
    conn.commit()
    conn.close()
    flash("Item added to cart.", "success")
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM cart WHERE id = ? AND user_id = ?", (cart_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Item removed from cart.", "info")
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    shipping_address = request.form.get('shipping_address', 'Default Address')
    conn = get_db_connection()
    cart_items = conn.execute("""
        SELECT c.product_id, c.quantity, p.price
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    """, (session['user_id'],)).fetchall()

    if not cart_items:
        flash("Your cart is empty.", "error")
        conn.close()
        return redirect(url_for('view_cart'))

    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)

    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, total_amount, shipping_address) VALUES (?, ?, ?)",
                   (session['user_id'], total_amount, shipping_address))
    order_id = cursor.lastrowid

    for item in cart_items:
        cursor.execute("INSERT INTO order_items (order_id, product_id, price, quantity) VALUES (?, ?, ?, ?)",
                       (order_id, item['product_id'], item['price'], item['quantity']))

    cursor.execute("DELETE FROM cart WHERE user_id = ?", (session['user_id'],))
    conn.commit()
    conn.close()

    flash(f"Order #{order_id} placed successfully!", "success")
    return redirect(url_for('orders'))

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        flash("Please log in to view your orders.", "error")
        return redirect(url_for('login'))

    conn = get_db_connection()
    user_orders = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('orders.html', orders=user_orders, cart_count=get_cart_count())

# Vulnerability 1: IDOR on Order Detail
@app.route('/order/<int:order_id>')
def order_detail(order_id):
    if 'user_id' not in session:
        flash("Please log in.", "error")
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Intentionally missing check for user_id ownership match!
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "error")
        return redirect(url_for('orders'))

    items = conn.execute("""
        SELECT oi.*, p.name, p.image_url 
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()
    
    order_user = conn.execute("SELECT username, email FROM users WHERE id = ?", (order['user_id'],)).fetchone()
    conn.close()
    return render_template('order_detail.html', order=order, items=items, order_user=order_user, cart_count=get_cart_count())

# --- Admin Routes ---
# Vulnerability 1: Broken Access Control (Missing role check on admin endpoints)
@app.route('/admin')
def admin_dashboard():
    # Intentionally missing role check for lab scenario (or weak client side check)
    # A standard user can navigate directly to /admin
    conn = get_db_connection()
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    product_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    order_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    revenue = conn.execute("SELECT SUM(total_amount) FROM orders").fetchone()[0] or 0.0
    conn.close()
    return render_template('admin_dashboard.html', user_count=user_count, product_count=product_count, 
                           order_count=order_count, revenue=revenue, cart_count=get_cart_count())

@app.route('/admin/users')
def admin_users():
    # Broken Access Control: Any user can access user database list
    conn = get_db_connection()
    users = conn.execute("SELECT id, username, email, password, role, full_name FROM users").fetchall()
    conn.close()
    return render_template('admin_users.html', users=users, cart_count=get_cart_count())

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', 0))
        category = request.form.get('category')
        image_url = request.form.get('image_url')
        stock = int(request.form.get('stock', 10))

        conn.execute("INSERT INTO products (name, description, price, category, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)",
                     (name, description, price, category, image_url, stock))
        conn.commit()
        flash("Product added successfully!", "success")

    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template('admin_products.html', products=products, cart_count=get_cart_count())

@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash("Product deleted successfully.", "info")
    return redirect(url_for('admin_products'))

# Vulnerability 3: Diagnostic / Security Misconfiguration Endpoint Exposing Server Details
@app.route('/debug/info')
def debug_info():
    info = {
        "flask_version": "2.0.1",
        "debug_mode": app.config['DEBUG'],
        "secret_key": app.config['SECRET_KEY'],
        "database_path": DB_FILE,
        "environment_vars": dict(os.environ)
    }
    return jsonify(info)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting SecureShop application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)