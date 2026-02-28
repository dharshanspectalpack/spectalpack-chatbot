// ============================================
// GLOBAL VARIABLES
// ============================================
// Dynamically detect API base URL for localhost (dev) or production domain
const API_BASE = window.location.origin + "/api";

let chatHistory = [];
let isLoading = false;
let typingComplete = false;
let typingShown = false;
let userInfo = null; // Store user info for personalized responses (if needed)

// Flag to track if user info has been collected
let pendingInitialMessage = "";
// ============================================
// TYPING ANIMATION POPUP
// ============================================
function showTypingAnimation() {
  if (typingShown) return; // Prevent multiple shows
  typingShown = true;

  const typingPopup = document.getElementById("typingPopup");
  const typingElement = document.getElementById("typingText");
  const subtitle = document.querySelector(".typing-subtitle");

  if (!typingPopup || !typingElement) {
    console.error("Typing elements not found!");
    return;
  }

  // Show the popup
  typingPopup.classList.add("show");

  const text = "Spectal Pack";
  const letterClasses = [
    "letter-s",
    "letter-p",
    "letter-e",
    "letter-c",
    "letter-t",
    "letter-a",
    "letter-l",
    "letter-space",
    "letter-p2",
    "letter-a2",
    "letter-c2",
    "letter-k",
  ];
  let index = 0;

  // Clear any existing content
  typingElement.innerHTML = "";

  // Start typing animation
  setTimeout(() => {
    const typeWriter = () => {
      if (index < text.length) {
        const letter = text.charAt(index);
        const span = document.createElement("span");
        span.className = letterClasses[index];
        span.textContent = letter === " " ? "\u00A0" : letter; // Use non-breaking space for space character
        typingElement.appendChild(span);
        index++;
        setTimeout(typeWriter, 120); // Typing speed
      } else {
        // Typing complete - show subtitle
        setTimeout(() => {
          if (subtitle) {
            subtitle.style.animation = "subtitleFadeIn 0.6s ease-out forwards";
          }

          // Hide popup after showing for a moment
          setTimeout(() => {
            typingPopup.classList.remove("show");
            typingPopup.classList.add("hide");
            typingComplete = true;
          }, 1500); // UPDATED - Show complete text for 1.5 seconds
        }, 600);
      }
    };

    typeWriter();
  }, 200); // UPDATED - Reduced delay so animation starts faster
}

// Show typing animation when page loads
function initializeTypingAnimation() {
  setTimeout(() => {
    showTypingAnimation();
  }, 500); // Faster initial show

  setTimeout(() => {
    if (!typingShown) {
      typingShown = false; // Reset flag
      showTypingAnimation();
    }
  }, 2000);

  // Optional: Also show when hovering near chat avatar (only if not already shown)
  const chatAvatar = document.getElementById("chatAvatar");
  let hoverTimeout;

  chatAvatar.addEventListener("mouseenter", () => {
    if (!typingShown && !typingComplete) {
      clearTimeout(hoverTimeout);
      hoverTimeout = setTimeout(() => {
        showTypingAnimation();
      }, 500);
    }
  });

  chatAvatar.addEventListener("mouseleave", () => {
    clearTimeout(hoverTimeout);
  });
}

