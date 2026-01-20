// ==================== CONFIGURATION ==================== 

const CONFIG = {
    adminPassword: 'admin123',
    apiEndpoint: 'http://localhost:8001',
    autoRefreshInterval: 30000, // 30 seconds
    tokenPrefix: 'sk_live_'
};

let appState = {
    isLoggedIn: false,
    currentUser: null,
    tokens: [],
    apis: [
        { name: 'Root Health', endpoint: '/', method: 'GET', auth: true },
        { name: 'Cache Query', endpoint: '/cache', method: 'GET', auth: true },
        { name: 'Health Check', endpoint: '/health', method: 'GET', auth: true },
        { name: 'Cache Stats', endpoint: '/cache/stats', method: 'GET', auth: true },
        { name: 'Batch Query', endpoint: '/cache/batch', method: 'POST', auth: true },
        { name: 'Clear Cache', endpoint: '/cache/clear', method: 'DELETE', auth: true },
        { name: 'Invalidate', endpoint: '/cache/invalidate', method: 'DELETE', auth: true }
    ],
    autoRefreshEnabled: true,
    refreshInterval: null
};

// ==================== INITIALIZATION ==================== 

document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    loadTokens();
    setupEventListeners();
    loadStoredSettings();
    
    // Check if user is already logged in
    const isLoggedIn = localStorage.getItem('dashboardAuth') === 'true';
    if (isLoggedIn) {
        appState.isLoggedIn = true;
        appState.currentUser = 'Admin';
        document.getElementById('loginModal').classList.remove('active');
        document.getElementById('mainDashboard').style.display = 'block';
        document.getElementById('logoutBtn').style.display = 'block';
        updateDashboard();
    }
    
    if (appState.autoRefreshEnabled) {
        startAutoRefresh();
    }
    
    // Debug: Monitor tab changes
    const testerTab = document.getElementById('testerTab');
    if (testerTab) {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    const isActive = testerTab.classList.contains('active');
                    console.log('🔍 TesterTab active state changed:', isActive);
                    if (!isActive) {
                        console.trace('⚠️ TesterTab was deactivated! Stack trace:');
                    }
                }
            });
        });
        observer.observe(testerTab, { attributes: true });
        console.log('✅ Monitoring tester tab for unexpected changes');
    }
});

function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            switchTab(this.dataset.tab, e);
        });
    });
    
    // Enter key on password field
    document.getElementById('adminPassword')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') handleLogin();
    });
    
    // Logout
    document.getElementById('logoutBtn')?.addEventListener('click', handleLogout);
    
    // Settings
    document.getElementById('autoRefresh')?.addEventListener('change', function() {
        appState.autoRefreshEnabled = this.checked;
        if (this.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
    
    // Prevent Enter key from submitting in URL input
    document.getElementById('testerUrl')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendApiRequest(e);
        }
    });
}

// ==================== AUTHENTICATION ==================== 

function handleLogin() {
    const password = document.getElementById('adminPassword').value;
    const errorDiv = document.getElementById('loginError');
    
    if (!password) {
        showAlert(errorDiv, 'Please enter a password', 'error');
        return;
    }
    
    if (password === CONFIG.adminPassword) {
        appState.isLoggedIn = true;
        appState.currentUser = 'Admin';
        localStorage.setItem('dashboardAuth', 'true');
        localStorage.setItem('loginTime', new Date().toISOString());
        
        document.getElementById('loginModal').classList.remove('active');
        document.getElementById('mainDashboard').style.display = 'block';
        document.getElementById('logoutBtn').style.display = 'block';
        
        updateDashboard();
    } else {
        showAlert(errorDiv, 'Invalid password', 'error');
        document.getElementById('adminPassword').value = '';
    }
}

function handleLogout() {
    if (confirm('Are you sure you want to logout?')) {
        appState.isLoggedIn = false;
        localStorage.removeItem('dashboardAuth');
        localStorage.removeItem('loginTime');
        
        document.getElementById('loginModal').classList.add('active');
        document.getElementById('mainDashboard').style.display = 'none';
        document.getElementById('logoutBtn').style.display = 'none';
        document.getElementById('adminPassword').value = '';
    }
}

