/**
 * Cache API Dashboard Application
 */

// Configuration
const CONFIG = {
    apiBaseUrl: 'https://cache-api.eternitylabs.co',
    adminToken: 'eternitylabsadmin', // Default for demo, should be managed securely
    checkInterval: 30000 // 30 seconds
};

// State
let state = {
    isLoggedIn: false,
    activeTab: 'tokens',
    stats: {
        activeTokens: 0,
        connectedApis: 0,
        health: 'Unknown'
    }
};

// DOM Elements
const elements = {
    loginModal: document.getElementById('loginModal'),
    mainDashboard: document.getElementById('mainDashboard'),
    logoutBtn: document.getElementById('logoutBtn'),
    loginError: document.getElementById('loginError'),
    adminPassword: document.getElementById('adminPassword'),
    tabButtons: document.querySelectorAll('.tab-button'),
    tabContents: document.querySelectorAll('.tab-content'),
    testerUrl: document.getElementById('testerUrl'),
    testerMethod: document.getElementById('testerMethod'),
    testerBody: document.getElementById('testerBody'),
    testerToken: document.getElementById('testerToken'),
    responseBody: document.getElementById('responseBody'),
    responseStatus: document.getElementById('responseStatus'),
    statusCode: document.getElementById('statusCode'),
    statusText: document.getElementById('statusText'),
    logsTableBody: document.getElementById('logsTableBody'),
    logsStats: document.getElementById('logsStats')
};

/**
 * Initialization
 */
document.addEventListener('DOMContentLoaded', () => {
    // Check if previously logged in (simple session check)
    if (localStorage.getItem('isLoggedIn') === 'true') {
        showDashboard();
    }

    // Initialize tabs
    elements.tabButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Set default token in tester
    if (elements.testerToken) {
        elements.testerToken.value = CONFIG.adminToken;
    }
    
    // Setup enter key for login
    if (elements.adminPassword) {
        elements.adminPassword.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleLogin();
        });
    }
});

/**
 * Authentication
 */
function handleLogin() {
    const password = elements.adminPassword.value;
    
    // Simple client-side check for demonstration
    // In production, this would validate against an auth endpoint
    if (password === 'admin123') {
        localStorage.setItem('isLoggedIn', 'true');
        showDashboard();
    } else {
        showLoginError('Invalid password');
    }
}

function showDashboard() {
    state.isLoggedIn = true;
    elements.loginModal.style.display = 'none';
    elements.loginModal.classList.remove('active');
    elements.mainDashboard.style.display = 'block';
    elements.logoutBtn.style.display = 'block';
    
    // Initial data fetch
    updateStats();
    
    // Setup logout handler
    elements.logoutBtn.onclick = handleLogout;
}

function handleLogout() {
    state.isLoggedIn = false;
    localStorage.setItem('isLoggedIn', 'false');
    window.location.reload();
}

function showLoginError(msg) {
    elements.loginError.textContent = msg;
    elements.loginError.style.display = 'block';
}

/**
 * Navigation
 */
function switchTab(tabId) {
    // Update state
    state.activeTab = tabId;
    
    // Update UI
    elements.tabButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    
    elements.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tabId}Tab`);
    });
    
    // Tab specific actions
    if (tabId === 'logs') {
        fetchLogs();
    }
}

/**
 * Logs Management
 */
async function fetchLogs() {
    if (!elements.logsTableBody) return;
    
    const limit = document.getElementById('logsLimit')?.value || 50;
    elements.logsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">Loading logs...</td></tr>';
    
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/admin/logs?limit=${limit}`, {
            headers: {
                'Authorization': `Bearer ${CONFIG.adminToken}`
            }
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        renderLogs(data.requests, data.total);
        
    } catch (error) {
        elements.logsTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-error">Failed to fetch logs: ${error.message}</td></tr>`;
    }
}