// ============================================
// INITIAL SETUP
// ============================================
document.addEventListener("DOMContentLoaded", function () {
  // Initialize typing animation
  initializeTypingAnimation();

  // Get elements
  const chatAvatar = document.getElementById("chatAvatar");
  const chatContainer = document.getElementById("chatContainer");
  const closeBtn = document.getElementById("closeBtn");
  const userInput = document.getElementById("userInput");

  // After bounce-in completes (delay 0.3s + duration 0.5s = ~0.9s), switch to gentle float
  setTimeout(() => {
    if (!chatAvatar.classList.contains("hidden")) {
      chatAvatar.classList.add("float-idle");
    }
  }, 950);

  // Avatar click: toggle chat
  chatAvatar.addEventListener("click", function (e) {
    e.stopPropagation();
    chatContainer.classList.toggle("open");

    // if opening chat
    if (chatContainer.classList.contains("open")) {
      chatAvatar.classList.add("hidden");         // hide avatar while chat is open
      chatAvatar.classList.remove("float-idle");  // pause float while hidden

      // Close typing animation popup immediately
      const typingPopup = document.getElementById("typingPopup");
      if (typingPopup && typingPopup.classList.contains("show")) {
        typingPopup.classList.remove("show");
        typingPopup.classList.add("hide");
      }

      // Focus input
      setTimeout(() => {
        userInput.focus();
      }, 100);
    } else {
      // Chat closed — show avatar again
      chatAvatar.classList.remove("hidden");
      // Resume gentle float after reappearing
      setTimeout(() => {
        if (!chatAvatar.classList.contains("hidden")) {
          chatAvatar.classList.add("float-idle");
        }
      }, 400);
    }
  });

  // Close button click
  closeBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    chatContainer.classList.remove("open");
    chatAvatar.classList.remove("hidden"); // show avatar again
    setTimeout(() => {
      if (!chatAvatar.classList.contains("hidden")) {
        chatAvatar.classList.add("float-idle");
      }
    }, 400);
  });

  // Wire up Enter key on the input (replaces removed inline onkeypress)
  userInput.addEventListener("keypress", handleKeyPress);

  // Menu button click - toggle dropdown
  const menuBtn = document.getElementById("menuBtn");
  const dropdownMenu = document.getElementById("dropdownMenu");

  if (menuBtn && dropdownMenu) {
    menuBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      dropdownMenu.classList.toggle("show");
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", function (e) {
      if (
        dropdownMenu.classList.contains("show") &&
        !menuBtn.contains(e.target) &&
        !dropdownMenu.contains(e.target)
      ) {
        dropdownMenu.classList.remove("show");
      }
    });
  }

  //  FIXED: Changed ID from 'refreshBtn' to 'refreshChatBtn' to match HTML
  const refreshChatBtn = document.getElementById("refreshChatBtn");
  if (refreshChatBtn) {
    refreshChatBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      if (dropdownMenu) dropdownMenu.classList.remove("show"); // Close menu after action
      refreshChat();
    });
  }

  //  FIXED: Changed ID from 'clearBtn' to 'clearChatBtn' to match HTML
  const clearChatBtn = document.getElementById("clearChatBtn");
  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      if (dropdownMenu) dropdownMenu.classList.remove("show"); // Close menu after action
      clearChat();
    });
  }

  // ---- Quick Action Buttons (left of input) ----
  const quickSampleKitBtn = document.getElementById("quickSampleKitBtn");
  const quickQuotationBtn = document.getElementById("quickQuotationBtn");
  if (quickSampleKitBtn) quickSampleKitBtn.addEventListener("click", (e) => { e.stopPropagation(); openSampleKitPanel(); });
  if (quickQuotationBtn) quickQuotationBtn.addEventListener("click", (e) => { e.stopPropagation(); openQuotationPanel(); });

  // ---- Welcome Card CTA Buttons ----
  const welcomeSampleKitBtn = document.getElementById("welcomeSampleKitBtn");
  const welcomeQuotationBtn = document.getElementById("welcomeQuotationBtn");
  if (welcomeSampleKitBtn) welcomeSampleKitBtn.addEventListener("click", (e) => { e.stopPropagation(); hideWelcomeCard(); openSampleKitPanel(); });
  if (welcomeQuotationBtn) welcomeQuotationBtn.addEventListener("click", (e) => { e.stopPropagation(); hideWelcomeCard(); openQuotationPanel(); });

  // ---- Hide welcome card when user starts typing ----
  userInput.addEventListener("input", hideWelcomeCard);

  // ---- Close form panels ----
  const closeSampleKitPanel = document.getElementById("closeSampleKitPanel");
  const closeQuotationPanel = document.getElementById("closeQuotationPanel");
  const formPanelOverlay = document.getElementById("formPanelOverlay");
  if (closeSampleKitPanel) closeSampleKitPanel.addEventListener("click", () => closeSampleKitPanelFn());
  if (closeQuotationPanel) closeQuotationPanel.addEventListener("click", () => closeQuotationPanelFn());
  if (formPanelOverlay) formPanelOverlay.addEventListener("click", () => { closeSampleKitPanelFn(); closeQuotationPanelFn(); });

  // Click outside chat to close
  document.addEventListener("click", function (e) {
    if (
      chatContainer.classList.contains("open") &&
      !chatContainer.contains(e.target) &&
      !chatAvatar.contains(e.target) &&
      !document.getElementById("sampleKitPanel").contains(e.target) &&
      !document.getElementById("quotationPanel").contains(e.target)
    ) {
      chatContainer.classList.remove("open");
      chatAvatar.classList.remove("hidden"); // show avatar again
      setTimeout(() => {
        if (!chatAvatar.classList.contains("hidden")) {
          chatAvatar.classList.add("float-idle");
        }
      }, 400);
    }
  });

  // Load user info with validation
  loadUserInfo();

  // load chat history if available, otherwise start with welcome message
  const chatMessages = document.getElementById("chatMessages");
  if (userInfo && userInfo.session_id) {
    // Show loading
    chatMessages.innerHTML = '<div class="loading"></div>';

    // Fetch from Railway DB
    fetch(`${API_BASE}/chat/history/${userInfo.session_id}?user_id=${userInfo.id}`)
      .then((res) => {
        if (res.status === 404) {
          throw new Error("invalid_session");
        }
        return res.json();
      })
      .then((data) => {
        if (data.success && data.history && data.history.length > 0) {
          chatHistory = data.history.map((msg) => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
          }));
          renderChatHistory();
        } else {
          chatHistory = [];
          chatMessages.innerHTML = '';
          addMessage(
            `Hello again, ${userInfo.name}! How can I assist you today?`,
            "bot",
          );
        }
      })
      .catch((err) => {
        if (err.message === "invalid_session") {
          console.warn("Session expired or database reset. Clearing local cache.");
          localStorage.removeItem("userInfo");
          localStorage.removeItem("userId");
          localStorage.removeItem("sessionId");
          userInfo = null;
          chatHistory = [];
          
          // Clear loading indicator
          chatMessages.innerHTML = "";
          addWelcomeMessage();
          return;
        }

        console.error("Failed to load chat history", err);
        chatHistory = [];
        chatMessages.innerHTML = '';
        addMessage(
          `Hello again, ${userInfo.name}! How can I assist you today?`,
          "bot",
        );
      });
  } else {
    chatHistory = [];
    addWelcomeMessage();
  }
});

