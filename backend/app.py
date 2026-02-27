from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory, send_file, redirect
from flask_cors import CORS
import os
import json
import requests
from dotenv import load_dotenv
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import db_railway as db
import logging
from werkzeug.middleware.proxy_fix import ProxyFix
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format='%(asctime)s %(levelname)s %(message)s')

# ✅ Load .env FIRST before any os.getenv() calls
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend'))
# Trust proxy headers from reverse proxies/CDNs
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Enforce HTTPS in production (respecting X-Forwarded-Proto from proxy)
@app.before_request
def enforce_https_in_production():
    if os.getenv('ENVIRONMENT') == 'production':
        proto = request.headers.get('X-Forwarded-Proto', request.scheme)
        if proto != 'https':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=308)

# Helper for reading boolean environment flags consistently

def env_bool(key, default=False):
    val = os.getenv(key)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "t", "yes", "y", "on")

# Frontend path helpers to avoid duplication
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

def fe_path(*parts):
    return os.path.join(FRONTEND_DIR, *parts)

# Admin credentials (kept for future login re-implementation)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    logging.warning("[WARN] ADMIN_USERNAME or ADMIN_PASSWORD not set. Admin login will be unauthenticated until credentials are configured.")


# Pricing restriction message
PRICING_RESPONSE = "Thank you for your interest! For pricing details, please contact our sales team at sales@spectalpackaging.com or call +91 9036254107. Our team will provide you with detailed quotes tailored to your needs."

# Keywords that trigger pricing restriction
PRICING_KEYWORDS = [
    r'\b(price|pricing|cost|rate|quote|fee|quotation|how much)\b',
    r'\b(afford|payment|budget|expensive|cheap|discount|offer)\b',
    r'\b(invoice|billing|payment terms|price list)\b'
]



# Load knowledge base files
KNOWLEDGE_BASE_PATH = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge-base'
)

COMPANY_KNOWLEDGE = ""
kb_files = ['company-info.md', 'products.md','foqs.md']

