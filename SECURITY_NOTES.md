# SecureShop - Vulnerability Reference & Security Assessment Guide

This document details the intentional security flaws built into **SecureShop** for Red Team testing, OWASP ZAP scanning, and application security evaluation.

---

## 1. Broken Access Control (OWASP A01:2021)

### A. Insecure Direct Object Reference (IDOR) - User Profile
- **Location**: `app.py`, route `/profile` (lines 141–157)
- **Vulnerable Code**:
  ```python
  target_id = request.args.get('id', session['user_id'])
  user = conn.execute("SELECT id, username, email, role, full_name, address FROM users WHERE id = ?", (target_id,)).fetchone()
  ```
- **Root Cause**: The application reads `target_id` directly from the URL query parameter without verifying if `target_id == session['user_id']` or if the requesting user has administrative privileges.
- **Impact**: Any authenticated user can view the full name, email, address, and role of any other user in the database by changing `?id=N`.
- **Remediation**: Enforce strict authorization logic:
  ```python
  if int(target_id) != session['user_id'] and session.get('role') != 'admin':
      flash("Unauthorized access.", "error")
      return redirect(url_for('profile'))
  ```

### B. IDOR - Order Details
- **Location**: `app.py`, route `/order/<int:order_id>` (lines 274–297)
- **Vulnerable Code**:
  ```python
  order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
  ```
- **Root Cause**: The handler queries the `orders` table by `order_id` without checking `WHERE id = ? AND user_id = ?`.
- **Impact**: Authenticated users can read invoice details and order history for any order in the system by incrementing the order ID parameter.
- **Remediation**: Restrict query to the logged-in user or check admin status:
  ```python
  order = conn.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, session['user_id'])).fetchone()
  ```

### C. Missing Function Level Access Control - Admin Routes
- **Location**: `app.py`, routes `/admin`, `/admin/users`, `/admin/products` (lines 301–341)
- **Vulnerable Code**:
  ```python
  @app.route('/admin')
  def admin_dashboard():
      # Missing role check!
      ...
  ```
- **Root Cause**: Lack of RBAC middleware or decorator validating `session.get('role') == 'admin'`.
- **Impact**: Standard users (or unauthenticated users) can directly access administrative stats, user tables, and inventory modification features.
- **Remediation**: Implement an `@admin_required` decorator check on all administrative routes:
  ```python
  def admin_required(f):
      @wraps(f)
      def decorated_function(*args, **kwargs):
          if session.get('role') != 'admin':
              flash("Admin access required.", "error")
              return redirect(url_for('login'))
          return f(*args, **kwargs)
      return decorated_function
  ```

---

## 2. SQL Injection (OWASP A03:2021)

- **Location**: `app.py`, route `/search` (lines 54–73)
- **Vulnerable Code**:
  ```python
  sql = f"SELECT * FROM products WHERE name LIKE '%{query}%' OR description LIKE '%{query}%' OR category LIKE '%{query}%'"
  cursor.execute(sql)
  ```
- **Root Cause**: Dynamic string formatting (`f"..."`) inserts raw user input directly into SQL statements without sanitization or parameterized bindings.
- **Impact**: Attackers can manipulate query execution logic, bypass filters, extract data from other database tables via `UNION SELECT`, or cause database errors.
- **Manual POC Payloads**:
  - Boolean Bypass: `' OR 1=1 --`
  - UNION Injection test: `' UNION SELECT 1, username, password, role, email, 10 FROM users --`
- **Expected ZAP Finding**: High Severity — SQL Injection (SQLite).
- **Remediation**: Use parameterized queries:
  ```python
  sql = "SELECT * FROM products WHERE name LIKE ? OR description LIKE ? OR category LIKE ?"
  param = f"%{query}%"
  cursor.execute(sql, (param, param, param))
  ```

---

## 3. Security Misconfiguration (OWASP A05:2021)

### A. Debug Mode Enabled & Weak Secret Key
- **Location**: `app.py` (lines 9–10)
- **Vulnerable Code**:
  ```python
  app.config['SECRET_KEY'] = 'secureshop_secret_123'
  app.config['DEBUG'] = True
  ```
- **Root Cause**: Hardcoded, guessable secret key and persistent interactive debugger enabled.
- **Impact**: Hardcoded secret keys allow attackers to forge Flask session cookies. Debug mode can expose interactive web consoles or detailed stack traces containing sensitive internal paths and variables.

### B. Diagnostic Information Exposure
- **Location**: `app.py`, route `/debug/info` (lines 352–361)
- **Vulnerable Code**:
  ```python
  @app.route('/debug/info')
  def debug_info():
      info = { "flask_version": "2.0.1", "secret_key": app.config['SECRET_KEY'], ... }
      return jsonify(info)
  ```
- **Root Cause**: Endpoints exposing environment configuration details without authentication.
- **Remediation**: Disable debug mode in production, use environment variables for `SECRET_KEY`, and remove diagnostic debug endpoints.

---

## 4. Authentication & Session Weaknesses (OWASP A07:2021)

### A. Non-HttpOnly Session Cookie
- **Location**: `app.py` (line 13)
- **Vulnerable Code**:
  ```python
  app.config['SESSION_COOKIE_HTTPONLY'] = False
  ```
- **Impact**: Client-side scripts (e.g. via Cross-Site Scripting) can read the session cookie using `document.cookie`.
- **Remediation**: Set `SESSION_COOKIE_HTTPONLY = True`.

### B. Plaintext Password Storage
- **Location**: `database.py` (lines 22–28) & `app.py` (lines 98–101)
- **Impact**: If database records are leaked via SQL Injection or IDOR, user passwords are immediately exposed without cryptographic hashing.
- **Remediation**: Hash passwords using `werkzeug.security.generate_password_hash` and check via `check_password_hash`.

---

## 5. Legitimate Outdated Dependency Audit (OWASP A06:2021)

- **Dependency**: `Werkzeug==2.0.1` / `Flask==2.0.1` (specified in `requirements.txt`)
- **Current Version**: `Werkzeug 3.0.x` / `Flask 3.0.x`
- **Security Concern**: 
  - **CVE-2022-29361**: Vulnerability in HTTP parsing handling within Werkzeug.
  - **CVE-2023-25577**: High risk multipart form parsing denial-of-service vulnerability where parsing excessive fields triggers severe CPU load or crashes in Werkzeug versions prior to 2.2.3.
- **Remediation**: Update `requirements.txt` to:
  ```text
  Flask>=3.0.0
  Werkzeug>=3.0.0
  ```

---

## OWASP ZAP Scanning Recommendations

1. Start SecureShop on `http://127.0.0.1:5000`.
2. Configure OWASP ZAP Automated Scanner with target `http://127.0.0.1:5000`.
3. Perform an Automated Scan or Spider + Active Scan.
4. Review ZAP Alerts tree for:
   - **SQL Injection** (`/search?q=`)
   - **Cookie No HttpOnly Flag**
   - **Directory Browsing / Information Disclosure**
   - **Missing Anti-clickjacking / Content-Security-Policy Headers**
