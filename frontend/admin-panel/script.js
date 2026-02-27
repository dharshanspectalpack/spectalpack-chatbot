// Dynamically detect API base URL - works for localhost (dev) or production domain
const API_BASE = window.location.origin + "/api/admin";

// DOM Elements
const userList = document.getElementById("user-list");
const userSearch = document.getElementById("user-search");
const currentUserName = document.getElementById("current-user-name");
const currentUserCompany = document.getElementById("current-user-company");
const sessionsContainer = document.getElementById("sessions-container");
const sessionList = document.getElementById("session-list");
const chatContainer = document.getElementById("chat-container");
const chatMessages = document.getElementById("chat-messages");
const emptyState = document.getElementById("empty-state");

const navLeads = document.getElementById("nav-leads");
const mainLeads = document.getElementById("main-leads");
const leadsSidebarContent = document.getElementById("leads-sidebar-content");

// Notification Elements
const notificationBell = document.getElementById("notification-bell");
const notificationBadge = document.getElementById("notification-badge");
const notificationsDropdown = document.getElementById("notifications-dropdown");
const notificationsList = document.getElementById("notifications-list");
const markAllReadBtn = document.getElementById("mark-all-read-btn");
let notificationPollingInterval = null;

let allUsers = [];
let currentSelectedUserId = null;
let currentSelectedSessionId = null;

// --- Auto-initialize dashboard on page load ---
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch(`${API_BASE}/users`);
        if (response.ok) {
            const data = await response.json();
            allUsers = data.users;
            renderUsers(allUsers);
        } else {
            userList.innerHTML = "<li class='user-item'>Failed to load leads.</li>";
        }
    } catch (err) {
        userList.innerHTML = "<li class='user-item'>Connection error. Ensure backend is running.</li>";
    }
    // Start notifications polling
    fetchNotifications();
    if (notificationPollingInterval) clearInterval(notificationPollingInterval);
    notificationPollingInterval = setInterval(fetchNotifications, 15000);
});

// --- Navigation --- //
navLeads.addEventListener("click", () => {
    navLeads.classList.add("active");
    navLeads.style.background = "#f1f5f9";
    navLeads.style.color = "#0f172a";

    mainLeads.style.display = "flex";
    leadsSidebarContent.style.display = "flex";
});


// --- User List --- //
function renderUsers(users) {
    userList.innerHTML = "";
    if (users.length === 0) {
        userList.innerHTML = "<li class='user-item'>No leads found</li>";
        return;
    }
    users.forEach(user => {
        const li = document.createElement("li");
        li.className = "user-item";
        li.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="user-name">${user.name}</div>
                    <div class="user-meta">${user.company} | ${user.email}</div>
                    <div class="user-meta">Joined: ${new Date(user.created_at).toLocaleDateString()}</div>
                </div>
                <button class="icon-btn delete-user-btn" data-id="${user.id}" title="Delete Lead" style="color: var(--status-danger-text); font-size: 0.9rem; padding: 4px;">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        li.addEventListener("click", (e) => {
             // If delete button was clicked
             if (e.target.closest('.delete-user-btn')) {
                 e.stopPropagation();
                 deleteUser(user.id);
                 return;
             }
             // Remove active class from all
             document.querySelectorAll(".user-item").forEach(item => item.classList.remove("active"));
             li.classList.add("active");
             selectUser(user);
        });
        userList.appendChild(li);
    });
}