try:
    os.makedirs(KNOWLEDGE_BASE_PATH, exist_ok=True)
    for kb_file in kb_files:
        file_path = os.path.join(KNOWLEDGE_BASE_PATH, kb_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            COMPANY_KNOWLEDGE += f.read() + "\n"
    print(f"[OK] Knowledge base loaded with {len(kb_files)} files from {KNOWLEDGE_BASE_PATH}")
except FileNotFoundError as e:
    COMPANY_KNOWLEDGE = "No company information available."
    print(f"[WARNING] Knowledge base file NOT found: {e}")
    print(f"[INFO] Create files in: {os.path.abspath(KNOWLEDGE_BASE_PATH)}")
print(f"[INFO] KB total length: {len(COMPANY_KNOWLEDGE)} characters")

# Allow CORS, preferably restricted to Frontend URL in production
frontend_url = os.getenv("FRONTEND_URL", "*")

# For local file double-clicking 'null' origin, allow wildcard in development
if env_bool('DEV_MODE') or os.getenv('ENVIRONMENT') == 'development':
    CORS(app, resources={r"/api/*": {"origins": "*"}})
else:
    # Split comma-separated URLs into a list for production
    origins_list = [url.strip() for url in frontend_url.split(',') if url.strip()]
    if not origins_list:
        print("[ERROR] FRONTEND_URL not set for production; refusing to start with insecure/broken CORS")
        import sys; sys.exit(1)
    CORS(app, resources={r"/api/*": {"origins": origins_list}})

# Configure Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# ✅ FIX #12: Add Security Headers
# Helper to build the security headers dict (easier to test and reuse)

def security_headers():
    headers = {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
    }
    if os.getenv('ENVIRONMENT') == 'production':
        headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    return headers

@app.after_request
def set_security_headers(response):
    """Add essential security headers to all responses"""
    for k, v in security_headers().items():
        response.headers[k] = v
    return response

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
MODEL = "gemini-2.5-flash"

@app.route('/')
def home():
    """Serve the main chat widget on root domain"""
    widget_path = fe_path('web-widget', 'index.html')
    return send_file(widget_path)

def is_pricing_query(message):
    """
    Check if user message is asking about pricing
    Returns True if pricing keywords are detected
    """
    message_lower = message.lower()
    for pattern in PRICING_KEYWORDS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return True
    return False



@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint using direct Gemini API calls 
    """
    try:
        # Verify API key exists
        if not GEMINI_API_KEY:
            # Log internal detail only
            print("[WARN] GEMINI_API_KEY missing")
            return jsonify({
                "success": False,
                "error": "Service temporarily unavailable. Please try again later."
            }), 503
        
        # Parse request
        data = request.get_json(silent=True) or {}
        if not data or 'message' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'message' in request body"
            }), 400     
        
        user_message = data.get('message', '')
        if not isinstance(user_message, str):
            return jsonify({"success": False, "error": "Invalid message format"}), 400
        
        # ✅ Validate message length (prevent DoS attacks - max 5000 chars)
        if len(user_message) > 5000:
            return jsonify({
                "success": False,
                "error": "Message too long (max 5000 characters)"
            }), 400
        
        if len(user_message.strip()) == 0:
            return jsonify({
                "success": False,
                "error": "Message cannot be empty"
            }), 400
        
        chat_history = data.get('chatHistory', [])
        if not isinstance(chat_history, list):
            chat_history = []
        else:
            chat_history = [m for m in chat_history if isinstance(m, dict)]
        
        # Predefined Response helper for pricing, etc.
        user_id_raw = data.get('user_id')
        user_id = int(user_id_raw) if isinstance(user_id_raw, (int, str)) and str(user_id_raw).strip().isdigit() else None
        
        def handle_predefined_response(response_text):
            # Save to Database before yielding
            if user_id is not None:
                try:
                    session_id = db.get_active_session(user_id)
                    if session_id:
                        db.save_message(session_id, 'user', user_message)
                        db.save_message(session_id, 'assistant', response_text)
                except Exception as e:
                    print(f"Failed to save chat: {str(e)}")
            
            def generate_predefined():
                yield f"data: {json.dumps({'chunk': response_text})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            return Response(stream_with_context(generate_predefined()), mimetype='text/event-stream')

        # === PRE-DEFINED RESPONSES ===
        
        # Pricing inquiry — redirect to sales team
        if is_pricing_query(user_message):
            return handle_predefined_response(PRICING_RESPONSE)
        
        messages = [
            {
                "role": "system",
                "content": f"""You are Spectal Pack AI Bot, a smart, polite, and helpful assistant for Spectal Pack.
    === COMPANY KNOWLEDGE BASE ===
     {COMPANY_KNOWLEDGE}
    === END KNOWLEDGE BASE ===
    
    CRITICAL RULES & PERSONALITY:
    1. TONE AND STYLE: Answer in plain English with proper, conversational sentences. Be polite and natural like a professional customer service representative.
    2. EXTREME CONCISENESS (CRITICAL): Your answers MUST be extremely short. MAXIMUM 1 TO 3 SENTENCES per response. NEVER write long paragraphs. NEVER list out multiple reasons or long explanations unless the user explicitly types the word "explain in detail". Get straight to the point, answer the question directly, and stop.
    3. LISTS: When asked what products or services you offer, YOU MUST ONLY PROVIDE A VERTICAL NUMBERED LIST OR BULLETED LIST WITH EXPLICIT LINE BREAKS. **DO NOT GIVE ANY DESCRIPTIONS, EXPLANATIONS, OR DEFINITIONS OF THE PRODUCTS WHATSOEVER.**
    4. KNOWLEDGE LIMITS: If the user asks for something NOT in the knowledge base or outside our products/services, DO NOT make up information. Politely say something convincing like: "I'm sorry, I don't have those specific details right now, but please contact info@spectalpack.com and our team will be happy to help you."
    5. PRODUCTS/SERVICES: If asked about products or services, strictly refer to the items listed in the knowledge base. Do not talk about products outside of our catalog.
    6. PRICING INQUIRIES: You are STRICTLY PROHIBITED from giving specific prices, costs, or quotes. If asked, respond politely that pricing depends on specific requirements (like size/quantity) and ask them to contact info@spectalpack.com for a custom quote.
    7. IDENTITY: Never mention you're an AI or language model. Always represent Spectal Pack accurately.
    8. **STRICT TOPIC RULE: ONLY answer the specific question asked by the user. DO NOT offer unsolicited details or links.**
    """
        }
    
        ]
        
        # Add recent chat history for context (last 5 messages)
        for msg in chat_history[-5:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("content", "")
            # Skip loading indicators and empty messages
            if content and not content.startswith("<div") and content.strip():
                # Avoid passing the last user message twice
                if role == "user" and content == user_message and msg == chat_history[-1]:
                    continue
                messages.append({"role": role, "content": content})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Make upstream request first to decide HTTP status before starting SSE
        try:
            upstream = requests.post(
                GEMINI_API_URL,
                headers={
                    "Authorization": f"Bearer {GEMINI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 350,
                    "top_p": 1,
                    "stream": True
                },
                stream=True,
                timeout=60
            )
        except requests.exceptions.Timeout:
            return Response(f"data: {json.dumps({'error': 'AI service timeout. Please try again in a moment.'})}\n\n", mimetype='text/event-stream', status=504)
        except requests.exceptions.RequestException:
            return Response(f"data: {json.dumps({'error': 'Network error while connecting to AI service.'})}\n\n", mimetype='text/event-stream', status=502)

        if upstream.status_code != 200:
            try:
                error_detail = upstream.json().get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_detail = f"HTTP {upstream.status_code}"

            print(f"Gemini API Error ({upstream.status_code}): {error_detail}")

            if upstream.status_code == 429:
                user_friendly_msg = "Sorry, we are currently facing high traffic and server trouble. Please try again later."
                body = f"data: {json.dumps({'error': user_friendly_msg})}\n\n"
                try:
                    db.create_notification("API Rate Limit Hit", f"Gemini API returned HTTP 429: {error_detail}", "error")
                except Exception:
                    pass
                if user_id is not None:
                    try:
                        session_id = db.get_active_session(user_id)
                        if session_id:
                            db.save_message(session_id, 'user', user_message)
                            db.save_message(session_id, 'assistant', f"[SYSTEM ERROR: 429 Rate Limit - {error_detail}]")
                    except Exception:
                        pass
                return Response(body, mimetype='text/event-stream', status=429)

            # Non-429 upstream failure: send terminal SSE error and 502 Bad Gateway
            body = f"data: {json.dumps({'error': 'AI service unavailable. Please try again later.'})}\n\n"
            return Response(body, mimetype='text/event-stream', status=502)

        def generate_stream():
            full_response = ""
            try:
                # Stream the chunks
                max_stream_chars = 8000
                for line in upstream.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            chunk_data = line[6:]
                            if chunk_data == '[DONE]':
                                break
                            try:
                                chunk_json = json.loads(chunk_data)
                                if 'choices' in chunk_json and len(chunk_json['choices']) > 0:
                                    delta = chunk_json['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        if len(full_response) < max_stream_chars:
                                            remaining = max_stream_chars - len(full_response)
                                            full_response += content[:remaining]
                                        yield f"data: {json.dumps({'chunk': content})}\n\n"
                            except json.JSONDecodeError:
                                pass
                # Signal completion
                yield f"data: {json.dumps({'done': True})}\n\n"

                # Save chat to database after streaming completes
                if user_id is not None:
                    try:
                        session_id = db.get_active_session(user_id)
                        if session_id:
                            db.save_message(session_id, 'user', user_message)
                            db.save_message(session_id, 'assistant', full_response)
                    except Exception as e:
                        print(f"Failed to save chat: {str(e)}")
            except requests.exceptions.Timeout:
                yield f"data: {json.dumps({'error': 'AI service timeout. Please try again in a moment.'})}\n\n"
            except requests.exceptions.RequestException:
                yield f"data: {json.dumps({'error': 'Network error while connecting to AI service.'})}\n\n"
            except Exception as e:
                import traceback
                print(f"Unexpected error in stream: {str(e)}")
                yield f"data: {json.dumps({'error': f'Internal error during streaming'})}\n\n"

        return Response(stream_with_context(generate_stream()), mimetype='text/event-stream')
        
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "error": "AI service timeout"}), 504
    except Exception as e:
        import traceback
        # Log error but don't expose sensitive info to client
        print(f"[ERROR] in /api/chat: {str(e)}")
        print(f"[DEBUG] {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": "Internal server error. Please try again later or contact support."
        }), 500

@app.route('/api/chat/history/<int:session_id>', methods=['GET'])
def get_user_chat_history(session_id):
    """
    Public endpoint to fetch all messages for a specific session to restore chat history
    on the client side.
    """
    try:
        req_user_id = request.args.get('user_id')
        if not req_user_id:
            return jsonify({"success": False, "error": "Unauthorized: Missing user_id"}), 401

        connection = db.get_connection()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT user_id FROM chat_sessions WHERE id = %s", (session_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({"success": False, "error": "invalid_session"}), 404
                if str(row[0]) != str(req_user_id):
                    return jsonify({"success": False, "error": "Forbidden: Session ownership mismatch"}), 403
            finally:
                try:
                    cursor.close()
                finally:
                    connection.close()

        messages = db.get_session_messages(session_id)
        # Format for the frontend script expectations
        formatted_history = []
        for msg in messages:
            formatted_history.append({
                "id": msg["id"],
                "role": msg["role"], # "user" or "assistant"
                "content": msg["content"],
                "timestamp": msg["timestamp"] # Will be serialized to string by jsonify
            })
        return jsonify({"success": True, "history": formatted_history}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/api/chat/message/<int:message_id>', methods=['DELETE'])
def api_delete_message(message_id):
    """Delete a specific message from chat history if owned by the user."""
    try:
        req_user_id = request.args.get('user_id')
        if not req_user_id:
            return jsonify({"success": False, "error": "Unauthorized: Missing user_id"}), 401

        connection = db.get_connection()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute('''
                    SELECT chat_sessions.user_id 
                    FROM messages 
                    JOIN chat_sessions ON messages.session_id = chat_sessions.id 
                    WHERE messages.id = %s
                ''', (message_id,))
                row = cursor.fetchone()
                
                if not row:
                    return jsonify({"success": False, "error": "Message not found"}), 404
                    
                if str(row[0]) != str(req_user_id):
                    return jsonify({"success": False, "error": "Forbidden: Message ownership mismatch"}), 403
            finally:
                try:
                    cursor.close()
                finally:
                    connection.close()

        success = db.delete_message(message_id)
        if success:
            return jsonify({"success": True, "message": "Message deleted"}), 200
        else:
            return jsonify({"success": False, "error": "Message not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/user', methods=['POST'])
@limiter.limit("10 per minute")  # ✅ Rate limit to prevent spam
def create_user_endpoint():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        Company = data.get('company', '').strip()
        email = data.get('email', '').strip()

        if not all([name, Company, email]):
            return jsonify({'success': False, 'error': 'All fields required'}), 400
        
        # ✅ FIX #11: Input Validation - Check field lengths & prevent DoS
        if len(name) < 2 or len(name) > 100:
            return jsonify({'success': False, 'error': 'Name must be 2-100 characters'}), 400
        if len(Company) < 2 or len(Company) > 150:
            return jsonify({'success': False, 'error': 'Company must be 2-150 characters'}), 400
        if len(email) > 255 or len(email) < 5:
            return jsonify({'success': False, 'error': 'Email must be 5-255 characters'}), 400
        
        # Basic email validation (lightweight)
        if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400

        # Create user + session using Database module
        user_id, session_id = db.create_user(name, Company, email)

        if user_id and session_id:
            return jsonify({
                'success': True,
                'user_id': user_id,
                'session_id': session_id,
                'message': f"User {name} created successfully"
            }), 201
        else:
            return jsonify({'success': False, 'error': 'Failed to create user'}), 500
      
    except Exception as e:
        print(f"[ERROR] in create_user: {str(e)}")
        return jsonify({'success': False, 'error': "Failed to create user. Please try again."}), 500

@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    """Admin: Fetch all users"""
    try:
        users = db.get_all_users()
        return jsonify({"success": True, "users": users}), 200
    except Exception as e:
        print(f"[ERROR] in admin_get_users: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch users. Contact support."}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    """Admin: Delete a specific user"""
    try:
        success = db.delete_user(user_id)
        if success:
            return jsonify({"success": True, "message": "User deleted successfully"}), 200
        else:
            return jsonify({"success": False, "error": "User not found or could not be deleted"}), 404
    except Exception as e:
        print(f"[ERROR] in admin_delete_user: {str(e)}")
        return jsonify({"success": False, "error": "Failed to delete user. Contact support."}), 500

@app.route('/api/admin/sessions/<int:user_id>', methods=['GET'])
def admin_get_sessions(user_id):
    """Admin: Fetch all sessions for a specific user"""
    try:
        sessions = db.get_user_sessions(user_id)
        return jsonify({"success": True, "sessions": sessions}), 200
    except Exception as e:
        print(f"[ERROR] in admin_get_sessions: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch sessions. Contact support."}), 500

@app.route('/api/admin/messages/<int:session_id>', methods=['GET'])
def admin_get_messages(session_id):
    """Admin: Fetch all messages for a specific session"""
    try:
        messages = db.get_session_messages(session_id)
        return jsonify({"success": True, "messages": messages}), 200
    except Exception as e:
        print(f"[ERROR] in admin_get_messages: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch messages. Contact support."}), 500

@app.route('/api/admin/sessions/<int:session_id>', methods=['DELETE'])
def admin_delete_session(session_id):
    """Admin: Delete a specific session"""
    try:
        success = db.delete_session(session_id)
        if success:
            return jsonify({"success": True, "message": "Session deleted successfully"}), 200
        else:
            return jsonify({"success": False, "error": "Session not found or could not be deleted"}), 404
    except Exception as e:
        print(f"[ERROR] in admin_delete_session: {str(e)}")
        return jsonify({"success": False, "error": "Failed to delete session. Contact support."}), 500


@app.route('/api/admin/notifications', methods=['GET'])
def admin_get_notifications():
    """Admin: Fetch unread notifications"""
    try:
        notifications = db.get_unread_notifications()
        return jsonify({"success": True, "notifications": notifications}), 200
    except Exception as e:
        print(f"[ERROR] in admin_get_notifications: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch notifications. Contact support."}), 500

@app.route('/api/admin/notifications/<int:notif_id>/read', methods=['POST'])
def admin_mark_notification_read(notif_id):
    """Admin: Mark notification as read"""
    try:
        success = db.mark_notification_read(notif_id)
        if success:
            return jsonify({"success": True, "message": "Notification marked read"}), 200
        else:
            return jsonify({"success": False, "error": "Failed to mark read or not found"}), 404
    except Exception as e:
        print(f"[ERROR] in admin_mark_notification_read: {str(e)}")
        return jsonify({"success": False, "error": "Failed to update notification. Contact support."}), 500

# ==================== STATIC FILE SERVING ====================

@app.route('/admin')
def admin_panel():
    """Serve admin panel"""
    admin_panel_path = fe_path('admin-panel', 'index.html')
    return send_file(admin_panel_path)

@app.route('/admin/style.css')
def admin_style():
    """Serve admin panel CSS"""
    return send_from_directory(
        fe_path('admin-panel'),
        'style.css'
    )

@app.route('/admin/script.js')
def admin_script():
    """Serve admin panel JavaScript"""
    return send_from_directory(
        fe_path('admin-panel'),
        'script.js'
    )

@app.route('/web-widget')
def web_widget():
    """Serve chat widget (public, no login required)"""
    widget_path = fe_path('web-widget', 'index.html')
    return send_file(widget_path)

@app.route('/web-widget/styles.css')
def widget_styles():
    """Serve widget CSS"""
    return send_from_directory(
        fe_path('web-widget'),
        'styles.css'
    )

@app.route('/web-widget/script.js')
def widget_script():
    """Serve widget JavaScript"""
    return send_from_directory(
        fe_path('web-widget'),
        'script.js'
    )

# ✅ FIX: Serve CSS and JS from root domain (/) for web-widget
@app.route('/styles.css')
def root_styles():
    """Serve widget CSS from root domain"""
    return send_from_directory(
        fe_path('web-widget'),
        'styles.css'
    )

@app.route('/script.js')
def root_script():
    """Serve widget JavaScript from root domain"""
    return send_from_directory(
        fe_path('web-widget'),
        'script.js'
    )

@app.route('/avatar1.jpg')
def avatar1_image():
    """Serve avatar1 image from root domain"""
    return send_from_directory(
        fe_path('web-widget'),
        'avatar1.jpg'
    )



if __name__ == '__main__':
    try:
        db.init_db()
        logging.info("Database initialized")
    except Exception as e:
        logging.error("Database initialization failed: %s", e)
        if os.getenv('ENVIRONMENT') == 'production':
            import sys; sys.exit(1)
    port = int(os.getenv('PORT', 3000))
    api_status = "YES" if GEMINI_API_KEY else "NO (Check .env file!)"
    logging.info("Spectal Chatbot API starting on http://localhost:%s", port)
    logging.info("Gemini API configured: %s", api_status)
    logging.info("Chat endpoint: http://localhost:%s/api/chat", port)
    logging.info("Frontend URL CORS: %s", frontend_url)
    
    # Run in production mode with debug=False by default unless explicitly enabled
    is_debug = env_bool("FLASK_DEBUG", False)
    if not is_debug:
        logging.info("Running in PRODUCTION mode (Waitress/Gunicorn recommended)")
    app.run(host='0.0.0.0', port=port, debug=is_debug)