// ==================== DASHBOARD UPDATE ==================== 

function updateDashboard() {
    updateStats();
    refreshApiStatus();
    updateLastUpdated();
}

function updateStats() {
    document.getElementById('activeTokensCount').textContent = appState.tokens.length;
    document.getElementById('connectedApisCount').textContent = appState.apis.length;
    
    // Fetch real health status from API
    fetch(`${CONFIG.apiEndpoint}/`)
        .then(response => response.json())
        .then(data => {
            const statusEl = document.getElementById('healthStatus');
            statusEl.textContent = data.status ? '✓ ' + data.status : '✓ Online';
            statusEl.style.color = data.status === 'online' ? '#10b981' : '#f59e0b';
        })
        .catch(error => {
            const statusEl = document.getElementById('healthStatus');
            statusEl.textContent = '✗ Offline';
            statusEl.style.color = '#ef4444';
        });
}

function updateLastUpdated() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    document.getElementById('lastUpdated').textContent = `${hours}:${minutes}`;
}

// ==================== TAB MANAGEMENT ==================== 

function switchTab(tabName, sourceEvent) {
    console.log('🔄 Switching tab to:', tabName);
    
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    const tab = document.getElementById(tabName + 'Tab');
    if (tab) {
        tab.classList.add('active');
        console.log('✅ Activated tab:', tabName);
    } else {
        console.error('❌ Tab not found:', tabName);
    }
    
    // Add active to button
    if (sourceEvent && sourceEvent.target) {
        const button = sourceEvent.target.closest('.tab-button');
        if (button) {
            button.classList.add('active');
        }
    } else {
        // If no event, find button by data-tab attribute
        const button = document.querySelector(`[data-tab="${tabName}"]`);
        if (button) {
            button.classList.add('active');
        }
    }
    
    // Special handling for some tabs
    if (tabName === 'apis') {
        refreshApiStatus();
    }
    
    if (tabName === 'tester') {
        setupApiTester();
    }
}

// ==================== TOKEN MANAGEMENT ==================== 

function loadTokens() {
    // Load from localStorage
    const stored = localStorage.getItem('apiTokens');
    if (stored) {
        appState.tokens = JSON.parse(stored);
    } else {
        // Demo tokens with Eternitylabs token
        appState.tokens = [
            {
                id: 1,
                name: 'Eternitylabs Bearer Token',
                token: 'eternitylabs123',
                created: new Date().toISOString(),
                expiry: null,
                status: 'active',
                description: 'Production Bearer token for Eternitylabs Cache API',
                authType: 'bearer'
            },
            {
                id: 2,
                name: 'Production Token',
                token: 'sk_live_prod_abc123def456...',
                created: new Date(Date.now() - 86400000).toISOString(),
                expiry: 90,
                status: 'active',
                authType: 'bearer'
            }
        ];
    }
    renderTokens();
}

function renderTokens() {
    const tokensList = document.getElementById('tokensList');
    
    if (appState.tokens.length === 0) {
        tokensList.innerHTML = `
            <div class="empty-state">
                <p>No tokens configured yet</p>
                <button class="btn btn-primary" onclick="showTokenForm()">Create First Token</button>
            </div>
        `;
        return;
    }
    
    tokensList.innerHTML = appState.tokens.map(token => `
        <div class="token-card">
            <div class="token-info">
                <div class="token-name">🔑 ${token.name}</div>
                <div class="token-value">${document.getElementById('showMaskedTokens')?.checked !== false ? token.token : '••••••••••••••••••••'}</div>
                <div class="token-meta">
                    Created: ${new Date(token.created).toLocaleDateString()} | 
                    Status: <span style="color: ${token.status === 'active' ? '#27ae60' : '#e74c3c'}">${token.status}</span> |
                    Expires: ${token.expiry ? token.expiry + ' days' : 'Never'}
                </div>
            </div>
            <div class="token-actions">
                <button class="btn btn-small" onclick="copyToken('${token.token}')">📋 Copy</button>
                <button class="btn btn-small" onclick="regenerateToken(${token.id})">🔄 Regenerate</button>
                <button class="btn btn-small btn-error" onclick="revokeToken(${token.id})">🗑️ Revoke</button>
            </div>
        </div>
    `).join('');
}

