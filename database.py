import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'secureshop.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Read and execute schema
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        cursor.executescript(f.read())

    # Populate initial sample data
    # Note: Storing plain passwords (Vulnerability 4: Authentication/Session weakness)
    cursor.execute("""
        INSERT INTO users (username, email, password, role, full_name, address)
        VALUES 
        ('admin', 'admin@secureshop.local', 'admin123', 'admin', 'System Administrator', '100 Security Way, Cyber City'),
        ('alice', 'alice@secureshop.local', 'password123', 'user', 'Alice Johnson', '12 Bluebird Lane, Metropolis'),
        ('bob', 'bob@secureshop.local', 'bobpass456', 'user', 'Bob Smith', '45 Elm Street, Gotham')
    """)

    sample_products = [
        ('Cyber Shield Firewall Appliance', 'Enterprise physical firewall unit with low latency monitoring.', 499.99, 'Hardware', '/static/images/firewall.svg', 15),
        ('Security Tokens - 5 Pack', 'Hardware 2FA authentication dongles for enterprise access control.', 75.50, 'Hardware', '/static/images/tokens.svg', 40),
        ('Encrypted Flash Drive 128GB', 'AES-256 hardware encrypted USB key with keypad input.', 89.00, 'Storage', '/static/images/usb.svg', 25),
        ('Wireless Penetration Audit Card', 'Dual-band long range Wi-Fi packet analyzer module.', 120.00, 'Tools', '/static/images/wifi.svg', 10),
        ('Application Security Audit Guidebook', 'Comprehensive guide covering OWASP Top 10 web vulnerabilities.', 39.99, 'Books', '/static/images/book1.svg', 50),
        ('Defensive Coding Best Practices', 'Step-by-step developer manual for secure software lifecycle.', 29.95, 'Books', '/static/images/book2.svg', 30)
    ]

    cursor.executemany("""
        INSERT INTO products (name, description, price, category, image_url, stock)
        VALUES (?, ?, ?, ?, ?, ?)
    """, sample_products)

    # Initial order for Alice
    cursor.execute("""
        INSERT INTO orders (user_id, total_amount, status, shipping_address)
        VALUES (2, 164.50, 'Completed', '12 Bluebird Lane, Metropolis')
    """)
    order_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO order_items (order_id, product_id, price, quantity)
        VALUES (?, 2, 75.50, 1), (?, 3, 89.00, 1)
    """, (order_id, order_id))

    conn.commit()
    conn.close()
    print("Database initialized successfully with test accounts and products.")

if __name__ == '__main__':
    init_db()
