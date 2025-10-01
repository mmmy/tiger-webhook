/**
 * Logs Query Page JavaScript
 * Handles log querying, filtering, and display functionality
 */

class LogsManager {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 500;
        this.totalEntries = 0;
        this.currentQuery = {};
        
        this.initializeElements();
        this.bindEvents();
        this.loadInitialData();
    }
    
    initializeElements() {
        // Filter elements
        this.timeRangeSelect = document.getElementById('time-range');
        this.customTimeRange = document.getElementById('custom-time-range');
        this.startTimeInput = document.getElementById('start-time');
        this.endTimeInput = document.getElementById('end-time');
        this.logLevelSelect = document.getElementById('log-level');
        this.searchTextInput = document.getElementById('search-text');
        this.pageSizeSelect = document.getElementById('page-size');
        
        // Button elements
        this.searchBtn = document.getElementById('search-btn');
        this.clearBtn = document.getElementById('clear-btn');
        this.refreshBtn = document.getElementById('refresh-btn');
        this.exportBtn = document.getElementById('export-btn');
        this.prevPageBtn = document.getElementById('prev-page');
        this.nextPageBtn = document.getElementById('next-page');
        
        // Display elements
        this.loadingDiv = document.getElementById('loading');
        this.logEntriesDiv = document.getElementById('log-entries');
        this.resultsCountSpan = document.getElementById('results-count');
        this.pageInfoSpan = document.getElementById('page-info');
        
        // Statistics elements
        this.totalEntriesSpan = document.getElementById('total-entries');
        this.errorCountSpan = document.getElementById('error-count');
        this.warningCountSpan = document.getElementById('warning-count');
        this.fileSizeSpan = document.getElementById('file-size');
        
        // Modal elements
        this.logModal = document.getElementById('log-modal');
        this.closeModalBtn = document.getElementById('close-modal');
        this.logDetailContent = document.getElementById('log-detail-content');
    }
    
    bindEvents() {
        // Filter events
        this.timeRangeSelect.addEventListener('change', () => this.handleTimeRangeChange());
        this.searchBtn.addEventListener('click', () => this.performSearch());
        this.clearBtn.addEventListener('click', () => this.clearFilters());
        this.refreshBtn.addEventListener('click', () => this.refreshData());
        this.exportBtn.addEventListener('click', () => this.exportLogs());
        
        // Pagination events
        this.prevPageBtn.addEventListener('click', () => this.goToPreviousPage());
        this.nextPageBtn.addEventListener('click', () => this.goToNextPage());
        this.pageSizeSelect.addEventListener('change', () => this.handlePageSizeChange());
        
        // Modal events
        this.closeModalBtn.addEventListener('click', () => this.closeModal());
        this.logModal.addEventListener('click', (e) => {
            if (e.target === this.logModal) this.closeModal();
        });
        
        // Enter key for search
        this.searchTextInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        
        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.logModal.style.display !== 'none') {
                this.closeModal();
            }
        });
    }
    
    async loadInitialData() {
        // Set default time range to last 1 hour
        this.setDefaultTimeRange();
        await this.loadStatistics();
        await this.performSearch(); // Load recent logs by default
    }

    setDefaultTimeRange() {
        const now = new Date();
        const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);

        this.startTimeInput.value = this.formatDateTimeLocal(oneHourAgo);
        this.endTimeInput.value = this.formatDateTimeLocal(now);
        this.timeRangeSelect.value = '1h';
        this.customTimeRange.style.display = 'none';
    }
    
    handleTimeRangeChange() {
        const value = this.timeRangeSelect.value;
        if (value === 'custom') {
            this.customTimeRange.style.display = 'block';
            const now = new Date();
            const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
            this.endTimeInput.value = this.formatDateTimeLocal(now);
            this.startTimeInput.value = this.formatDateTimeLocal(oneHourAgo);
        } else {
            this.customTimeRange.style.display = 'none';
        }
    }
    
    formatDateTimeLocal(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    }
    
    updateUrlParams(params) {
        const url = new URL(window.location.href);
        url.search = params.toString();
        const newUrl = `${url.pathname}${url.search}${url.hash}`;
        window.history.replaceState({}, '', newUrl);
    }

    buildQueryParams() {
        const params = new URLSearchParams();
        
        // Time range
        const timeRange = this.timeRangeSelect.value;
        if (timeRange && timeRange !== 'custom') {
            params.append('start_time', `${timeRange} ago`);
        } else if (timeRange === 'custom') {
            if (this.startTimeInput.value) {
                params.append('start_time', new Date(this.startTimeInput.value).toISOString());
            }
            if (this.endTimeInput.value) {
                params.append('end_time', new Date(this.endTimeInput.value).toISOString());
            }
        }
        
        // Other filters
        if (this.logLevelSelect.value) {
            params.append('level', this.logLevelSelect.value);
        }
        if (this.searchTextInput.value.trim()) {
            params.append('search', this.searchTextInput.value.trim());
        }
        
        // Pagination
        params.append('limit', this.pageSize.toString());
        params.append('offset', ((this.currentPage - 1) * this.pageSize).toString());
        
        return params;
    }
    
    async performSearch() {
        this.showLoading(true);
        
        try {
            const params = this.buildQueryParams();
            this.currentQuery = Object.fromEntries(params);
            this.updateUrlParams(params);
            
            const response = await fetch(`/api/logs/query?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayLogEntries(data.data.entries);
                this.updateResultsInfo(data.data.entries.length);
                this.updatePaginationControls();
            } else {
                this.showError('查询失败: ' + data.message);
            }
        } catch (error) {
            this.showError('网络错误: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadStatistics() {
        try {
            const response = await fetch('/api/logs/stats');
            const data = await response.json();
            
            if (data.success && data.data.recent_24h) {
                const stats = data.data.recent_24h;
                const fileInfo = data.data.file_info;
                
                this.totalEntriesSpan.textContent = stats.total_entries.toLocaleString();
                this.errorCountSpan.textContent = (stats.level_distribution.ERROR || 0).toLocaleString();
                this.warningCountSpan.textContent = (stats.level_distribution.WARNING || 0).toLocaleString();
                this.fileSizeSpan.textContent = fileInfo.size_mb + ' MB';
            }
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    }
    
    displayLogEntries(entries) {
        if (!entries || entries.length === 0) {
            this.logEntriesDiv.innerHTML = `
                <div class="no-results">
                    <p>🔍 没有找到匹配的日志条目</p>
                </div>
            `;
            return;
        }
        
        const entriesHtml = entries.map(entry => this.createLogEntryHtml(entry)).join('');
        this.logEntriesDiv.innerHTML = entriesHtml;
        
        // Bind click events to log entries
        this.logEntriesDiv.querySelectorAll('.log-entry').forEach((element, index) => {
            element.addEventListener('click', () => this.showLogDetail(entries[index]));
        });
    }
    
    createLogEntryHtml(entry) {
        const timestamp = this.formatTimestamp(entry.timestamp);
        const level = entry.level.toLowerCase();
        const message = this.escapeHtml(entry.message);
        const module = entry.module ? this.escapeHtml(entry.module) : '';

        return `
            <div class="log-entry">
                <div class="log-entry-header">
                    <span class="log-timestamp">${timestamp}</span>
                    <span class="log-level ${level}">${entry.level}</span>
                    <span class="log-entry-content">${message}</span>
                </div>
            </div>
        `;
    }
    
    formatTimestamp(timestamp) {
        try {
            const date = new Date(timestamp);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                fractionalSecondDigits: 3
            });
        } catch (error) {
            return timestamp;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showLogDetail(entry) {
        const detailHtml = `
            <div class="log-detail-content">
                <div class="detail-field">
                    <div class="detail-label">时间戳</div>
                    <div class="detail-value">${this.formatTimestamp(entry.timestamp)}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-label">级别</div>
                    <div class="detail-value">${entry.level}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-label">日志器</div>
                    <div class="detail-value">${entry.logger}</div>
                </div>
                ${entry.module ? `
                <div class="detail-field">
                    <div class="detail-label">模块</div>
                    <div class="detail-value">${entry.module}</div>
                </div>
                ` : ''}
                ${entry.function ? `
                <div class="detail-field">
                    <div class="detail-label">函数</div>
                    <div class="detail-value">${entry.function}</div>
                </div>
                ` : ''}
                ${entry.line ? `
                <div class="detail-field">
                    <div class="detail-label">行号</div>
                    <div class="detail-value">${entry.line}</div>
                </div>
                ` : ''}
                <div class="detail-field">
                    <div class="detail-label">消息</div>
                    <div class="detail-value">${this.escapeHtml(entry.message)}</div>
                </div>
                ${entry.extra_data && Object.keys(entry.extra_data).length > 0 ? `
                <div class="detail-field">
                    <div class="detail-label">额外数据</div>
                    <div class="detail-value"><pre>${JSON.stringify(entry.extra_data, null, 2)}</pre></div>
                </div>
                ` : ''}
            </div>
        `;
        
        this.logDetailContent.innerHTML = detailHtml;
        this.logModal.style.display = 'flex';
    }
    
    closeModal() {
        this.logModal.style.display = 'none';
    }
    
    updateResultsInfo(count) {
        this.resultsCountSpan.textContent = `${count} 条记录`;
    }
    
    updatePaginationControls() {
        this.pageInfoSpan.textContent = `第 ${this.currentPage} 页`;
        this.prevPageBtn.disabled = this.currentPage <= 1;
        // Note: We don't know total pages, so we enable next if we got full page
        this.nextPageBtn.disabled = false; // Will be handled by actual results
    }
    
    goToPreviousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.performSearch();
        }
    }
    
    goToNextPage() {
        this.currentPage++;
        this.performSearch();
    }
    
    handlePageSizeChange() {
        this.pageSize = parseInt(this.pageSizeSelect.value);
        this.currentPage = 1;
        this.performSearch();
    }
    
    clearFilters() {
        this.timeRangeSelect.value = '24h';
        this.logLevelSelect.value = '';
        this.searchTextInput.value = '';
        this.customTimeRange.style.display = 'none';
        this.currentPage = 1;
        this.performSearch();
    }
    
    refreshData() {
        this.loadStatistics();
        this.performSearch();
    }
    
    async exportLogs() {
        try {
            const params = this.buildQueryParams();
            params.set('limit', '10000'); // Export more entries
            params.delete('offset'); // Remove pagination for export
            
            const response = await fetch(`/api/logs/query?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.downloadAsCSV(data.data.entries);
            } else {
                this.showError('导出失败: ' + data.message);
            }
        } catch (error) {
            this.showError('导出错误: ' + error.message);
        }
    }
    
    downloadAsCSV(entries) {
        const headers = ['时间戳', '级别', '日志器', '模块', '函数', '行号', '消息'];
        const csvContent = [
            headers.join(','),
            ...entries.map(entry => [
                `"${entry.timestamp}"`,
                `"${entry.level}"`,
                `"${entry.logger}"`,
                `"${entry.module || ''}"`,
                `"${entry.function || ''}"`,
                `"${entry.line || ''}"`,
                `"${entry.message.replace(/"/g, '""')}"`
            ].join(','))
        ].join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `logs_${new Date().toISOString().slice(0, 10)}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    showLoading(show) {
        this.loadingDiv.style.display = show ? 'flex' : 'none';
    }
    
    showError(message) {
        this.logEntriesDiv.innerHTML = `
            <div class="no-results">
                <p>❌ ${message}</p>
            </div>
        `;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new LogsManager();
});
