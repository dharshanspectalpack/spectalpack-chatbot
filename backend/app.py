from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory, send_file
from flask_cors import CORS
import os
import json
import requests
from dotenv import load_dotenv
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import db_railway as db

# ✅ Load .env FIRST before any os.getenv() calls
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend'))

# Basic Auth Setup for Admin Panel
auth = HTTPBasicAuth()

# Admin Credentials for Admin Panel (REQUIRED - Must be set in environment)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# ⚠️ PRODUCTION: Fail startup if credentials are missing (no hardcoded defaults)
if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    import sys
    print("\n" + "="*70)
    print("[ERROR] CRITICAL: Admin credentials not configured!")
    print("="*70)
    print("\nYou MUST set these environment variables before starting:")
    print("  • ADMIN_USERNAME=your_admin_username")
    print("  • ADMIN_PASSWORD=your_secure_password_16chars_minimum")
    print("\nExample:")
    print("  export ADMIN_USERNAME=admin_prod")
    print("  export ADMIN_PASSWORD=Your$ecure#Pass123")
    print("\nFor Railway/Cloud deployment:")
    print("  Add these to your environment variables in the platform UI")
    print("="*70 + "\n")
    sys.exit(1)  # Exit immediately - don't allow startup

ADMIN_USERS = {
    ADMIN_USERNAME: generate_password_hash(ADMIN_PASSWORD)
}

@auth.verify_password
def verify_password(username, password):
    if username in ADMIN_USERS and check_password_hash(ADMIN_USERS.get(username), password):
        return username
    return None

# Pricing restriction message
PRICING_RESPONSE = "Thank you for your interest! For pricing details, please contact our sales team at sales@spectalpackaging.com or call +91 9036254107. Our team will provide you with detailed quotes tailored to your needs."

# Keywords that trigger pricing restriction
PRICING_KEYWORDS = [
    r'\b(price|pricing|cost|rate|quote|fee|quotation|how much)\b',
    r'\b(afford|payment|budget|expensive|cheap|discount|offer)\b',
    r'\b(invoice|billing|payment terms|price list)\b'
]

# Sample Kit specific message and form
SAMPLE_KIT_RESPONSE = """<p>Thank you for your interest in a sample kit! Since you are already on our website, you can simply fill out the form below to request one, and our team will get in touch with you shortly.</p>
<form id="sample-kit-form" class="chat-form" onsubmit="submitSampleKitForm(event)">
  <input type="text" id="sk-name" placeholder="Name" required>
  <input type="text" id="sk-company" placeholder="Company Name" required>
  <input type="tel" id="sk-phone" placeholder="Phone Number" required>
  <input type="email" id="sk-email" placeholder="Email Address" required>
  <textarea id="sk-address" placeholder="Shipping Address" required style="width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; font-family: inherit; resize: vertical; min-height: 60px;"></textarea>
  <textarea id="sk-remarks" placeholder="Remarks (Optional)" style="width: 100%; padding: 10px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; font-family: inherit; resize: vertical; min-height: 60px;"></textarea>
  <button type="submit">Submit Request</button>
</form>"""

# Keywords that trigger sample kit restriction
SAMPLE_KIT_KEYWORDS = [
    r'\b(sample kit|sample pack|testing kit)\b'
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
if os.getenv('ENVIRONMENT') == 'development':
    CORS(app, resources={r"/api/*": {"origins": "*"}})
else:
    # Split comma-separated URLs into a list for production
    origins_list = [url.strip() for url in frontend_url.split(',') if url.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins_list}})

# Configure Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# ✅ FIX #12: Add Security Headers
@app.after_request
def set_security_headers(response):
    """Add essential security headers to all responses"""
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    
    # HSTS (Strict Transport Security) - for HTTPS only
    if os.getenv('ENVIRONMENT') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    return response

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

@app.route('/')
def home():
    """Serve the main chat widget on root domain"""
    widget_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'frontend', 
        'web-widget', 
        'index.html'
    )
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