// ============================================
// ADD WELCOME MESSAGE
// ============================================
function addWelcomeMessage() {
  setTimeout(() => {
    addMessage("Hello! 👋 Welcome to Spectal Pack. I'm your AI assistant. How can I assist you today?", "bot");
  }, 1000);
}

// ============================================
// USER INFO COLLECTION - FORM
// ============================================
function startUserInfoCollection() {
  const formHtml = `
    <p style="margin-bottom: 15px;">To provide you with a customized packaging solutions, could you please tell me a bit about yourself?</p>
    <form id="user-info-form" class="chat-form" onsubmit="submitUserInfoForm(event)">
      <input type="text" id="formName" placeholder="Your Name" required minlength="2">
      <input type="text" id="formCompany" placeholder="Company Name" required minlength="3">
      <input type="email" id="formEmail" placeholder="Email Address (e.g. name@gmail.com)" required>
      <div id="formError" class="form-error">Please enter a valid email format.</div>
      <button type="submit">Start Chatting</button>
    </form>
  `;
  addMessage(formHtml, "bot");
}

function submitUserInfoForm(event) {
  event.preventDefault();

  const nameInput = document.getElementById("formName").value.trim();
  const companyInput = document.getElementById("formCompany").value.trim();
  const emailInput = document.getElementById("formEmail").value.trim();
  const errorDiv = document.getElementById("formError");

  // Validate email format (any valid email, not just Gmail)
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(emailInput)) {
    errorDiv.textContent = "Please enter a valid email address.";
    errorDiv.style.display = "block";
    return;
  }
  errorDiv.style.display = "none";

  const userData = {
    name: nameInput,
    company: companyInput,
    email: emailInput,
  };

  // Convert the form to basic text so it doesn't stay interactive in history
  const contentDiv = event.target.closest('.message-content');
  if (contentDiv) {
    contentDiv.innerHTML = `<p>To provide personalized packaging solutions and assist you properly, could you please tell me a bit about yourself?</p><p style="color:#666; font-size:12px; margin-top:10px;"><em>[Form submitted by ${nameInput}]</em></p>`;
  }

  // Send to backend to create user
  fetch(`${API_BASE}/user`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(userData),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Save user info with ID
        userInfo = {
          ...userData,
          id: data.user_id,
          session_id: data.session_id,
        };
        localStorage.setItem("userInfo", JSON.stringify(userInfo));
        localStorage.setItem("userId", data.user_id);
        localStorage.setItem("sessionId", data.session_id);

        if (pendingInitialMessage) {
          chatHistory.push({
            role: "user",
            content: pendingInitialMessage,
            timestamp: new Date().toISOString()
          });
          pendingInitialMessage = "";
          getAIResponse();
        } else {
          addMessage(
            `Perfect! Thank you ${userInfo.name} from ${userInfo.company}. How can I assist you with your packaging needs today?`,
            "bot",
          );
        }
      } else {
        addMessage(`⚠️ ${data.error}. Continuing without history.`, "bot");
        userInfo = { ...userData };
        localStorage.setItem("userInfo", JSON.stringify(userInfo));
        if (pendingInitialMessage) {
          chatHistory.push({
            role: "user",
            content: pendingInitialMessage,
            timestamp: new Date().toISOString()
          });
          pendingInitialMessage = "";
          getAIResponse();
        } else {
          addMessage(`Thank you! How can I assist you today?`, "bot");
        }
      }
    })
    .catch((error) => {
      console.error("User Creation failed:", error);
      userInfo = { ...userData };
      localStorage.setItem("userInfo", JSON.stringify(userInfo));
      if (pendingInitialMessage) {
        chatHistory.push({
          role: "user",
          content: pendingInitialMessage,
          timestamp: new Date().toISOString()
        });
        pendingInitialMessage = "";
        getAIResponse();
      } else {
        addMessage(`Thank you! How can I assist you today?`, "bot");
      }
    });
}