function showTokenForm() {
    document.getElementById('tokenFormModal').classList.add('active');
}

function closeTokenForm() {
    document.getElementById('tokenFormModal').classList.remove('active');
    document.getElementById('tokenFormError').style.display = 'none';
    document.getElementById('tokenFormSuccess').style.display = 'none';
    document.getElementById('tokenName').value = '';
    document.getElementById('tokenDescription').value = '';
    document.getElementById('tokenExpiry').value = '';
}

function handleCreateToken(event) {
    event.preventDefault();
    
    const name = document.getElementById('tokenName').value;
    const description = document.getElementById('tokenDescription').value;
    const expiry = document.getElementById('tokenExpiry').value || null;
    const errorDiv = document.getElementById('tokenFormError');
    
    if (!name.trim()) {
        showAlert(errorDiv, 'Token name is required', 'error');
        return;
    }
    
    // Generate token
    const token = CONFIG.tokenPrefix + generateRandomString(32);
    
    const newToken = {
        id: Date.now(),
        name: name,
        description: description,
        token: token,
        created: new Date().toISOString(),
        expiry: expiry ? parseInt(expiry) : null,
        status: 'active'
    };
    
    appState.tokens.push(newToken);
    saveTokens();
    closeTokenForm();
    
    // Show token display modal with the generated token
    document.getElementById('generatedToken').value = token;
    document.getElementById('tokenDisplayModal').classList.add('active');
    
    showNotification('Token created successfully!', 'success');
    renderTokens();
}

function closeTokenDisplay() {
    document.getElementById('tokenDisplayModal').classList.remove('active');
}

function copyToken(token) {
    navigator.clipboard.writeText(token).then(() => {
        showNotification('Token copied to clipboard!', 'success');
    });
}

function regenerateToken(tokenId) {
    if (!confirm('Regenerate this token? The old token will still be valid but will be marked as regenerated.')) {
        return;
    }
    
    const token = appState.tokens.find(t => t.id === tokenId);
    if (!token) return;
    
    const newToken = CONFIG.tokenPrefix + generateRandomString(32);
    token.token = newToken;
    token.status = 'regenerated';
    
    saveTokens();
    renderTokens();
    showNotification('Token regenerated successfully!', 'success');
}

function revokeToken(tokenId) {
    if (!confirm('Revoke this token? It cannot be recovered.')) {
        return;
    }
    
    appState.tokens = appState.tokens.filter(t => t.id !== tokenId);
    saveTokens();
    renderTokens();
    showNotification('Token revoked successfully!', 'success');
}

function saveTokens() {
    localStorage.setItem('apiTokens', JSON.stringify(appState.tokens));
    updateStats();
}

// ==================== API MANAGEMENT ==================== 

function refreshApiStatus() {
    const apisList = document.getElementById('apisList');
    apisList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">Loading API status...</div>';
    
    // Fetch real data from production endpoint
    fetch(`${CONFIG.apiEndpoint}/`)
        .then(response => response.json())
        .then(data => {
            renderApiStatus(data);
        })
        .catch(error => {
            console.error('Error fetching API status:', error);
            renderApiStatusOffline();
        });
}

