# 📋 WHERE TO PASTE YOUR CREDENTIALS - Step by Step

---

## 🎯 WHAT YOU NEED TO PROVIDE (Copy from here)

Fill in these 5 items with YOUR actual values:

```
1. New Groq API Key:          [PASTE HERE]
2. New Database Password:     [PASTE HERE]
3. Production Domain 1:       [PASTE HERE] (e.g., chatbot.spectalpack.com)
4. Production Domain 2:       [PASTE HERE] (e.g., admin.spectalpack.com)
5. Admin Username:            [PASTE HERE] (e.g., admin_prod)
6. Admin Password:            [PASTE HERE] (16+ characters, strong password)
```

---

## 📍 WHERE EACH VALUE GOES IN YOUR PROJECT

### **LOCATION 1: File `backend/.env`**
**FILE PATH:** `c:\Users\DELL\Desktop\Spectalpack Chatbot\backend\.env`

**Current content:**
```env
PORT=3000
GROQ_API_KEY=gsk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
FRONTEND_URL=*

MYSQLHOST=maglev.proxy.rlwy.net
MYSQLUSER=root
MYSQLPASSWORD=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
MYSQLPORT=16299
MYSQLDATABASE=railway
```

**What to change:**

1️⃣ **Line 2 - GROQ_API_KEY**
```env
GROQ_API_KEY=gsk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
                 ↓↓↓ REPLACE THIS ENTIRE KEY ↓↓↓
GROQ_API_KEY=[PASTE_YOUR_NEW_GROQ_API_KEY_HERE]
```

**Example:**
```env
GROQ_API_KEY=gsk_abc123def456xyz789...
```

---

2️⃣ **Line 3 - FRONTEND_URL**
```env
FRONTEND_URL=*
           ↓ REPLACE * WITH YOUR DOMAINS ↓
FRONTEND_URL=https://chatbot.spectalpack.com,https://admin.spectalpack.com
```

**Example:**
```env
FRONTEND_URL=https://chatbot.spectalpack.com,https://admin.spectalpack.com
```

---

3️⃣ **Line 7 - MYSQLPASSWORD**
```env
MYSQLPASSWORD=hmEKevPzRryEethGOTHGGphPvKXSWxfB
              ↓↓↓ REPLACE THIS PASSWORD ↓↓↓
MYSQLPASSWORD=[PASTE_YOUR_NEW_DB_PASSWORD_HERE]
```

**Example:**
```env
MYSQLPASSWORD=Your$ecure#Pass123
```

---

### **LOCATION 2: Environment Variables (for startup)**

When you start the app, set these environment variables:

**On Windows (PowerShell):**
```powershell
$env:ADMIN_USERNAME="your_admin_username"
$env:ADMIN_PASSWORD="Your$ecure#Pass16Chars"
$env:ENVIRONMENT="production"
```

**On Linux/Mac (Bash):**
```bash
export ADMIN_USERNAME=your_admin_username
export ADMIN_PASSWORD=Your$ecure#Pass16Chars
export ENVIRONMENT=production
```

**On Railway/Cloud Platform:**
Add these in the environment variables section:
```
ADMIN_USERNAME = your_admin_username
ADMIN_PASSWORD = Your$ecure#Pass16Chars
ENVIRONMENT = production
GROQ_API_KEY = gsk_your_key
MYSQLPASSWORD = your_db_password
```

---

## 📝 COMPLETE EXAMPLE `.env` FILE After Filling In

**Create/Edit:** `backend/.env`

```env
PORT=3000
GROQ_API_KEY=gsk_abc123def456xyz789abc123def456
FRONTEND_URL=https://chatbot.spectalpack.com,https://admin.spectalpack.com

MYSQLHOST=maglev.proxy.rlwy.net
MYSQLUSER=root
MYSQLPASSWORD=MyNewSecurePassword123!
MYSQLPORT=16299
MYSQLDATABASE=railway

ENVIRONMENT=production
ADMIN_USERNAME=admin_prod
ADMIN_PASSWORD=AdminSecurePass2024!
```

---

## ✅ STEP-BY-STEP INSTRUCTIONS

### **STEP 1: Get New Groq API Key**
1. Go to: https://console.groq.com
2. Log in to your account
3. Click "API Keys" section
4. Click "Create New Key"
5. Copy the key (starts with `gsk_`)
6. **Save it** - you'll paste it in `.env`

---

### **STEP 2: Get New Database Password**
1. Go to: https://railway.app
2. Log in to your account
3. Click on your Spectalpack project
4. Click on the MySQL plugin/database
5. Click "Settings" or "PostgreSQL/MySQL"
6. Go to "Credentials" section
7. Click "Reset Password" or change password
8. Copy new password
9. **Save it** - you'll paste it in `.env`

---

### **STEP 3: Decide Your Domains**
Think about where you want to host each:

**Option A: Same domain, different paths**
```env
FRONTEND_URL=https://spectalpack.com
```

**Option B: Different subdomains**
```env
FRONTEND_URL=https://chat.spectalpack.com,https://admin.spectalpack.com
```

**Option C: Different domains**
```env
FRONTEND_URL=https://chatbot.mycompany.com,https://admin.mycompany.com
```

**Save your chosen domains** - you'll paste them in `.env`

---

### **STEP 4: Create Admin Credentials**
Choose a strong username and password:

**Username:** (examples)
- `admin_prod`
- `spectal_admin`
- `admin_2024`

**Password:** (must be 16+ characters)
- `AdminSecure2024!@#`
- `SpectalPack#Prod123`
- `MyStrong$Pass2024`

**Save both** - you'll need them when starting the app

---

## 🔑 CHECKLIST BEFORE PASTING

Before you give me the credentials, verify:

- [ ] You have rotated the old Groq API key (old one is compromised)
- [ ] You have a NEW Groq API key (starts with `gsk_`)
- [ ] You have rotated the old DB password
- [ ] You have a NEW database password
- [ ] You know your production domain(s)
- [ ] You created a strong admin username (8+ chars)
- [ ] You created a strong admin password (16+ chars, has uppercase, lowercase, numbers, symbols)

---

## 📬 WHAT TO REPLY WITH

Once you have all 6 items, reply to me with:

```
GROQ_API_KEY: gsk_your_key_here
DB_PASSWORD: your_new_db_password
FRONTEND_URL: https://domain1.com,https://domain2.com
ADMIN_USERNAME: your_admin_username
ADMIN_PASSWORD: Your$ecure#Password123
ENVIRONMENT: production
```

**OR just paste the complete `.env` file content** - I'll use it directly.

---

## ⚠️ IMPORTANT SAFETY NOTES

### ✅ DO:
- Use STRONG passwords (16+ chars with symbols)
- Generate NEW keys (don't reuse old ones)
- Rotate credentials regularly in production
- Keep `.env` ONLY on your local machine (never in git)

### ❌ DON'T:
- Share your credentials in plaintext on chat (use secure method)
- Reuse same password for admin and database
- Use simple passwords like "password123"
- Commit `.env` to GitHub

---

## 🚀 ONCE YOU REPLY WITH CREDENTIALS

I will:
1. ✅ Update `backend/.env` with your credentials
2. ✅ Lock CORS to your domains
3. ✅ Create `.env.example` (template without secrets)
4. ✅ Create a deployment guide for Railway/AWS
5. ✅ Give you final production readiness report

---

**YOU'RE READY TO PROVIDE CREDENTIALS?** 👇

Just reply with your 6 items and I'll finish everything!
