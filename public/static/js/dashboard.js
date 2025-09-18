// Deribit Webhook Python Dashboard JavaScript

class Dashboard {
    constructor() {
        this.apiBase = '';
        this.refreshInterval = 30000; // 30 seconds
        this.logs = [];
        this.maxLogs = 50;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadInitialData();
        this.startAutoRefresh();
    }
    
    bindEvents() {
        // Polling controls
        document.getElementById('start-polling')?.addEventListener('click', () => this.startPolling());
        document.getElementById('stop-polling')?.addEventListener('click', () => this.stopPolling());
        document.getElementById('manual-poll')?.addEventListener('click', () => this.manualPoll());
        
        // WeChat controls
        document.getElementById('test-wechat')?.addEventListener('click', () => this.testWeChat());
    }
    
    async loadInitialData() {
        await Promise.all([
            this.loadServiceStatus(),
            this.loadPollingStatus(),
            this.loadWeChatStatus()
        ]);
    }
    
    async loadServiceStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            this.updateServiceStatus(data);
            this.addLog('info', 'Service status loaded successfully');
        } catch (error) {
            this.updateServiceStatus(null, error);
            this.addLog('error', `Failed to load service status: ${error.message}`);
        }
    }
    
    updateServiceStatus(data, error = null) {
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        const statusDot = statusIndicator?.querySelector('.status-dot');
        
        if (error || !data) {
            statusText.textContent = 'Offline';
            statusDot?.classList.remove('loading', 'healthy');
            statusDot?.classList.add('unhealthy');
            return;
        }
        
        statusText.textContent = 'Online';
        statusDot?.classList.remove('loading', 'unhealthy');
        statusDot?.classList.add('healthy');
        
        // Update details
        document.getElementById('version').textContent = data.version || '-';
        document.getElementById('environment').textContent = data.environment || '-';
        document.getElementById('mock-mode').textContent = data.mock_mode ? 'Enabled' : 'Disabled';
        document.getElementById('account-count').textContent = data.enabled_accounts || 0;
        
        // Update account list
        this.updateAccountList(data.accounts || []);
    }
    
    updateAccountList(accounts) {
        const accountList = document.getElementById('account-list');
        if (!accountList) return;
        
        accountList.innerHTML = '';
        
        if (accounts.length === 0) {
            accountList.innerHTML = '<p class="logs-placeholder">No accounts configured</p>';
            return;
        }
        
        accounts.forEach(account => {
            const accountItem = document.createElement('div');
            accountItem.className = 'account-item';
            accountItem.innerHTML = `
                <span>${account.name}</span>
                <span class="account-status"></span>
            `;
            accountList.appendChild(accountItem);
        });
    }
    
    async loadPollingStatus() {
        try {
            const response = await fetch('/api/positions/polling/status');
            const data = await response.json();
            
            this.updatePollingStatus(data);
        } catch (error) {
            this.updatePollingStatus(null, error);
            this.addLog('error', `Failed to load polling status: ${error.message}`);
        }
    }
    
    updatePollingStatus(data, error = null) {
        const pollingText = document.getElementById('polling-text');
        const pollingDot = document.getElementById('polling-dot');
        
        if (error || !data || !data.success) {
            pollingText.textContent = 'Unknown';
            pollingDot?.classList.remove('healthy');
            pollingDot?.classList.add('unhealthy');
            return;
        }
        
        const isRunning = data.polling_enabled;
        pollingText.textContent = isRunning ? 'Running' : 'Stopped';
        
        if (isRunning) {
            pollingDot?.classList.remove('unhealthy');
            pollingDot?.classList.add('healthy');
        } else {
            pollingDot?.classList.remove('healthy');
            pollingDot?.classList.add('unhealthy');
        }
    }
    
    async loadWeChatStatus() {
        try {
            const response = await fetch('/api/wechat/configs');
            const data = await response.json();
            
            this.updateWeChatStatus(data);
        } catch (error) {
            this.updateWeChatStatus(null, error);
            this.addLog('error', `Failed to load WeChat status: ${error.message}`);
        }
    }
    
    updateWeChatStatus(data, error = null) {
        const wechatCount = document.getElementById('wechat-count');
        
        if (error || !data || !data.success) {
            wechatCount.textContent = '-';
            return;
        }
        
        wechatCount.textContent = data.total_configs || 0;
    }
    
    async startPolling() {
        try {
            const response = await fetch('/api/positions/polling/start', {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.addLog('success', 'Position polling started');
                await this.loadPollingStatus();
            } else {
                this.addLog('error', `Failed to start polling: ${data.message}`);
            }
        } catch (error) {
            this.addLog('error', `Error starting polling: ${error.message}`);
        }
    }
    
    async stopPolling() {
        try {
            const response = await fetch('/api/positions/polling/stop', {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.addLog('success', 'Position polling stopped');
                await this.loadPollingStatus();
            } else {
                this.addLog('error', `Failed to stop polling: ${data.message}`);
            }
        } catch (error) {
            this.addLog('error', `Error stopping polling: ${error.message}`);
        }
    }
    
    async manualPoll() {
        try {
            this.addLog('info', 'Starting manual poll...');
            
            const response = await fetch('/api/positions/poll', {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.addLog('success', `Manual poll completed: ${data.message}`);
            } else {
                this.addLog('error', `Manual poll failed: ${data.message}`);
            }
        } catch (error) {
            this.addLog('error', `Error during manual poll: ${error.message}`);
        }
    }
    
    async testWeChat() {
        try {
            this.addLog('info', 'Testing WeChat bots...');
            
            const response = await fetch('/api/wechat/test-all', {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.addLog('success', `WeChat test completed: ${data.message}`);
            } else {
                this.addLog('error', `WeChat test failed: ${data.message}`);
            }
        } catch (error) {
            this.addLog('error', `Error testing WeChat: ${error.message}`);
        }
    }
    
    addLog(level, message) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = {
            timestamp,
            level,
            message
        };
        
        this.logs.unshift(logEntry);
        
        // Keep only the most recent logs
        if (this.logs.length > this.maxLogs) {
            this.logs = this.logs.slice(0, this.maxLogs);
        }
        
        this.updateLogsDisplay();
    }
    
    updateLogsDisplay() {
        const logsContainer = document.getElementById('logs-container');
        if (!logsContainer) return;
        
        if (this.logs.length === 0) {
            logsContainer.innerHTML = '<p class="logs-placeholder">Activity logs will appear here...</p>';
            return;
        }
        
        const logsHtml = this.logs.map(log => `
            <div class="log-entry">
                <span class="log-timestamp">${log.timestamp}</span>
                <span class="log-level ${log.level}">${log.level.toUpperCase()}</span>
                <span class="log-message">${log.message}</span>
            </div>
        `).join('');
        
        logsContainer.innerHTML = logsHtml;
    }
    
    startAutoRefresh() {
        setInterval(() => {
            this.loadInitialData();
        }, this.refreshInterval);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