function loadUserInfo() {
  const savedUserInfo = localStorage.getItem("userInfo");
  if (savedUserInfo) {
    try {
      const parsedInfo = JSON.parse(savedUserInfo);
      // Validate that it's a real user and not dummy data from old conversational flow
      if (
        !parsedInfo.name ||
        parsedInfo.name.length > 30 ||
        !parsedInfo.email
      ) {
        console.warn("Found corrupt user data, clearing cache.");
        localStorage.removeItem("userInfo");
        userInfo = null;
        return false;
      }
      userInfo = parsedInfo;
      return true;
    } catch (e) {
      console.warn("Could not load user info");
      localStorage.removeItem("userInfo");
      userInfo = null;
      return false;
    }
  }
  return false;
}


// ============================================
// HANDLE KEY PRESS (Enter to send)
// ============================================
function handleKeyPress(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// ============================================
// SEND MESSAGE
// ============================================
async function sendMessage() {
  const userInput = document.getElementById("userInput");
  const message = userInput.value.trim();

  if (!message || isLoading) return;

  // Hide the welcome card when user actually sends a message
  hideWelcomeCard();

  // Validate message length (max 5000 chars - DoS protection)
  if (message.length > 5000) {
    addMessage("⚠️ Message is too long (max 5000 characters).", "bot");
    return;
  }

  // Clear input
  userInput.value = "";

  // Add user message
  addMessage(message, "user");

  // Handle user info collection if active
  if (!userInfo) {
    if (!pendingInitialMessage) {
      pendingInitialMessage = message;
      startUserInfoCollection();
    } else {
      addMessage("Please fill out the form above so I can assist you properly.", "bot");
    }
    return;
  }

  // Save to history list for local render (No longer saving to localStorage)
  chatHistory.push({
    role: "user",
    content: message,
    timestamp: new Date().toISOString(),
  });

  // Get AI response
  await getAIResponse();
}

// ============================================
// GET AI RESPONSE
// ============================================
async function getAIResponse() {
  if (isLoading) return;

  isLoading = true;

  // Add loading indicator
  const loadingMessage = {
    role: "assistant",
    content: '<div class="loading"></div>',
    timestamp: new Date().toISOString(),
  };

  chatHistory.push(loadingMessage);
  addMessage('<div class="loading"></div>', "bot");

  try {
    // Get the last user message (at index -2 since loading is last)
    const userMessage = chatHistory[chatHistory.length - 2].content;

    // Call your backend API
    const body = {
      message: userMessage,
      chatHistory: chatHistory.slice(0, -1), // Exclude loading message
    };

    // Only add user_id if it exists to prevent sending the string "null"
    const userId = localStorage.getItem("userId");
    if (userId) {
      body.user_id = userId;
    }

    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      if (response.status === 429) {
        throw new Error(
          "You are sending messages too fast! Please wait a moment and try again.",
        );
      }
      throw new Error(`API error: ${response.status}`);
    }

    // We will consume the response as a stream instead of a single json block.
    // Remove loading indicator from DOM
    const chatMessages = document.getElementById("chatMessages");
    if (chatMessages && chatMessages.lastElementChild && 
        chatMessages.lastElementChild.innerHTML.includes('<div class="loading"></div>')) {
      chatMessages.lastElementChild.remove();
    }
    chatHistory.pop();

    // Add empty AI response to history
    const botMessage = {
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
    };
    chatHistory.push(botMessage);
    
    // Inject bot message without full screen redraw
    addMessage("", "bot");
    const lastMessageContent =
      chatMessages.lastElementChild.querySelector(".message-content");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");

      // Keep the last partial line in the buffer
      buffer = lines.pop();

      for (const line of lines) {
        if (line.trim() === "") continue;
        if (line.startsWith("data: ")) {
          const dataStr = line.substring(6);
          try {
            const dataObj = JSON.parse(dataStr);
            if (dataObj.error) {
              botMessage.content += `\n**Error:** ${dataObj.error}`;
              lastMessageContent.innerHTML = marked.parse(botMessage.content);
            } else if (dataObj.chunk) {
              botMessage.content += dataObj.chunk;
              lastMessageContent.innerHTML = marked.parse(botMessage.content);
              chatMessages.scrollTop = chatMessages.scrollHeight;
            } else if (dataObj.done) {
              // History saved to DB automatically by backend.
              // We'll fetch updated history to sync message IDs.
            }
          } catch (e) {
            // Ignore parse errors on incomplete chunks
          }
        }
      }
    }
  } catch (error) {
    console.error("Error:", error);

    // Remove loading indicator from DOM
    const chatMessages = document.getElementById("chatMessages");
    if (chatMessages && chatMessages.lastElementChild && 
        chatMessages.lastElementChild.innerHTML.includes('<div class="loading"></div>')) {
      chatMessages.lastElementChild.remove();
    }
    chatHistory.pop();

    // Show error message (generic - don't reveal backend URL)
    const errorMessage = {
      role: "assistant",
      content: `⚠️ Sorry, I encountered an error while processing your request. Please try again in a moment or contact support if the issue persists.`,
      timestamp: new Date().toISOString(),
    };

    chatHistory.push(errorMessage);
    addMessage(errorMessage.content, "bot");
  } finally {
    isLoading = false;
    
    // Silently fetch updated history to get message IDs for freshly generated messages
    if (userInfo && userInfo.session_id) {
      fetch(`${API_BASE}/chat/history/${userInfo.session_id}?user_id=${userInfo.id}`)
        .then(res => {
          if (res.status === 404) throw new Error("invalid_session");
          return res.json();
        })
        .then(data => {
          if(data.success && data.history) {
             chatHistory = data.history.map((msg) => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                timestamp: msg.timestamp,
             }));
          }
        }).catch(err => {
          if (err.message === "invalid_session") {
            console.warn("Session expired during chat. Next refresh will reset forms.");
            localStorage.removeItem("userInfo");
            localStorage.removeItem("userId");
            localStorage.removeItem("sessionId");
            userInfo = null;
          } else {
            console.error("Could not sync history", err);
          }
        });
    }
  }
}