function renderApiStatus(data) {
    const apisList = document.getElementById('apisList');
    
    // Main service card with real data
    let html = `
        <div class="api-card">
            <div class="api-header">
                <div class="api-name">📡 ${data.service || 'Cache API'}</div>
                <div class="api-status ${data.status === 'online' ? 'online' : 'offline'}">
                    ✓ ${data.status || 'online'}
                </div>
            </div>
            <div class="api-info">
                <div class="api-info-item">
                    <div class="api-info-label">Version</div>
                    <div class="api-info-value">${data.version || '2.0.0'}</div>
                </div>
                <div class="api-info-item">
                    <div class="api-info-label">Status</div>
                    <div class="api-info-value">${data.status || 'online'}</div>
                </div>
                <div class="api-info-item">
                    <div class="api-info-label">Endpoint</div>
                    <div class="api-info-value">${CONFIG.apiEndpoint}</div>
                </div>
                <div class="api-info-item">
                    <div class="api-info-label">Response Time</div>
                    <div class="api-info-value">--ms</div>
                </div>
            </div>
        </div>
    `;
    
    // Features list
    if (data.features && data.features.length > 0) {
        html += `
            <div class="api-card">
                <div class="api-header">
                    <div class="api-name">⚙️ Available Features</div>
                </div>
                <div style="padding: 0 20px 20px 20px;">
                    <ul style="list-style: none; padding: 0; margin: 0;">
        `;
        data.features.forEach(feature => {
            html += `<li style="padding: 8px 0; color: #374151; border-bottom: 1px solid #e5e7eb;">✓ ${feature}</li>`;
        });
        html += `
                    </ul>
                </div>
            </div>
        `;
    }
    
    // Additional endpoints
    html += `
        <div class="api-card">
            <div class="api-header">
                <div class="api-name">🔗 Available Endpoints</div>
            </div>
            <div style="padding: 0 20px 20px 20px;">
    `;
    
    appState.apis.forEach(api => {
        html += `
            <div style="padding: 12px; background: #f3f4f6; border-radius: 6px; margin-bottom: 10px;">
                <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">${api.name}</div>
                <div style="font-size: 12px; color: #6b7280; font-family: monospace;">${api.method} ${api.endpoint}</div>
            </div>
        `;
    });
    
    html += `
            </div>
        </div>
    `;
    
    apisList.innerHTML = html;
}

function renderApiStatusOffline() {
    const apisList = document.getElementById('apisList');
    
    apisList.innerHTML = `
        <div class="api-card">
            <div class="api-header">
                <div class="api-name">📡 Cache API</div>
                <div class="api-status offline">✗ Offline</div>
            </div>
            <div class="api-info">
                <div class="api-info-item">
                    <div class="api-info-label">Status</div>
                    <div class="api-info-value">offline</div>
                </div>
                <div class="api-info-item">
                    <div class="api-info-label">Endpoint</div>
                    <div class="api-info-value">${CONFIG.apiEndpoint}</div>
                </div>
            </div>
            <div style="padding-top: 15px; color: #ef4444; font-size: 14px;">
                ⚠️ Unable to connect to API server. Please check your connection and endpoint configuration.
            </div>
        </div>
    `;
}

function testApiEndpoint(endpoint) {
    const testUrl = `${CONFIG.apiEndpoint}${endpoint}`;
    
    showNotification(`Testing ${endpoint}...`, 'info');
    
    // Make real API call
    fetch(testUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': appState.tokens.length > 0 ? `Bearer ${appState.tokens[0].token}` : 'Bearer test-token'
        }
    })
    .then(response => {
        if (response.ok) {
            showNotification(`✓ ${endpoint} responded successfully (${response.status})`, 'success');
        } else {
            showNotification(`✗ ${endpoint} returned ${response.status}`, 'warning');
        }
    })
    .catch(error => {
        showNotification(`✗ ${endpoint} failed: ${error.message}`, 'error');
    });
}

// ==================== SETTINGS ==================== 

function loadStoredSettings() {
    const endpoint = localStorage.getItem('apiEndpoint');
    if (endpoint) {
        CONFIG.apiEndpoint = endpoint;
        document.getElementById('apiEndpoint').value = endpoint;
    }
    
    const autoRefresh = localStorage.getItem('autoRefresh');
    if (autoRefresh !== null) {
        appState.autoRefreshEnabled = autoRefresh === 'true';
        document.getElementById('autoRefresh').checked = appState.autoRefreshEnabled;
    }
    
    const showMasked = localStorage.getItem('showMaskedTokens');
    if (showMasked !== null) {
        document.getElementById('showMaskedTokens').checked = showMasked === 'true';
    }
}