// --- Delete User --- //
async function deleteUser(userId) {
    const confirmed = confirm("Are you sure you want to delete this lead? This will permanently delete their data and all associated chat sessions.");
    if (!confirmed) return;

    try {
        const response = await fetch(`${API_BASE}/users/${userId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Remove user from allUsers array
            allUsers = allUsers.filter(u => u.id !== userId);
            
            // Re-render
            const term = userSearch.value.toLowerCase();
            const filtered = term ? allUsers.filter(u => 
                u.name.toLowerCase().includes(term) || 
                u.company.toLowerCase().includes(term) ||
                u.email.toLowerCase().includes(term)
            ) : allUsers;
            renderUsers(filtered);
            
            // If the deleted user was currently selected, reset view
            if (currentSelectedUserId === userId) {
                resetView();
            }
        } else {
            alert(`Error deleting user: ${data.error || 'Unknown error'}`);
        }
    } catch (err) {
        alert("Connection error while attempting to delete lead.");
        console.error(err);
    }
}

// --- Refresh Users --- //
const refreshUsersBtn = document.getElementById("refresh-users-btn");
if (refreshUsersBtn) {
    refreshUsersBtn.addEventListener("click", async () => {
        refreshUsersBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        try {
            const response = await fetch(`${API_BASE}/users`, {});
            if (response.ok) {
                const data = await response.json();
                allUsers = data.users;
                
                // Re-apply search filter if any
                const term = userSearch.value.toLowerCase();
                if (term) {
                    const filtered = allUsers.filter(u => 
                        u.name.toLowerCase().includes(term) || 
                        u.company.toLowerCase().includes(term) ||
                        u.email.toLowerCase().includes(term)
                    );
                    renderUsers(filtered);
                } else {
                    renderUsers(allUsers);
                }
            }
        } catch (err) {
            console.error("Failed to refresh users", err);
        } finally {
            refreshUsersBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
        }
    });
}

userSearch.addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase();
    const filtered = allUsers.filter(u => 
        u.name.toLowerCase().includes(term) || 
        u.company.toLowerCase().includes(term) ||
        u.email.toLowerCase().includes(term)
    );
    renderUsers(filtered);
});

async function selectUser(user) {
    currentSelectedUserId = user.id;
    currentSelectedSessionId = null;
    currentUserName.textContent = user.name;
    currentUserCompany.textContent = `${user.company} (${user.email})`;
    emptyState.style.display = "none";
    sessionsContainer.style.display = "block";
    chatContainer.style.display = "none";
    sessionList.innerHTML = "<li>Loading sessions...</li>";

    try {
        const response = await fetch(`${API_BASE}/sessions/${user.id}`, {});
        const data = await response.json();
        if (data.success) {
            renderSessions(data.sessions);
        }
    } catch (err) {
        sessionList.innerHTML = "<li>Error loading sessions</li>";
    }
}

// --- Sessions --- //
function renderSessions(sessions) {
    sessionList.innerHTML = "";
    if (sessions.length === 0) {
        sessionList.innerHTML = "<li>No chat sessions</li>";
        return;
    }

    sessions.forEach((sess, index) => {
        const li = document.createElement("li");
        li.className = "session-item";
        const date = new Date(sess.started_at).toLocaleString();
        li.innerHTML = `
            <span class="session-date">${date}</span>
            <span class="session-status" style="color: ${sess.is_active ? 'var(--brand-secondary)' : 'var(--text-muted)'}">
               ${sess.is_active ? 'Active' : 'Ended'}
            </span>
        `;
        li.addEventListener("click", () => {
             document.querySelectorAll(".session-item").forEach(item => item.classList.remove("active"));
             li.classList.add("active");
             selectSession(sess.id);
        });
        sessionList.appendChild(li);

        // Auto-select most recent session
        if (index === 0) {
            li.click();
        }
    });
}

async function selectSession(sessionId) {
    currentSelectedSessionId = sessionId;
    chatContainer.style.display = "flex";
    chatMessages.innerHTML = "<div>Loading messages...</div>";

    try {
        const response = await fetch(`${API_BASE}/messages/${sessionId}`, {});
        const data = await response.json();
        if (data.success) {
            renderMessages(data.messages);
        }
    } catch (err) {
        chatMessages.innerHTML = "<div class='error-msg'>Error loading messages</div>";
    }
}

// --- Delete Session --- //
const deleteSessionBtn = document.getElementById("delete-session-btn");
if (deleteSessionBtn) {
    deleteSessionBtn.addEventListener("click", async () => {
        if (!currentSelectedSessionId) return;
        
        const confirmed = confirm("Are you sure you want to delete this chat session? This action cannot be undone and will delete all messages inside it.");
        if (!confirmed) return;

        deleteSessionBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
        deleteSessionBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE}/sessions/${currentSelectedSessionId}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (response.ok && data.success) {
                // Refresh the sessions for the current user to remove the deleted one from UI
                chatContainer.style.display = "none";
                emptyState.style.display = "flex";
                if (currentSelectedUserId) {
                    const indexUser = allUsers.find(u => u.id === currentSelectedUserId);
                    if (indexUser) {
                        selectUser(indexUser);
                    }
                }
            } else {
                alert(`Error deleting session: ${data.error || 'Unknown error'}`);
            }
        } catch (err) {
            alert("Connection error while attempting to delete session.");
            console.error(err);
        } finally {
            deleteSessionBtn.innerHTML = '<i class="fas fa-trash"></i> Delete Session';
            deleteSessionBtn.disabled = false;
        }
    });
}

// --- Messages --- //
function renderMessages(messages) {
    chatMessages.innerHTML = "";
    if (messages.length === 0) {
        chatMessages.innerHTML = "<div style='text-align:center; color: var(--text-muted)'>No messages in this session</div>";
        return;
    }

    messages.forEach(msg => {
        const div = document.createElement("div");
        div.className = `message ${msg.role === 'user' ? 'message-user' : 'message-bot'}`;
        
        const sender = msg.role === 'user' ? 'User' : 'Spectal Bot';
        const time = new Date(msg.timestamp).toLocaleTimeString();
        
        div.innerHTML = `
            <div class="message-meta">${sender} - ${time}</div>
            <div class="message-content">${formatText(msg.content)}</div>
        `;
        chatMessages.appendChild(div);
    });

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatText(text) {
    return text.replace(/\n/g, '<br>');
}

function resetView() {
    currentSelectedUserId = null;
    currentSelectedSessionId = null;
    currentUserName.textContent = "Select a lead";
    currentUserCompany.textContent = "to view conversation history";
    sessionsContainer.style.display = "none";
    chatContainer.style.display = "none";
    emptyState.style.display = "flex";
}

// --- Notifications --- //

// Toggle dropdown visibility
notificationBell.querySelector('button').addEventListener('click', (e) => {
    e.stopPropagation();
    notificationsDropdown.classList.toggle('show');
    if (notificationsDropdown.classList.contains('show')) {
        fetchNotifications();
    }
});

// Close dropdown if clicking outside
document.addEventListener('click', (e) => {
    if (!notificationBell.contains(e.target)) {
        notificationsDropdown.classList.remove('show');
    }
});

// Fetch notifications from backend
// Fetch notifications from backend
// Note: moving renderNotifications definition up or ensuring it's available
function renderNotifications(notifications) {
    if (notifications.length > 0) {
        notificationBadge.style.display = "flex";
        notificationBadge.textContent = notifications.length > 99 ? "99+" : notifications.length;
    } else {
        notificationBadge.style.display = "none";
        notificationBadge.textContent = "0";
    }

    notificationsList.innerHTML = "";
    if (notifications.length === 0) {
        notificationsList.innerHTML = '<div class="empty-notifications">No new notifications</div>';
        return;
    }

    notifications.forEach(notif => {
        const li = document.createElement("li");
        li.className = `notification-item ${notif.is_read ? '' : 'unread'}`;
        
        let iconHtml = '';
        if (notif.type === 'error') {
            iconHtml = '<i class="fas fa-exclamation-triangle notification-icon-error"></i>';
        } else if (notif.type === 'lead') {
            iconHtml = '<i class="fas fa-user-plus notification-icon-lead"></i>';
        } else {
            iconHtml = '<i class="fas fa-info-circle" style="color:var(--brand-secondary);"></i>';
        }
        
        const timeStr = new Date(notif.created_at).toLocaleString();

        li.innerHTML = `
            <div class="notification-title">
                ${iconHtml}
                ${notif.title}
            </div>
            <div class="notification-message">${notif.message}</div>
            <div class="notification-time">${timeStr}</div>
        `;
        
        li.addEventListener("click", () => {
            markNotificationRead(notif.id);
            
            // Optional: navigate depending on type
            if (notif.type === 'lead') {
                if(navLeads) navLeads.click();
                if(refreshUsersBtn) refreshUsersBtn.click();
            }
        });
        
        notificationsList.appendChild(li);
    });
}

async function fetchNotifications() {
    try {
        const response = await fetch(`${API_BASE}/notifications`);
        if (response.ok) {
            const data = await response.json();
            renderNotifications(data.notifications);
        }
    } catch (err) {
        console.error("Failed to fetch notifications", err);
    }
}

async function markNotificationRead(notifId) {
    try {
        const response = await fetch(`${API_BASE}/notifications/${notifId}/read`, {
            method: 'POST'
        });
        if (response.ok) {
            // Re-fetch to update badge and list
            fetchNotifications();
        }
    } catch (err) {
        console.error("Failed to mark notification read", err);
    }
}

if (markAllReadBtn) {
    markAllReadBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        // Mark all unread notifications as read
        try {
            const response = await fetch(`${API_BASE}/notifications`);
            if (response.ok) {
                const data = await response.json();
                const unread = (data.notifications || []).filter(n => !n.is_read);
                await Promise.all(unread.map(n =>
                    fetch(`${API_BASE}/notifications/${n.id}/read`, { method: 'POST' })
                ));
                fetchNotifications();
            }
        } catch (err) {
            console.error("Failed to mark all read", err);
        }
    });
}