// ============================================
// SANITIZE HTML (Prevent XSS Attacks)
// ============================================
function sanitizeHTML(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
// ============================================
// ADD MESSAGE TO CHAT UI
// ============================================
function addMessage(content, sender) {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;


  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${sender}-message`;

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";

  // Check if content is HTML (loading spinner) or plain text
  if (
    content.includes('<div class="loading"></div>') ||
    content.includes("<form")
  ) {
    contentDiv.innerHTML = content; // Render raw HTML
  } else if (sender === "bot") {
    contentDiv.innerHTML = marked.parse(content); // Use marked.js for bot responses
  } else {
    contentDiv.innerHTML = `<p>${sanitizeHTML(content)}</p>`; // Sanitize user input
  }

  const timeSpan = document.createElement("span");
  timeSpan.className = "message-time";
  timeSpan.textContent = formatTime(new Date());

  messageDiv.appendChild(contentDiv);
  messageDiv.appendChild(timeSpan);

  chatMessages.appendChild(messageDiv);

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ============================================
// RENDER CHAT HISTORY
// ============================================
function renderChatHistory() {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;

  chatMessages.innerHTML = "";

  chatHistory
    .filter(msg => !msg.content.includes('<div class="loading"></div>')) // skip spinner entries
    .forEach((message, index) => {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${message.role === "user" ? "user-message" : "bot-message"}`;

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";

    // Check if content is HTML (loading spinner) or plain text
    if (
      message.content.includes('<div class="loading"></div>') ||
      message.content.includes("<form")
    ) {
      contentDiv.innerHTML = message.content;
    } else if (message.role === "assistant" || message.role === "bot") {
      contentDiv.innerHTML = marked.parse(message.content);
    } else {
      contentDiv.innerHTML = `<p>${sanitizeHTML(message.content)}</p>`; // Sanitize user input
    }

    const timeSpan = document.createElement("span");
    timeSpan.className = "message-time";
    timeSpan.textContent = formatTime(new Date(message.timestamp));

    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeSpan);

    chatMessages.appendChild(messageDiv);
  });

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ============================================
// FORMAT TIME
// ============================================
function formatTime(date) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const messageDate = new Date(date);

  if (messageDate.toDateString() === today.toDateString()) {
    return messageDate.toLocaleTimeString('en-IN', {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Kolkata"
    });
  }

  return messageDate.toLocaleDateString('en-IN', {
      timeZone: "Asia/Kolkata"
  });
}



