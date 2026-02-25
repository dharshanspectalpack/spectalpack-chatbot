# 🔧 FIX PRIORITY CHECKLIST (One by One)

## 🔴 **PHASE 1: CRITICAL SECURITY (MUST DO FIRST - Days 1-2)**

### ✅ **FIX #1: REMOVE EXPOSED CREDENTIALS FROM `.env`** 
**Severity:** 🔴 CRITICAL  
**File:** `backend/.env`  
**Action:** Before I fix code - **YOU** need to:
1. Go to Groq console: https://console.groq.com → Create NEW API Key
2. Go to Railway DB admin → Reset password (generate new)
3. Share ONLY NEW credentials with me (not old ones)

**What needs to happen:**
```env
# I will REMOVE old credentials and put:
GROQ_API_KEY=[PLACEHOLDER - USER WILL SET IN RAILWAY]
MYSQLPASSWORD=[PLACEHOLDER - USER WILL SET IN RAILWAY]
```

**Status:** ⏳ WAITING FOR YOUR NEW CREDENTIALS

---

### ✅ **FIX #2: DISABLE FLASK DEBUG MODE**
**Severity:** 🔴 CRITICAL  
**File:** `backend/app.py` line 573  
**Current:**
```python
app.run(host='0.0.0.0', port=port, debug=True)
```
**Will Change To:**
```python
app.run(host='0.0.0.0', port=port, debug=False)
```
**Status:** ✅ READY TO IMPLEMENT - Want me to fix this?

---

### ✅ **FIX #3: FIX CORS (Lock to your domains)**
**Severity:** 🔴 CRITICAL  
**Files:** `backend/.env` + `backend/app.py` line 96  
**What needs to change:**
```env
# Current: FRONTEND_URL=*
# New: FRONTEND_URL=https://chatbot.spectalpack.com,https://admin.spectalpack.com
```
**Status:** ✅ READY - But need YOUR domain names. What are they?

---

### ✅ **FIX #4: FIX WEAK ADMIN AUTH (Require env vars)**
**Severity:** 🔴 CRITICAL  
**File:** `backend/app.py` lines 21-34  
**Current:** Falls back to `admin` / `1`  
**Will Change To:** **FAIL startup if credentials missing** (force admin to set them)  
**New env vars needed:**
```env
ADMIN_USERNAME=set_your_username_here
ADMIN_PASSWORD=set_your_16char_password_here
```
**Status:** ✅ READY - Want me to implement?

---

### ✅ **FIX #5: PROTECT UNPROTECTED ENDPOINTS** (Authorization checks)
**Severity:** 🔴 CRITICAL  
**Files:** `backend/app.py` lines 358-398 (chat history) + 404-422 (delete message)  
**Problem:** Anyone can access any user's chat history  
**Solution:** Add ownership verification  
**Status:** ✅ READY - Want me to fix?

---

## 🟠 **PHASE 2: HIGH-PRIORITY (Days 2-3)**

### ✅ **FIX #6: REMOVE DUPLICATE DB FUNCTIONS**
**Severity:** 🟠 HIGH  
**File:** `backend/db_railway.py` lines 469-510  
**Action:** Delete duplicate definitions  
**Status:** ✅ READY - Want me to delete?

---

### ✅ **FIX #7: FIX EMAIL VALIDATION (Accept all emails, not just Gmail)**
**Severity:** 🟠 HIGH  
**File:** `frontend/web-widget/script.js` line 315  
**Current:**
```javascript
const emailRegex = /^[^\s@]+@gmail\.com$/i;  // ❌ Only Gmail
```
**New:**
```javascript
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;  // ✅ Any email
```
**Status:** ✅ READY - Want me to fix?

---

### ✅ **FIX #8: REMOVE HARDCODED LOCALHOST URLs**
**Severity:** 🟠 HIGH  
**Files:** 
- `frontend/web-widget/script.js` line 5
- `frontend/admin-panel/script.js` line 1  
**Current:** `const API_BASE = "http://localhost:3000/api";`  
**New:** Will use production domain instead  
**Status:** ✅ READY - Need YOUR production base URL (e.g., https://api.spectalpack.com)

---

### ✅ **FIX #9: REMOVE DUPLICATE FLASK APP INIT**
**Severity:** 🟠 HIGH  
**File:** `backend/app.py` lines 15 & 83  
**Action:** Keep line 15, delete line 83  
**Status:** ✅ READY - Want me to delete?

---

### ✅ **FIX #10: FIX ERROR MESSAGE LEAKAGE**
**Severity:** 🟠 HIGH  
**File:** `backend/app.py` (multiple locations with `f"Internal server error: {str(e)}"`)  
**Action:** Return generic message instead, log details server-side  
**Status:** ✅ READY - Want me to fix?

---

## 🟡 **PHASE 3: MEDIUM-PRIORITY (Days 3-4)**

### ✅ **FIX #11: ADD INPUT VALIDATION**
**Severity:** 🟡 MEDIUM  
**Files:** `backend/app.py` (user creation)  
**Action:** Limit name to 2-100 chars, validate email format  
**Status:** ✅ READY

---

### ✅ **FIX #12: ADD SECURITY HEADERS**
**Severity:** 🟡 MEDIUM  
**File:** `backend/app.py` (after CORS setup)  
**Action:** Add X-Frame-Options, CSP, HSTS headers  
**Status:** ✅ READY

---

### ✅ **FIX #13: SWITCH RATE LIMITER TO REDIS** (Optional - if you have Redis)
**Severity:** 🟡 MEDIUM  
**File:** `backend/app.py` line 93  
**Requires:** Redis server running  
**Status:** ⏳ WAITING - Do you want to use Redis or keep memory-based?

---

## 📁 **PHASE 4: CLEANUP (Days 4-5)**

### ✅ **DELETE DEV-ONLY FILES**
- `backend/test_connection.py`
- `backend/test_db_connection.py`
- `backend/view_history.py`
- `backend/backend.log`

---

## 📋 **WHAT I NEED FROM YOU BEFORE STARTING:**

1. **New Groq API Key** (rotated from current exposed one)
2. **New Database Password** (rotated from current exposed one)
3. **Your Production Domain** (e.g., `https://chatbot.spectalpack.com`)
4. **Admin Username** (what you want to be called)
5. **Admin Password** (strong 16+ char password)
6. **Do you want Redis?** (for distributed rate limiting)

---

## 🎯 **RECOMMENDED FIX ORDER:**

1. **FIX #1:** Get new credentials from you
2. **FIX #2:** Disable debug mode (quick)
3. **FIX #3:** Lock CORS (quick)
4. **FIX #4:** Require admin auth (quick)
5. **FIX #5:** Protect endpoints (medium)
6. **FIX #6:** Remove duplicates (quick)
7. **FIX #7:** Fix email validation (quick)
8. **FIX #8:** Fix localhost URLs (quick)
9. **FIX #9:** Remove duplicate app init (quick)
10. **FIX #10:** Fix error leakage (medium)
11. Delete dev files

---

**👇 PLEASE PROVIDE (copy-paste below):**

```
1. New Groq API Key: [YOUR_NEW_KEY]
2. New Database Password: [YOUR_NEW_PASSWORD]
3. Production Domain: [YOUR_DOMAIN.COM]
4. Admin Username: [YOUR_USERNAME]
5. Admin Password: [YOUR_PASSWORD]
6. Use Redis? (yes/no): 
```

**Once you provide these, I'll start FIX #1-#10 immediately!**