function renderLogs(logs, total) {
    if (!logs || logs.length === 0) {
        elements.logsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No logs found</td></tr>';
        return;
    }
    
    if (elements.logsStats) {
        elements.logsStats.textContent = `Showing ${logs.length} of ${total} total logs`;
    }
    
    const html = logs.map(log => {
        const date = new Date(log.timestamp).toLocaleString();
        const duration = log.response_time_ms ? `${log.response_time_ms.toFixed(2)}ms` : '-';
        const statusClass = log.response_status >= 400 ? 'status-error' : 'status-success';
        const location = log.location || 'Unknown';
        const token = log.token_masked || '-';
        
        return `
            <tr>
                <td>${date}</td>
                <td><span class="badge">${log.method}</span></td>
                <td class="font-mono">${log.path}</td>
                <td><span class="status-badge ${statusClass}">${log.response_status}</span></td>
                <td>${duration}</td>
                <td>
                    <div><small><strong>IP:</strong> ${log.ip_address} (${location})</small></div>
                    <div><small><strong>Token:</strong> ${token}</small></div>
                    <div><small class="text-muted"><span title="${log.user_agent}">${log.user_agent?.substring(0, 20)}...</span></small></div>
                </td>
            </tr>
        `;
    }).join('');
    
    elements.logsTableBody.innerHTML = html;
}

/**
 * API Tester
 */
function setEndpoint(method, path, event) {
    if (event) event.preventDefault();
    
    elements.testerMethod.value = method;
    elements.testerUrl.value = `${CONFIG.apiBaseUrl}${path}`;
    
    // Auto-fill body for batch request
    if (path.includes('batch') && method === 'POST') {
        loadBatchExample();
    }
}

function loadBatchExample() {
    if (elements.testerBody) {
        elements.testerBody.value = JSON.stringify({
            "team": ["sea", "ne"],
            "player": ["Cooper Kupp"],
            "market": ["Rush + Rec Yards"]
        }, null, 2);
    }
}

function clearTesterForm() {
    elements.testerUrl.value = CONFIG.apiBaseUrl;
    elements.testerBody.value = '';
    elements.responseBody.innerHTML = '<div style="text-align: center; color: #999; padding: 40px;">Send a request to see the response here</div>';
    elements.responseStatus.style.display = 'none';
}

function switchReqTab(tabName, event) {
    if (event) event.preventDefault();
    
    // Update buttons
    document.querySelectorAll('.req-tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Update content
    document.querySelectorAll('.req-tab-content').forEach(content => content.style.display = 'none');
    document.getElementById(`${tabName}Tab`).style.display = 'block';
}

async function sendApiRequest(event) {
    if (event) event.preventDefault();
    
    const method = elements.testerMethod.value;
    const url = elements.testerUrl.value;
    const token = elements.testerToken.value;
    const bodyStr = elements.testerBody.value;
    
    // UI Loading state
    elements.responseBody.innerHTML = '<div class="loading-spinner">Sending request...</div>';
    elements.responseStatus.style.display = 'none';
    
    try {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const options = {
            method,
            headers
        };
        
        if (method !== 'GET' && method !== 'HEAD' && bodyStr) {
            try {
                options.body = JSON.stringify(JSON.parse(bodyStr));
            } catch (e) {
                alert('Invalid JSON in request body');
                return;
            }
        }
        
        const startTime = performance.now();
        const response = await fetch(url, options);
        const duration = performance.now() - startTime;
        
        // Handle response
        const status = response.status;
        const statusText = response.statusText;
        let responseData;
        
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            responseData = await response.json();
            elements.responseBody.innerHTML = `<pre>${JSON.stringify(responseData, null, 2)}</pre>`;
        } else {
            responseData = await response.text();
            elements.responseBody.innerHTML = `<pre>${responseData}</pre>`;
        }
        
        // Update status UI
        elements.statusCode.textContent = status;
        elements.statusText.textContent = `${statusText} (${duration.toFixed(0)}ms)`;
        
        elements.responseStatus.className = 'response-status ' + (status >= 400 ? 'status-error' : 'status-success');
        elements.responseStatus.style.display = 'flex';
        
    } catch (error) {
        elements.responseBody.innerHTML = `<div class="alert alert-error">Request failed: ${error.message}</div>`;
    }
}

/**
 * Stats & Utils
 */
function updateStats() {
    // Mock stats for now
    if (document.getElementById('lastUpdated')) {
        document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
    }
}

function copyToClipboard(elementId) {
    const el = document.getElementById(elementId);
    el.select();
    document.execCommand('copy');
    
    // Visual feedback
    const btn = el.nextElementSibling;
    const originalText = btn.textContent;
    btn.textContent = '✓ Copied!';
    setTimeout(() => btn.textContent = originalText, 2000);
}