def is_sample_kit_query(message):
    """
    Check if user message is asking for a sample kit
    """
    message_lower = message.lower()
    
    # Do not trigger form if this is the form submission payload itself!
    if "[form submission: sample kit request]" in message_lower:
        return False
        
    for pattern in SAMPLE_KIT_KEYWORDS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return True
    return False

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint using direct Groq API calls 
    """
    try:
        # Verify API key exists and looks valid
        if not GROQ_API_KEY or not GROQ_API_KEY.startswith('gsk_'):
            return jsonify({
                "success": False,
                "error": "Groq API key not configured properly. Check .env file."
            }), 500
        
        # Parse request
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'message' in request body"
            }), 400     
        
        user_message = data['message']
        
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
        
        # Predefined Response helper for pricing, sample kit, etc.
        user_id = data.get('user_id')
        
        def handle_predefined_response(response_text):
            # Save to Database before yielding
            if user_id is not None and str(user_id).strip().isdigit():
                try:
                    session_id = db.get_active_session(int(user_id))
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
        
        # Check if they already submitted the sample kit form
        already_submitted = False
        for msg in chat_history:
            if "[form submission: sample kit request]" in msg.get("content", "").lower():
                already_submitted = True
                break
            
        if is_sample_kit_query(user_message):
            if already_submitted:
                return handle_predefined_response("You have already submitted a sample kit request. Our team will contact you shortly!")
            else:
                return handle_predefined_response(SAMPLE_KIT_RESPONSE)
            
        if "[form submission: sample kit request]" in user_message.lower():
            # Trigger DB notification
            db.create_notification("New Sample Kit Request", f"A user requested a sample kit. Check the Sample Kits tab.", "sample_kit")
            return handle_predefined_response("Thank you! Your sample kit request has been received. Our team will review your details and get in touch with you shortly.")
        
        # Build conversation context with company-specific instructions
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
        
        def generate():
            full_response = ""
            try:
                # Call Groq API directly via HTTP request with streaming enabled
                response = requests.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": MODEL,
                        "messages": messages,
                        "temperature": 0.4,
                        "max_tokens": 350,
                        "top_p": 1,
                        "stream": True # Enable streaming from Groq
                    },
                    stream=True,     # Stream the response back
                    timeout=60
                )
                
                # Handle initial API errors
                if response.status_code != 200:
                    try:
                        error_detail = response.json().get('error', {}).get('message', 'Unknown error')
                    except:
                        error_detail = f"HTTP {response.status_code}"
                    
                    print(f"Groq API Error ({response.status_code}): {error_detail}")
                    
                    if response.status_code == 429:
                        # Rate limit reached
                        user_friendly_msg = "Sorry, we are currently facing high traffic and server trouble. Please try again later."
                        yield f"data: {json.dumps({'error': user_friendly_msg})}\n\n"
                        
                        db.create_notification("API Rate Limit Hit", f"Groq API returned HTTP 429: {error_detail}", "error")
                        
                        # Save the actual error to DB for admins to see
                        user_id = data.get('user_id')
                        if user_id is not None and str(user_id).strip().isdigit():
                            try:
                                session_id = db.get_active_session(int(user_id))
                                if session_id:
                                    db.save_message(session_id, 'user', user_message)
                                    db.save_message(session_id, 'assistant', f"[SYSTEM ERROR: 429 Rate Limit - {error_detail}]")
                            except Exception as e:
                                pass
                        return
                        
                    yield f"data: {json.dumps({'error': f'AI service error: {error_detail}'})}\n\n"
                    return
                
                # Stream the chunks
                for line in response.iter_lines():
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
                                        full_response += content
                                        # Yield the data chunk to frontend immediately
                                        yield f"data: {json.dumps({'chunk': content})}\n\n"
                            except json.JSONDecodeError:
                                pass
                
                # Signal completion
                yield f"data: {json.dumps({'done': True})}\n\n"

                # Save chat to database after streaming completes
                user_id = data.get('user_id')
                if user_id is not None and str(user_id).strip().isdigit():
                    try:
                        session_id = db.get_active_session(int(user_id))
                        if session_id:
                            db.save_message(session_id, 'user', user_message)
                            db.save_message(session_id, 'assistant', full_response)
                    except Exception as e:
                        print(f"Failed to save chat: {str(e)}")

            except requests.exceptions.Timeout:
                yield f"data: {json.dumps({'error': 'AI service timeout. Please try again in a moment.'})}\n\n"
            except requests.exceptions.RequestException as e:
                yield f"data: {json.dumps({'error': 'Network error while connecting to AI service.'})}\n\n"
            except Exception as e:
                import traceback
                print(f"Unexpected error in stream: {str(e)}")
                yield f"data: {json.dumps({'error': f'Internal error during streaming'})}\n\n"
                
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
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
            cursor.execute("SELECT user_id FROM chat_sessions WHERE id = %s", (session_id,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                connection.close()
                return jsonify({"success": False, "error": "invalid_session"}), 404
            
            if str(row[0]) != str(req_user_id):
                cursor.close()
                connection.close()
                return jsonify({"success": False, "error": "Forbidden: Session ownership mismatch"}), 403
                
            cursor.close()
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
            cursor.execute('''
                SELECT chat_sessions.user_id 
                FROM messages 
                JOIN chat_sessions ON messages.session_id = chat_sessions.id 
                WHERE messages.id = %s
            ''', (message_id,))
            row = cursor.fetchone()
            
            if not row:
                cursor.close()
                connection.close()
                return jsonify({"success": False, "error": "Message not found"}), 404
                
            if str(row[0]) != str(req_user_id):
                cursor.close()
                connection.close()
                return jsonify({"success": False, "error": "Forbidden: Message ownership mismatch"}), 403
                
            cursor.close()
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
        
        # Basic email Validation
        if'@' not in email or '.' not in email.split('@')[-1]:
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
@auth.login_required
def admin_get_users():
    """Admin: Fetch all users"""
    try:
        users = db.get_all_users()
        return jsonify({"success": True, "users": users}), 200
    except Exception as e:
        print(f"[ERROR] in admin_get_users: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch users. Contact support."}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@auth.login_required
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
@auth.login_required
def admin_get_sessions(user_id):
    """Admin: Fetch all sessions for a specific user"""
    try:
        sessions = db.get_user_sessions(user_id)
        return jsonify({"success": True, "sessions": sessions}), 200
    except Exception as e:
        print(f"[ERROR] in admin_get_sessions: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch sessions. Contact support."}), 500

@app.route('/api/admin/messages/<int:session_id>', methods=['GET'])
@auth.login_required
def admin_get_messages(session_id):
    """Admin: Fetch all messages for a specific session"""
    try:
        messages = db.get_session_messages(session_id)
        return jsonify({"success": True, "messages": messages}), 200
    except Exception as e:
        print(f"[ERROR] in admin_get_messages: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch messages. Contact support."}), 500

@app.route('/api/admin/sessions/<int:session_id>', methods=['DELETE'])
@auth.login_required
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

@app.route('/api/admin/sample_kits', methods=['GET'])
@auth.login_required
def admin_get_sample_kits():
    """Admin: Fetch all submitted sample kit requests"""
    try:
        sample_kits = db.get_all_sample_kit_requests()
        return jsonify({"success": True, "sample_kits": sample_kits}), 200
    except Exception as e:
        print(f"[ERROR] in admin_get_sample_kits: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch sample kits. Contact support."}), 500

@app.route('/api/admin/notifications', methods=['GET'])
@auth.login_required
def admin_get_notifications():
    """Admin: Fetch unread notifications"""
    try:
        notifications = db.get_unread_notifications()
        return jsonify({"success": True, "notifications": notifications}), 200
    except Exception as e:
        print(f"[ERROR] in admin_get_notifications: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch notifications. Contact support."}), 500

@app.route('/api/admin/notifications/<int:notif_id>/read', methods=['POST'])
@auth.login_required
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
@auth.login_required
def admin_panel():
    """Serve admin panel (login required)"""
    admin_panel_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'frontend', 
        'admin-panel', 
        'index.html'
    )
    return send_file(admin_panel_path)

@app.route('/admin/style.css')
@auth.login_required
def admin_style():
    """Serve admin panel CSS"""
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'admin-panel'),
        'style.css'
    )

@app.route('/admin/script.js')
@auth.login_required
def admin_script():
    """Serve admin panel JavaScript"""
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'admin-panel'),
        'script.js'
    )

@app.route('/web-widget')
def web_widget():
    """Serve chat widget (public, no login required)"""
    widget_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'frontend', 
        'web-widget', 
        'index.html'
    )
    return send_file(widget_path)

@app.route('/web-widget/styles.css')
def widget_styles():
    """Serve widget CSS"""
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'web-widget'),
        'styles.css'
    )

@app.route('/web-widget/script.js')
def widget_script():
    """Serve widget JavaScript"""
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'web-widget'),
        'script.js'
    )

# ✅ FIX: Serve CSS and JS from root domain (/) for web-widget
@app.route('/styles.css')
def root_styles():
    """Serve widget CSS from root domain"""
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'web-widget'),
        'styles.css'
    )

@app.route('/script.js')
def root_script():
    """Serve widget JavaScript from root domain"""
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'web-widget'),
        'script.js'
    )

@app.route('/avatar2.jpg')
def avatar_image():
    """Serve avatar image from root domain"""
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'web-widget'),
        'avatar2.jpg'
    )

if __name__ == '__main__':
    db.init_db()
    port = int(os.getenv('PORT', 3000))
    api_status = "YES" if GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_') else "NO (Check .env file!)"
    print(f"\n[START] Spectal Chatbot API starting on http://localhost:{port}")
    print(f"[API KEY] Groq API configured: {api_status}")
    print(f"[ENDPOINT] Chat endpoint: http://localhost:{port}/api/chat")
    print(f"[FRONTEND] Frontend URL CORS: {frontend_url}\n")
    
    # Run in production mode with debug=False by default unless explicitly enabled
    is_debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    if not is_debug:
        print("[INFO] Running in PRODUCTION mode (Waitress/Gunicorn recommended)")
    app.run(host='0.0.0.0', port=port, debug=is_debug)