// ============================================
// REFRESH CHAT BUTTON
// ============================================
function refreshChat() {
  //check if we need to collect user info
  if (!userInfo) {
    //clear chat for clean collection flow
    chatHistory = [];
    const chatMessages = document.getElementById("chatMessages");
    if (chatMessages) chatMessages.innerHTML = "";

    //start user info collection properly with welcome
    addWelcomeMessage();
  } else {
    // Clear chat locally and create a new session next time user sends a message
    chatHistory = [];
    localStorage.removeItem("chatHistory");
    localStorage.removeItem("sessionId");  // ✅ Force new session on next message
    // Update userInfo in memory (keep name/email/id but clear session)
    if (userInfo) {
      userInfo.session_id = null;
      localStorage.setItem("userInfo", JSON.stringify(userInfo));
    }
    const chatMessages = document.getElementById("chatMessages");
    if (chatMessages) chatMessages.innerHTML = "";
    addMessage(`Hello ${userInfo.name}! How can I help you today?`, "bot");
  }
}

// ============================================
// CLEAR CHAT BUTTON
// ============================================
function clearChat() {
  // Show confirmation dialog
  const confirmed = confirm(
    "Are you sure you want to clear the chat history? This action cannot be undone.",
  );

  if (!confirmed) return;

  // Clear chat history from memory
  chatHistory = [];
  localStorage.removeItem("userInfo");
  localStorage.removeItem("userId");
  localStorage.removeItem("sessionId");
  userInfo = null;

  const chatMessages = document.getElementById("chatMessages");
  if (chatMessages) chatMessages.innerHTML = "";

  showWelcomeCard();
  addWelcomeMessage();
}

// ============================================
// WELCOME CARD
// ============================================
let welcomeCardHidden = false;

function hideWelcomeCard() {
  if (welcomeCardHidden) return;
  welcomeCardHidden = true;
  const card = document.getElementById("welcomeCard");
  if (card) card.classList.add("hidden");
  // Reveal the compact quick-action buttons now that user is chatting
  const qaRow = document.getElementById("quickActionRow");
  if (qaRow) qaRow.classList.remove("hidden");
}

function showWelcomeCard() {
  welcomeCardHidden = false;
  const card = document.getElementById("welcomeCard");
  if (card) card.classList.remove("hidden");
  // Hide the quick-action row again when resetting to welcome state
  const qaRow = document.getElementById("quickActionRow");
  if (qaRow) qaRow.classList.add("hidden");
}

// ============================================
// SAMPLE KIT PANEL
// ============================================
function openSampleKitPanel() {
  const panel = document.getElementById("sampleKitPanel");
  const overlay = document.getElementById("formPanelOverlay");
  if (panel) panel.classList.add("open");
  if (overlay) overlay.classList.add("visible");
}

