# SecureShop - Vulnerable E-Commerce Application Security Lab

SecureShop is a lightweight, local-only Python/Flask web application intentionally designed with controlled web application vulnerabilities. It serves as a practical target environment for Application Security (AppSec) learning, Red Team assessment, manual penetration testing, and **OWASP ZAP** automated vulnerability scanning.

> **IMPORTANT**: This application is built strictly for localhost security research and educational assignments. Do not deploy to public internet environments or target external production systems.

---

## Table of Contents
1. [Project Overview & Features](#project-overview--features)
2. [Project Structure](#project-structure)
3. [Installation & Setup](#installation--setup)
4. [Running the Application](#running-the-application)
5. [Local Access & Test Credentials](#local-access--test-credentials)
6. [Intentionally Included Vulnerabilities](#intentionally-included-vulnerabilities)
7. [Outdated Dependency Audit](#outdated-dependency-audit)
8. [Safe Manual Verification Steps](#safe-manual-verification-steps)
9. [Evidence & Screenshots to Collect](#evidence--screenshots-to-collect)

---

## Project Overview & Features
SecureShop provides a complete e-commerce experience:
- **Product Catalog & Search**: Browse hardware products by category or search by keyword.
- **Product Details & Cart**: Detailed item pages with quantity selector, shopping cart management, and checkout.
- **User Authentication**: User registration, login, session persistence, and logout.
- **User Dashboard & Order History**: Personal user profile and historical order receipts.
- **Admin Portal**: Executive dashboard displaying user stats, revenue metrics, product catalog management (Add/Delete), and user account directory.
- **Automated Database Initialization**: SQLite database (`secureshop.db`) is generated and seeded automatically on application launch.

---

## Project Structure
```text
secureshop/
│
├── app.py                # Main Flask web server, route definitions, and intentionally vulnerable handlers
├── database.py           # Database connection helpers and automatic seed data population script
├── schema.sql            # SQLite database schema DDL (users, products, cart, orders, order_items)
├── requirements.txt      # Python package dependencies (includes intentional outdated libraries)
├── README.md             # Complete lab setup, execution guide, and verification steps
├── SECURITY_NOTES.md     # Detailed vulnerability breakdown, risk impact, & mitigation strategies
│
├── templates/            # HTML templates using Jinja2 engine
│   ├── base.html             # Master layout template (navbar, flash messages, footer)
│   ├── index.html            # Catalog home page & search results
│   ├── product_detail.html   # Product details view & add to cart
│   ├── login.html            # User/Admin login page with test credentials
│   ├── register.html         # New account registration page
│   ├── cart.html             # Shopping cart view & checkout form
│   ├── profile.html          # User profile management (Vulnerable to IDOR)
│   ├── orders.html           # User order history listing
│   ├── order_detail.html     # Detailed receipt view (Vulnerable to IDOR)
│   ├── admin_dashboard.html  # Admin panel stats & diagnostics
│   ├── admin_users.html      # Admin user directory (Exposes plaintext credentials & BAC)
│   └── admin_products.html   # Admin inventory management (Add/Delete products)
│
└── static/               # Static assets
    ├── css/
    │   └── style.css         # Modern dark-mode custom stylesheet with glassmorphism UI
    └── js/
        └── main.js           # Client-side utility functions
```

---

## Installation & Setup

### Prerequisites
- Python 3.8+ installed on your system.

### Steps
1. Navigate to the project root directory:
   ```bash
   cd secureshop
   ```
2. (Recommended) Create and activate a virtual environment:
   - **On Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **On macOS/Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Application

Execute `app.py` directly using Python:
```bash
python app.py
```

Upon launch, `app.py` checks for `secureshop.db`. If not present, it invokes `database.py` to construct the tables from `schema.sql` and populate sample products, orders, and test accounts automatically.

---

## Local Access & Test Credentials

- **Local URL**: `http://127.0.0.1:5000`

### Pre-seeded Accounts
| Role | Username | Password | Purpose / Testing Use Case |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Full Administrative Access & Admin Dashboard |
| **User** | `alice` | `password123` | Regular customer account with existing sample order (#1) |
| **User** | `bob` | `bobpass456` | Secondary test user for multi-user IDOR testing |

---

## Intentionally Included Vulnerabilities

SecureShop contains **4 main controlled vulnerability categories** + **1 documented outdated dependency issue**:

1. **Broken Access Control (OWASP A01:2021)**
   - **IDOR on Profile**: Visiting `/profile?id=1` or `/profile?id=2` displays any user's profile details without ownership verification.
   - **IDOR on Order Receipts**: Visiting `/order/1` while logged in as `bob` displays Alice's order receipt.
   - **Missing Role Checks**: `/admin`, `/admin/users`, and `/admin/products` endpoints can be accessed by regular users or unauthenticated clients without role verification.

2. **SQL Injection (OWASP A03:2021)**
   - **Product Search Handler**: The `/search?q=` route directly concatenates user input into SQL string queries without parameter binding (`SELECT * FROM products WHERE name LIKE '%{query}%'`).

3. **Security Misconfiguration (OWASP A05:2021)**
   - `DEBUG = True` is enabled in `app.py`, rendering verbose tracebacks on errors.
   - Hardcoded weak `SECRET_KEY = 'secureshop_secret_123'`.
   - Exposed diagnostic debug route `/debug/info` returning environment details in JSON.

4. **Authentication / Session Weakness (OWASP A07:2021)**
   - Session cookies omit `HttpOnly` flag (`SESSION_COOKIE_HTTPONLY = False`), exposing session identifiers to client-side scripts.
   - User passwords are stored as unhashed plain text in the SQLite database.

5. **Outdated Dependency Security Risk (OWASP A06:2021)**
   - Detailed in the section below.

---

## Outdated Dependency Audit

| Metric | Details |
| :--- | :--- |
| **Dependency Name** | `Werkzeug` (and `Flask`) |
| **Installed Version** | `Werkzeug==2.0.1` / `Flask==2.0.1` |
| **Current Stable Version** | `Werkzeug 3.x` / `Flask 3.x` |
| **Security Concern** | **High/Medium Risk**: Parsing vulnerabilities, DoS via multipart payload parsing, potential HTTP header injection, and unauthorized session cookie parsing. |
| **Associated CVEs** | **CVE-2022-29361** (Information Disclosure in Werkzeug request parser), **CVE-2023-25577** (Multipart form parsing denial of service in Werkzeug < 2.2.3). |
| **Remediation** | Upgrade `Flask` and `Werkzeug` in `requirements.txt` to the latest releases (`pip install --upgrade flask werkzeug`). |

---

## Safe Manual Verification Steps

### 1. Verify SQL Injection
- Navigate to `http://127.0.0.1:5000/`
- Enter `1' OR '1'='1` or `%' OR 1=1--` into the product search bar and click **Search**.
- **Result**: All products in the database are returned, confirming SQL string concatenation.
- Enter `'` (single quote) into search.
- **Result**: Triggers a SQLite syntax error exposed via the application error handler.

### 2. Verify Broken Access Control (IDOR)
- Log in as user `bob` (`bob` / `bobpass456`).
- Navigate to `http://127.0.0.1:5000/profile?id=1` or `http://127.0.0.1:5000/profile?id=2`.
- **Result**: You can view profile details for `admin` (ID 1) and `alice` (ID 2).
- Navigate to `http://127.0.0.1:5000/order/1`.
- **Result**: You can view the order receipt and items for Alice's order without authorization.

### 3. Verify Admin Access without Privilege
- While logged in as `alice` (or logged out), open `http://127.0.0.1:5000/admin/users`.
- **Result**: The page loads the complete user list including plaintext passwords.

### 4. Verify Security Misconfiguration & Exposed Debug Info
- Open `http://127.0.0.1:5000/debug/info` in your web browser.
- **Result**: Receives a JSON payload displaying internal Flask debug status, database file paths, and server environment parameters.

### 5. Verify Session Cookie Weakness
- Open Browser Developer Tools (F12) -> Application -> Cookies -> `http://127.0.0.1:5000`.
- Look at `session` cookie flags.
- **Result**: The `HttpOnly` flag is unchecked (`False`), allowing `document.cookie` inspection.

---

## Evidence & Screenshots to Collect for Assignment

When documenting findings for your Application Security / Red Team report:

1. **SQL Injection**:
   - Screenshot of the URL bar containing `http://127.0.0.1:5000/search?q=%27+OR+1%3D1--`
   - Screenshot of search results returning all records or the SQLite syntax error prompt.
2. **Broken Access Control**:
   - Screenshot of active session as `bob` viewing `/profile?id=2` (Alice's Profile).
   - Screenshot of active session as `bob` viewing `/order/1` (Alice's Order Receipt).
   - Screenshot of `/admin/users` loaded without admin privilege.
3. **Security Misconfiguration**:
   - Screenshot of `/debug/info` JSON output.
   - Screenshot of Python exception stack trace rendered on screen when triggering a syntax error.
4. **Session & Password Weakness**:
   - Screenshot of Browser DevTools Cookies tab showing `HttpOnly` is disabled for `session`.
   - Screenshot of `/admin/users` showing stored plaintext passwords (`admin123`, `password123`).
5. **OWASP ZAP Automated Scan**:
   - Screenshot of ZAP Alerts tree showing SQL Injection, Missing Anti-clickjacking Header / Cookie flags, and Information Disclosure alerts.