function saveSettings() {
    const endpoint = document.getElementById('apiEndpoint').value;
    CONFIG.apiEndpoint = endpoint;
    localStorage.setItem('apiEndpoint', endpoint);
    
    const autoRefresh = document.getElementById('autoRefresh').checked;
    appState.autoRefreshEnabled = autoRefresh;
    localStorage.setItem('autoRefresh', autoRefresh);
    
    const showMasked = document.getElementById('showMaskedTokens').checked;
    localStorage.setItem('showMaskedTokens', showMasked);
    
    renderTokens();
    showNotification('Settings saved successfully!', 'success');
}

function resetSettings() {
    if (confirm('Reset all settings to defaults?')) {
        localStorage.removeItem('apiEndpoint');
        localStorage.removeItem('autoRefresh');
        localStorage.removeItem('showMaskedTokens');
        location.reload();
    }
}

function changeAdminPassword() {
    const newPassword = document.getElementById('changePassword').value;
    
    if (!newPassword) {
        showNotification('Please enter a password', 'warning');
        return;
    }
    
    // In a real app, this would be sent to the server
    CONFIG.adminPassword = newPassword;
    localStorage.setItem('adminPassword', newPassword);
    
    document.getElementById('changePassword').value = '';
    showNotification('Admin password changed successfully!', 'success');
}

// ==================== API TESTER ==================== 

function setupApiTester() {
    console.log('🔧 Setting up API Tester...');
    console.log('✅ API Tester setup complete');
}

function loadBatchExample() {
    // Pre-populate the tester with the batch query example
    document.getElementById('testerUrl').value = 'https://cache-api.eternitylabs.co/cache/batch';
    document.getElementById('testerMethod').value = 'POST';
    document.getElementById('testerAuthType').value = 'bearer';
    
    // Set the first eternitylabs token
    const tokenSelect = document.getElementById('testerToken');
    if (appState.tokens.length > 0) {
        tokenSelect.value = appState.tokens[0].token;
    }
    
    // Pre-fill the batch query body
    const batchBody = {
        "team": ["Lakers", "Warriors", "Bulls"],
        "player": ["LeBron James", "Stephen Curry"],
        "market": ["moneyline", "spread"],
        "sport": "Basketball"
    };
    document.getElementById('testerBody').value = JSON.stringify(batchBody, null, 2);
    
    switchReqTab('body');
    showNotification('Batch example loaded! Click "Send" to test.', 'info');
}

function clearTesterForm() {
    document.getElementById('testerUrl').value = '';
    document.getElementById('testerMethod').value = 'GET';
    document.getElementById('testerToken').value = '';
    document.getElementById('testerAuthType').value = 'bearer';
    document.getElementById('testerBody').value = '';
    document.getElementById('testerHeaders').value = '';
    document.getElementById('testerParams').value = '';
    document.getElementById('responseBody').innerHTML = '<div style="text-align: center; color: #999; padding: 40px;">Send a request to see the response here</div>';
    document.getElementById('responseStatus').style.display = 'none';
}

