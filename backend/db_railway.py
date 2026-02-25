import mysql.connector
from mysql.connector import pooling
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load env vars before defining dbconfig
load_dotenv()

# Create a global connection pool
dbconfig = {
    "host": os.getenv('MYSQLHOST', 'localhost'),
    "user": os.getenv('MYSQLUSER', 'root'),
    "password": os.getenv('MYSQLPASSWORD', ''),
    "database": os.getenv('MYSQLDATABASE', 'railway'),
    "port": int(os.getenv('MYSQLPORT', 3306)),
    "charset": 'utf8mb4',
    "collation": 'utf8mb4_unicode_ci',
    "autocommit": True,
}

try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="spectalpack_pool",
        pool_size=5,
        pool_reset_session=True,
        **dbconfig
    )
except Error as e:
    print(f"[ERROR] Failed to create connection pool: {e}")
    connection_pool = None

def get_connection():
    """Get Railway MySQL connection from pool"""
    try:
        if connection_pool:
            return connection_pool.get_connection()
        else:
            # Fallback if pool failed
            return mysql.connector.connect(**dbconfig)
    except Error as e:
        print(f"[ERROR] MySQL Connection Error: {e}")
        return None

def init_db():
    """Create tables automatically on first run"""
    connection = get_connection()
    if not connection:
        print("[WARN] Could not connect to database")
        return
    
    cursor = connection.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            company VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    
    # Create chat_sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user_active (user_id, is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    
    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id INT NOT NULL,
            role ENUM('user', 'assistant') NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
            INDEX idx_session (session_id),
            INDEX idx_timestamp (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    
    # Create notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            type VARCHAR(50) NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    
    cursor.close()
    connection.close()
    print("[OK] Database tables ready")


def create_user(name, company, email):
    """Create a user and start an active chat session. Returns (user_id, session_id)."""
    connection = get_connection()
    if not connection:
        return None, None

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (name, company, email) VALUES (%s, %s, %s)",
            (name, company, email)
        )
        user_id = cursor.lastrowid
        
        # Trigger lead notification
        create_notification("New Lead Signed Up", f"{name} from {company} ({email}) just started a chat.", "lead")
        
    except Error as e:
        # Handle existing user by email
        if getattr(e, "errno", None) == 1062:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            user_id = row[0] if row else None
        else:
            print(f"[ERROR] Failed to create user: {e}")
            return None, None

    if not user_id:
        return None, None

    try:
        cursor.execute(
            "INSERT INTO chat_sessions (user_id, is_active) VALUES (%s, 1)",
            (user_id,)
        )
        session_id = cursor.lastrowid
        return user_id, session_id
    except Error as e:
        print(f"[ERROR] Failed to create session for user {user_id}: {e}")
        return user_id, None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_active_session(user_id):
    """Return active session id for user, create one if not found."""
    connection = get_connection()
    if not connection:
        return None

    cursor = None
    try:
        cursor = connection.cursor()
        
        # Validate that the user exists first to avoid ghost foreign key errors
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            print(f"[ERROR] Cannot create or get session. User {user_id} does not exist.")
            return None
            
        cursor.execute(
            "SELECT id FROM chat_sessions WHERE user_id = %s AND is_active = 1 ORDER BY started_at DESC LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()

        if row:
            return row[0]
        else:
            cursor.execute(
                "INSERT INTO chat_sessions (user_id, is_active) VALUES (%s, 1)",
                (user_id,)
            )
            return cursor.lastrowid
    except Error as e:
        print(f"[ERROR] Failed to get/create active session: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def save_message(session_id, role, content):
    """Save a chat message. Returns True if successful."""
    if role not in ("user", "assistant"):
        return False
    
    # ✅ Validate content length (prevent DoS)
    if len(content) > 50000:
        print(f"[WARN] Message content too large ({len(content)} chars), truncating")
        content = content[:50000]

    connection = get_connection()
    if not connection:
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content)
        )
        
        # Add sample kit notification if applicable
        if role == 'user' and '[Form Submission: Sample Kit Request]' in content:
            cursor.execute(
                "INSERT INTO notifications (type, title, message) VALUES (%s, %s, %s)",
                ('sample_kit', 'New Sample Kit Request', 'A new sample kit request has been submitted.')
            )
            
        return True
    except Error as e:
        print(f"[ERROR] Failed to save message: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def get_all_users():
    """Admin function: Get all users ordered by creation date."""
    connection = get_connection()
    if not connection:
        return []

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # ✅ Limit to prevent resource exhaustion
        cursor.execute("SELECT id, name, company, email, created_at FROM users ORDER BY created_at DESC LIMIT 10000")
        users = cursor.fetchall()
        return users
    except Error as e:
        print(f"[ERROR] Failed to fetch users: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def get_user_sessions(user_id):
    """Admin function: Get all sessions for a specific user."""
    connection = get_connection()
    if not connection:
        return []

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('''
            SELECT id, started_at, ended_at, is_active 
            FROM chat_sessions 
            WHERE user_id = %s 
            ORDER BY started_at DESC
            LIMIT 100
        ''', (user_id,))
        sessions = cursor.fetchall()
        return sessions
    except Error as e:
        print(f"[ERROR] Failed to fetch sessions: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def get_session_messages(session_id):
    """Admin function: Get all messages for a specific session."""
    connection = get_connection()
    if not connection:
        return []

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('''
            SELECT id, role, content, timestamp 
            FROM messages 
            WHERE session_id = %s 
            ORDER BY timestamp ASC
            LIMIT 1000
        ''', (session_id,))
        messages = cursor.fetchall()
        return messages
    except Error as e:
        print(f"[ERROR] Failed to fetch messages: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def delete_session(session_id):
    """Admin function: Delete a specific session and all its messages."""
    connection = get_connection()
    if not connection:
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        # Based on schema ON DELETE CASCADE is set for messages
        cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
        return cursor.rowcount > 0
    except Error as e:
        print(f"[ERROR] Failed to delete session: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def delete_message(message_id):
    """Delete a specific message."""
    connection = get_connection()
    if not connection:
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM messages WHERE id = %s", (message_id,))
        return cursor.rowcount > 0
    except Error as e:
        print(f"[ERROR] Failed to delete message: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def delete_user(user_id):
    """Admin function: Delete a specific user and all their data."""
    connection = get_connection()
    if not connection:
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        return cursor.rowcount > 0
    except Error as e:
        print(f"[ERROR] Failed to delete user: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def get_unread_notifications():
    """Admin function: Get all unread notifications."""
    connection = get_connection()
    if not connection:
        return []

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, type, title, message, is_read, created_at FROM notifications WHERE is_read = 0 ORDER BY created_at DESC LIMIT 500"
        )
        notifications = cursor.fetchall()
        
        # Format datetimes for JSON serialization
        for notif in notifications:
            if notif['created_at']:
                notif['created_at'] = notif['created_at'].isoformat()
                
        return notifications
    except Error as e:
        print(f"[ERROR] Failed to fetch notifications: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def mark_notification_read(notif_id):
    """Admin function: Mark notification as read."""
    connection = get_connection()
    if not connection:
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = %s", (notif_id,))
        return cursor.rowcount > 0
    except Error as e:
        print(f"[ERROR] Failed to mark notification read: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def get_all_sample_kit_requests():
    """Admin function: Get all parsed sample kit requests from messaging history."""
    connection = get_connection()
    if not connection:
        return []

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        import re
        
        # Search messages starting with the identifier. Join with users to get basic details.
        cursor.execute('''
            SELECT m.id, m.content, m.timestamp, u.name as user_name, u.email as user_email, u.company as user_company
            FROM messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE m.role = 'user' AND m.content LIKE '%[Form Submission: Sample Kit Request]%'
            ORDER BY m.timestamp DESC
            LIMIT 1000
        ''')
        requests = cursor.fetchall()
        
        # Parse the text block into structured JSON safely using Regex in case newlines were stripped.
        parsed_requests = []
        for req in requests:
            content = req["content"]
            
            parsed_req = {
                "id": req["id"],
                "timestamp": req["timestamp"].isoformat() if req["timestamp"] else None,
                "user_name": req["user_name"],
                "user_email": req["user_email"],
                "user_company": req["user_company"],
                # Defaults
                "form_name": "N/A",
                "form_company": "N/A",
                "phone": "N/A",
                "email": "N/A",
                "address": "N/A",
                "remarks": "None"
            }
            
            # Regex extractors - using more robust patterns to handle potential HTML/Markdown from the chat widget
            name_match = re.search(r'Name:\s*<[^>]+>\s*(.*?)(?:<br>|\n|(?=\s*<strong))', content, re.IGNORECASE)
            if not name_match: name_match = re.search(r'Name:\s*(.*?)(?=\s*Company:|$)', content, re.IGNORECASE)
            
            company_match = re.search(r'Company:\s*<[^>]+>\s*(.*?)(?:<br>|\n|(?=\s*<strong))', content, re.IGNORECASE)
            if not company_match: company_match = re.search(r'Company:\s*(.*?)(?=\s*Phone:|$)', content, re.IGNORECASE)
            
            phone_match = re.search(r'Phone:\s*<[^>]+>\s*(.*?)(?:<br>|\n|(?=\s*<strong))', content, re.IGNORECASE)
            if not phone_match: phone_match = re.search(r'Phone:\s*(.*?)(?=\s*Email:|$)', content, re.IGNORECASE)
            
            email_match = re.search(r'Email:\s*<[^>]+>\s*(.*?)(?:<br>|\n|(?=\s*<strong))', content, re.IGNORECASE)
            if not email_match: email_match = re.search(r'Email:\s*(.*?)(?=\s*Address:|$)', content, re.IGNORECASE)
            
            address_match = re.search(r'Address:\s*<[^>]+>\s*(.*?)(?:<br>|\n|(?=\s*<strong))', content, re.IGNORECASE)
            if not address_match: address_match = re.search(r'Address:\s*(.*?)(?=\s*Remarks:|$)', content, re.IGNORECASE)
            
            remarks_match = re.search(r'Remarks:\s*<[^>]+>\s*(.*?)(?:<br>|\n|</div>|$)', content, re.IGNORECASE)
            if not remarks_match: remarks_match = re.search(r'Remarks:\s*(.*)', content, re.IGNORECASE)
            
            if name_match: parsed_req["form_name"] = name_match.group(1).strip()
            if company_match: parsed_req["form_company"] = company_match.group(1).strip()
            if phone_match: parsed_req["phone"] = phone_match.group(1).strip()
            if email_match: parsed_req["email"] = email_match.group(1).strip()
            if address_match: parsed_req["address"] = address_match.group(1).strip()
            if remarks_match: parsed_req["remarks"] = remarks_match.group(1).strip() if remarks_match.group(1).strip() else "None"
                    
            # Clean up any residual HTML tags block in case regex picked it up
            def clean_html(text):
                return re.sub(r'<[^>]+>', '', text).strip()
                
            parsed_req["form_name"] = clean_html(parsed_req["form_name"])
            parsed_req["form_company"] = clean_html(parsed_req["form_company"])
            parsed_req["phone"] = clean_html(parsed_req["phone"])
            parsed_req["email"] = clean_html(parsed_req["email"])
            parsed_req["address"] = clean_html(parsed_req["address"])
            parsed_req["remarks"] = clean_html(parsed_req["remarks"])
            
            parsed_requests.append(parsed_req)

        return parsed_requests
    except Error as e:
        print(f"[ERROR] Failed to fetch sample kit requests: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def create_notification(title, message, type):
    """Create a new notification alert"""
    connection = get_connection()
    if not connection:
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        # ✅ Validate input length
        if len(title) > 255 or len(message) > 5000:
            print(f"[WARN] Notification content too large, truncating")
            title = title[:255]
            message = message[:5000]
        
        cursor.execute(
            "INSERT INTO notifications (title, message, type) VALUES (%s, %s, %s)",
            (title, message, type)
        )
        return cursor.rowcount > 0
    except Error as e:
        print(f"[ERROR] Failed to save notification: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == '__main__':
    init_db()