function closeSampleKitPanelFn() {
  const panel = document.getElementById("sampleKitPanel");
  const overlay = document.getElementById("formPanelOverlay");
  if (panel) panel.classList.remove("open");
  // Only hide overlay if both panels are closed
  const quotPanel = document.getElementById("quotationPanel");
  if (overlay && !quotPanel.classList.contains("open")) overlay.classList.remove("visible");
}

async function submitSampleKit(event) {
  event.preventDefault();
  const btn = document.getElementById("sk-submit-btn");
  const errorDiv = document.getElementById("sk-error");
  errorDiv.style.display = "none";

  // Collect selected products
  const checkedProducts = Array.from(
    document.querySelectorAll('#sampleKitForm input[name="products"]:checked')
  ).map(cb => cb.value).join(", ");

  const payload = {
    name:     document.getElementById("sk-name").value.trim(),
    company:  document.getElementById("sk-company").value.trim(),
    email:    document.getElementById("sk-email").value.trim(),
    phone:    document.getElementById("sk-phone").value.trim(),
    products: checkedProducts,
    quantity: document.getElementById("sk-quantity").value.trim(),
    address:  document.getElementById("sk-address").value.trim(),
  };

  if (!payload.name || !payload.email) {
    errorDiv.textContent = "Name and email are required.";
    errorDiv.style.display = "block";
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span>Sending...</span>';

  try {
    const res = await fetch(`${API_BASE}/sample-kit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.success) {
      closeSampleKitPanelFn();
      document.getElementById("sampleKitForm").reset();
      addMessage(
        `✅ **Sample Kit Request Received!**\n\nThank you ${payload.name}! We've received your sample kit request and will ship it to you shortly. Our team will contact you at **${payload.email}** to confirm details.`,
        "bot"
      );
    } else {
      errorDiv.textContent = data.error || "Failed to submit. Please try again.";
      errorDiv.style.display = "block";
    }
  } catch (err) {
    errorDiv.textContent = "Network error. Please try again.";
    errorDiv.style.display = "block";
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Send Sample Kit Request</span>';
  }
}

// ============================================
// QUOTATION PANEL
// ============================================
function openQuotationPanel() {
  const panel = document.getElementById("quotationPanel");
  const overlay = document.getElementById("formPanelOverlay");
  if (panel) panel.classList.add("open");
  if (overlay) overlay.classList.add("visible");
}

function closeQuotationPanelFn() {
  const panel = document.getElementById("quotationPanel");
  const overlay = document.getElementById("formPanelOverlay");
  if (panel) panel.classList.remove("open");
  const kitPanel = document.getElementById("sampleKitPanel");
  if (overlay && !kitPanel.classList.contains("open")) overlay.classList.remove("visible");
}

async function submitQuotation(event) {
  event.preventDefault();
  const btn = document.getElementById("qt-submit-btn");
  const errorDiv = document.getElementById("qt-error");
  errorDiv.style.display = "none";

  const payload = {
    name:         document.getElementById("qt-name").value.trim(),
    company:      document.getElementById("qt-company").value.trim(),
    email:        document.getElementById("qt-email").value.trim(),
    phone:        document.getElementById("qt-phone").value.trim(),
    product_type: document.getElementById("qt-product-type").value,
    size:         document.getElementById("qt-size").value.trim(),
    material:     document.getElementById("qt-material").value,
    quantity:     document.getElementById("qt-quantity").value.trim(),
    timeline:     document.getElementById("qt-timeline").value,
    notes:        document.getElementById("qt-notes").value.trim(),
  };

  if (!payload.name || !payload.company || !payload.email) {
    errorDiv.textContent = "Name, company and email are required.";
    errorDiv.style.display = "block";
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span>Sending...</span>';

  try {
    const res = await fetch(`${API_BASE}/quotation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.success) {
      closeQuotationPanelFn();
      document.getElementById("quotationForm").reset();
      addMessage(
        `✅ **Quotation Request Received!**\n\nThank you ${payload.name}! We've received your quotation request for **${payload.product_type || 'packaging'}**. Our sales team will prepare a custom quote and contact you at **${payload.email}** within 24 hours.`,
        "bot"
      );
    } else {
      errorDiv.textContent = data.error || "Failed to submit. Please try again.";
      errorDiv.style.display = "block";
    }
  } catch (err) {
    errorDiv.textContent = "Network error. Please try again.";
    errorDiv.style.display = "block";
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Send Quotation Request</span>';
  }
}