function sendApiRequest(event) {
    // Prevent any default behavior (like form submission)
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    console.log('🚀 sendApiRequest called');
    console.log('📍 Current active tab:', document.querySelector('.tab-content.active')?.id);
    
    // Get URL from new input field
    let url = document.getElementById('testerUrl').value.trim();
    
    if (!url) {
        showNotification('Please enter a URL or endpoint', 'error');
        return false;
    }
    
    // If URL is just a path, append to base API
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = CONFIG.apiEndpoint + url;
    }
    
    const method = document.getElementById('testerMethod').value;
    const token = document.getElementById('testerToken').value;
    const authType = document.getElementById('testerAuthType').value;
    const bodyText = document.getElementById('testerBody').value;
    const headersText = document.getElementById('testerHeaders').value;
    const paramsText = document.getElementById('testerParams').value;
    
    const responseBodyEl = document.getElementById('responseBody');
    const responseStatusEl = document.getElementById('responseStatus');
    
    // Show loading
    responseBodyEl.innerHTML = 'Sending request...';
    responseBodyEl.className = 'response-body';
    responseStatusEl.style.display = 'none';
    
    try {
        // Parse body
        let body = null;
        if (bodyText.trim()) {
            body = JSON.parse(bodyText);
        }
        
        // Parse query parameters
        let params = {};
        if (paramsText.trim()) {
            params = JSON.parse(paramsText);
        }
        
        // Add query params to URL
        if (Object.keys(params).length > 0) {
            const queryString = new URLSearchParams(params).toString();
            url += (url.includes('?') ? '&' : '?') + queryString;
        }
        
        // Parse additional headers
        let additionalHeaders = {};
        if (headersText.trim()) {
            additionalHeaders = JSON.parse(headersText);
        }
        
        // Build headers
        const headers = {
            'Content-Type': 'application/json',
            ...additionalHeaders
        };
        
        // Add authorization header based on type
        if (token) {
            if (authType === 'bearer') {
                headers['Authorization'] = `Bearer ${token}`;
            } else if (authType === 'basic') {
                const encoded = btoa(token + ':');
                headers['Authorization'] = `Basic ${encoded}`;
            } else if (authType === 'custom') {
                headers['Authorization'] = token;
            }
        }
        
        // Make request
        const options = {
            method: method,
            headers: headers
        };
        
        if (body && method !== 'GET' && method !== 'HEAD') {
            options.body = JSON.stringify(body);
        }
        
        showNotification(`Sending ${method} ${url.substring(0, 50)}...`, 'info');
        
        // Debug logging
        console.log('📤 Request Details:');
        console.log('URL:', url);
        console.log('Method:', method);
        console.log('Headers:', headers);
        console.log('Body:', body);
        
        fetch(url, options)
            .then(response => {
                // Debug logging
                console.log('📥 Response Status:', response.status, response.statusText);
                console.log('📥 Response URL:', response.url);
                console.log('📥 Response Type:', response.type);
                console.log('📥 Response Redirected:', response.redirected);
                
                // Show status
                const statusEl = responseStatusEl.querySelector('#statusCode');
                const textEl = responseStatusEl.querySelector('#statusText');
                if (statusEl && textEl) {
                    statusEl.textContent = response.status;
                    textEl.textContent = response.statusText;
                    responseStatusEl.style.display = 'flex';
                } else {
                    console.error('❌ Status elements not found');
                }
                
                // Parse response
                return response.text().then(text => ({
                    status: response.status,
                    statusText: response.statusText,
                    text: text,
                    ok: response.ok
                }));
            })
            .then(data => {
                console.log('✅ Response received, updating UI');
                console.log('Status:', data.status, 'OK:', data.ok);
                console.log('Response text length:', data.text ? data.text.length : 0);
                
                // Try to format JSON
                let displayText = data.text;
                try {
                    displayText = JSON.stringify(JSON.parse(data.text), null, 2);
                } catch (e) {
                    // Not JSON, display as is
                    console.log('Response is not JSON, displaying as text');
                }
                
                responseBodyEl.textContent = displayText || '(Empty response)';
                responseBodyEl.className = data.ok ? 'response-body success' : 'response-body error';
                
                // Force visibility
                responseBodyEl.style.display = 'block';
                responseBodyEl.style.visibility = 'visible';
                responseBodyEl.style.opacity = '1';
                
                // Ensure tester tab stays active
                const testerTab = document.getElementById('testerTab');
                if (testerTab && !testerTab.classList.contains('active')) {
                    console.warn('⚠️ TesterTab lost active class! Re-activating...');
                    testerTab.classList.add('active');
                }
                
                console.log('✅ UI updated successfully');
                console.log('✅ Response body element:', responseBodyEl);
                console.log('✅ Response body display:', responseBodyEl.style.display);
                console.log('✅ Staying on tester tab');
                console.log('📍 Final active tab check:', document.querySelector('.tab-content.active')?.id);
                
                // Show appropriate notification based on status
                if (data.status === 401) {
                    showNotification('⚠️ Unauthorized - Invalid or expired token', 'error');
                } else if (data.status === 403) {
                    showNotification('⚠️ Forbidden - Admin access required', 'error');
                } else {
                    showNotification(
                        `Response: ${data.status} ${data.statusText}`, 
                        data.ok ? 'success' : 'warning'
                    );
                }
            })
            .catch(error => {
                console.error('❌ Fetch error:', error);
                console.log('📍 Tab after error:', document.querySelector('.tab-content.active')?.id);
                responseBodyEl.textContent = `Error: ${error.message}`;
                responseBodyEl.className = 'response-body error';
                responseStatusEl.style.display = 'none';
                
                // Ensure tester tab stays active even on error
                const testerTab = document.getElementById('testerTab');
                if (testerTab && !testerTab.classList.contains('active')) {
                    console.warn('⚠️ TesterTab lost active class after error! Re-activating...');
                    testerTab.classList.add('active');
                }
                
                showNotification(`Request failed: ${error.message}`, 'error');
            });
        
    } catch (error) {
        console.error('❌ Try-catch error:', error);
        console.log('📍 Tab after try-catch error:', document.querySelector('.tab-content.active')?.id);
        responseBodyEl.textContent = `JSON Error: ${error.message}`;
        responseBodyEl.className = 'response-body error';
        responseStatusEl.style.display = 'none';
        showNotification(`Invalid JSON: ${error.message}`, 'error');
    }
    
    return false; // Prevent any form submission
}

// ==================== UTILITY FUNCTIONS ==================== 

function generateRandomString(length) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    navigator.clipboard.writeText(element.value).then(() => {
        showNotification('Copied to clipboard!', 'success');
    });
}

function showAlert(element, message, type = 'info') {
    if (!element) return;
    
    element.textContent = message;
    element.className = `alert alert-${type} show`;
    element.style.display = 'block';
    
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notifications');
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function loadSettings() {
    // Load any settings from localStorage
}

function saveSettings() {
    // Implemented above
}

// ==================== AUTO-REFRESH ==================== 

function startAutoRefresh() {
    if (appState.refreshInterval) clearInterval(appState.refreshInterval);
    
    appState.refreshInterval = setInterval(() => {
        if (appState.isLoggedIn) {
            updateDashboard();
        }
    }, CONFIG.autoRefreshInterval);
}

function stopAutoRefresh() {
    if (appState.refreshInterval) {
        clearInterval(appState.refreshInterval);
        appState.refreshInterval = null;
    }
}

// ==================== POSTMAN STYLE TESTER FUNCTIONS ==================== 

function setEndpoint(method, endpoint, evt) {
    if (evt) {
        evt.preventDefault();
        evt.stopPropagation();
    }
    document.getElementById('testerMethod').value = method;
    document.getElementById('testerUrl').value = endpoint;
}

function switchReqTab(tab, evt) {
    // Prevent default if event is passed
    if (evt) {
        evt.preventDefault();
        evt.stopPropagation();
    }
    
    // Hide all tabs
    document.getElementById('bodyTab').style.display = 'none';
    document.getElementById('headersTab').style.display = 'none';
    document.getElementById('paramsTab').style.display = 'none';
    
    // Remove active from all buttons
    document.querySelectorAll('.req-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tab + 'Tab').style.display = 'block';
    
    // Add active to the clicked button
    if (evt && evt.target) {
        evt.target.classList.add('active');
    } else {
        // Fallback: find button by checking which tab is displayed
        const buttons = document.querySelectorAll('.req-tab-btn');
        buttons.forEach(btn => {
            if (btn.textContent.toLowerCase().includes(tab.toLowerCase())) {
                btn.classList.add('active');
            }
        });
    }
}

// ==================== PAGE UNLOAD ==================== 

window.addEventListener('beforeunload', function() {
    if (appState.refreshInterval) {
        clearInterval(appState.refreshInterval);
    }
});

// ==================== ERROR HANDLING ==================== 

window.addEventListener('error', function(e) {
    console.error('💥 Global error caught:', e.message, e.filename, e.lineno, e.colno);
    console.error('Error object:', e.error);
    // Don't prevent default - let the error be logged
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('💥 Unhandled promise rejection:', e.reason);
    // Don't prevent default
});