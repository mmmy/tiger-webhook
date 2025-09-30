class AccountDetailPage {
    constructor() {
        this.accountName = this._detectAccountName();
        this.currencySelect = document.getElementById('currency-select');
        this.refreshButton = document.getElementById('refresh-button');
        this.positionsWrapper = document.getElementById('positions-wrapper');
        this.summarySection = document.getElementById('summary-section');
        this.assetsSection = document.getElementById('assets-section');
        this.managedSection = document.getElementById('managed-section');
        this.wechatSection = document.getElementById('wechat-section');
        this.errorsSection = document.getElementById('errors-section');
        this.errorList = document.getElementById('error-list');

        if (!this.accountName) {
            this._renderFatalError('Unable to determine account name from URL.');
            return;
        }

        this._bindEvents();
        this.loadData();
    }

    _detectAccountName() {
        const match = window.location.pathname.match(/\/accounts\/([^\/]+)/);
        if (!match || match.length < 2) {
            return null;
        }
        try {
            return decodeURIComponent(match[1]);
        } catch (error) {
            console.error('Failed to decode account name', error);
            return match[1];
        }
    }

    _bindEvents() {
        if (this.refreshButton) {
            this.refreshButton.addEventListener('click', () => this.loadData(true));
        }

        if (this.currencySelect) {
            this.currencySelect.addEventListener('change', () => this.loadData());
        }
    }

    async loadData(isManual = false) {
        const currency = this.currencySelect?.value || 'USD';
        const params = new URLSearchParams({
            include_positions: 'true',
            include_summary: 'true',
            include_assets: 'true',
            include_managed: 'true',
            currency
        });

        this._setLoadingState(isManual);

        try {
            const response = await fetch(`/api/accounts/${encodeURIComponent(this.accountName)}?${params.toString()}`);
            if (!response.ok) {
                throw new Error(`Request failed: ${response.status}`);
            }

            const payload = await response.json();
            this._renderData(payload);
        } catch (error) {
            console.error('Failed to load account detail', error);
            this._renderErrorState(error);
        }
    }

    _setLoadingState(isManual) {
        if (isManual && this.refreshButton) {
            this.refreshButton.disabled = true;
            this.refreshButton.textContent = 'Refreshing...';
        }

        this.positionsWrapper.innerHTML = '<p class="placeholder">Loading positions...</p>';
        this.summarySection.innerHTML = '<p class="placeholder">Loading account summary...</p>';
        if (this.assetsSection) {
            this.assetsSection.innerHTML = '<p class="placeholder">Loading asset information...</p>';
        }
        if (this.managedSection) {
            this.managedSection.innerHTML = '<p class="placeholder">Loading managed account details...</p>';
        }
        this.wechatSection.innerHTML = '<p class="placeholder">Loading WeChat configuration...</p>';
    }

    _renderData(payload) {
        const { account, environment, polling, summary, positions, assets, managed_accounts: managedAccounts, wechat_bot: wechatBot, errors } = payload;

        this._updateHeading(account);
        this._updateQuickStats(account, environment);
        this._updateMetadata(account, environment, polling);
        this._updateWeChat(wechatBot);
        this._updateSummary(summary);
        this._updateAssets(assets);
        this._updateManagedAccounts(managedAccounts);
        this._updatePositions(positions);
        this._updateErrors(errors);
        this._resetRefreshButton();
    }

    _updateHeading(account) {
        const heading = document.getElementById('account-name-heading');
        const description = document.getElementById('account-description');

        if (heading) {
            heading.textContent = account.name;
        }

        if (description) {
            description.textContent = account.description || 'No description provided.';
        }
    }

    _updateQuickStats(account, environment) {
        const statusEl = document.getElementById('account-status');
        const marketEl = document.getElementById('account-market');
        const numberEl = document.getElementById('account-number');
        const mockModeEl = document.getElementById('mock-mode');

        if (statusEl) {
            statusEl.textContent = account.enabled ? 'Enabled' : 'Disabled';
            if (account.enabled) {
                statusEl.dataset.state = 'enabled';
            } else {
                statusEl.dataset.state = 'disabled';
            }
        }

        if (marketEl) {
            marketEl.textContent = account.market || '-';
        }

        if (numberEl) {
            numberEl.textContent = account.account_number || '-';
        }

        if (mockModeEl) {
            mockModeEl.textContent = environment?.mock_mode ? 'Enabled' : 'Disabled';
        }
    }

    _updateMetadata(account, environment, polling) {
        const tigerIdEl = document.getElementById('account-tiger-id');
        const keyPathEl = document.getElementById('account-key-path');
        const tokenEl = document.getElementById('account-token');
        const trackingEl = document.getElementById('polling-tracking');
        const intervalEl = document.getElementById('polling-interval');
        const environmentEl = document.getElementById('environment-name');
        const testEnvEl = document.getElementById('test-environment');

        if (tigerIdEl) tigerIdEl.textContent = account.tiger_id || '-';
        if (keyPathEl) keyPathEl.textContent = account.private_key_path || '-';
        if (tokenEl) tokenEl.textContent = account.has_user_token ? 'Configured' : 'Not configured';

        if (trackingEl) {
            const tracking = polling?.tracking_account;
            trackingEl.innerHTML = tracking
                ? '<span class="badge success">Active</span>'
                : '<span class="badge warning">Not Monitored</span>';
        }

        if (intervalEl) {
            const interval = polling?.interval_seconds ?? 0;
            intervalEl.textContent = interval ? `${interval}s` : 'Not configured';
        }

        if (environmentEl) {
            environmentEl.textContent = environment?.environment || '-';
        }

        if (testEnvEl) {
            const value = environment?.test_environment;
            testEnvEl.textContent = value === true ? 'Test' : 'Production';
        }
    }

    _updateWeChat(wechatBot) {
        if (!this.wechatSection) return;

        if (!wechatBot) {
            this.wechatSection.innerHTML = '<p class="placeholder">WeChat bot not configured for this account.</p>';
            return;
        }

        this.wechatSection.innerHTML = `
            <dl>
                <div>
                    <dt>Webhook URL</dt>
                    <dd>${wechatBot.webhook_url}</dd>
                </div>
                <div>
                    <dt>Enabled</dt>
                    <dd>${wechatBot.enabled ? 'Yes' : 'No'}</dd>
                </div>
                <div>
                    <dt>Timeout</dt>
                    <dd>${wechatBot.timeout} ms</dd>
                </div>
                <div>
                    <dt>Retry Count</dt>
                    <dd>${wechatBot.retry_count}</dd>
                </div>
                <div>
                    <dt>Retry Delay</dt>
                    <dd>${wechatBot.retry_delay} ms</dd>
                </div>
            </dl>
        `;
    }

    _updateSummary(summary) {
        if (!this.summarySection) return;

        if (!summary) {
            this.summarySection.innerHTML = '<p class="placeholder">Summary not available for this account.</p>';
            return;
        }

        const metrics = [
            { label: 'Option Positions', value: summary.option_position_count },
            { label: 'Total Delta', value: summary.option_total_delta },
            { label: 'Total Gamma', value: summary.option_total_gamma },
            { label: 'Total Theta', value: summary.option_total_theta },
            { label: 'Total Vega', value: summary.option_total_vega },
            { label: 'Unrealized PnL', value: summary.total_unrealized_pnl },
            { label: 'Realized PnL', value: summary.total_realized_pnl },
            { label: 'Mark Value', value: summary.total_mark_value }
        ];

        const metricsHtml = metrics.map(metric => `
            <div class="summary-item">
                <span class="summary-label">${metric.label}</span>
                <span class="summary-value">${this._formatNumber(metric.value)}</span>
            </div>
        `).join('');

        this.summarySection.innerHTML = `
            <div class="summary-grid">
                ${metricsHtml}
            </div>
            <p class="summary-timestamp">Updated at ${new Date(summary.timestamp).toLocaleString()}</p>
        `;
    }

    _updateAssets(assets) {
        if (!this.assetsSection) return;

        if (!assets || assets.length === 0) {
            this.assetsSection.innerHTML = '<p class="placeholder">Asset information not available for this account.</p>';
            return;
        }

        const [primary] = assets;
        const summary = primary?.summary || {};
        const summaryMetrics = [
            { label: 'Net Liquidation', key: 'net_liquidation' },
            { label: 'Cash', key: 'cash' },
            { label: 'Buying Power', key: 'buying_power' },
            { label: 'Available Funds', key: 'available_funds' },
            { label: 'Equity With Loan', key: 'equity_with_loan' },
            { label: 'Maintenance Margin', key: 'maintenance_margin_requirement' },
            { label: 'Initial Margin', key: 'initial_margin_requirement' },
            { label: 'Realized PnL', key: 'realized_pnl' },
            { label: 'Unrealized PnL', key: 'unrealized_pnl' }
        ];

        const summaryHtml = summaryMetrics.map(({ label, key }) => `
            <div class="summary-item">
                <span class="summary-label">${label}</span>
                <span class="summary-value">${this._formatNumber(summary[key])}</span>
            </div>
        `).join('');

        let marketHtml = '';
        if (Array.isArray(primary?.market_values) && primary.market_values.length) {
            const rows = primary.market_values.map(item => `
                <tr>
                    <td>${item.currency || '-'}</td>
                    <td>${this._formatNumber(item.net_liquidation)}</td>
                    <td>${this._formatNumber(item.cash_balance)}</td>
                    <td>${this._formatNumber(item.stock_market_value)}</td>
                    <td>${this._formatNumber(item.option_market_value)}</td>
                    <td>${this._formatNumber(item.realized_pnl)}</td>
                    <td>${this._formatNumber(item.unrealized_pnl)}</td>
                </tr>
            `).join('');

            marketHtml = `
                <div class="assets-market-values">
                    <h3>Market Values</h3>
                    <table class="positions-table assets-table">
                        <thead>
                            <tr>
                                <th>Currency</th>
                                <th>Net Liquidation</th>
                                <th>Cash</th>
                                <th>Stock Value</th>
                                <th>Option Value</th>
                                <th>Realized PnL</th>
                                <th>Unrealized PnL</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            `;
        }

        this.assetsSection.innerHTML = `
            <div class="summary-grid assets-summary">
                ${summaryHtml || '<p class="placeholder">No asset summary metrics available.</p>'}
            </div>
            ${marketHtml}
        `;
    }


    _updateManagedAccounts(managedAccounts) {
        if (!this.managedSection) return;

        if (!managedAccounts || managedAccounts.length === 0) {
            this.managedSection.innerHTML = '<p class="placeholder">Managed account information not available for this account.</p>';
            return;
        }

        const rows = managedAccounts.map(profile => {
            const capability = Array.isArray(profile.capability)
                ? profile.capability.join(', ')
                : (profile.capability || '-');
            const status = profile.status || '-';
            const accountId = profile.account || '-';
            const accountType = profile.account_type || '-';

            return `
                <tr>
                    <td>${accountId}</td>
                    <td>${capability}</td>
                    <td>${status}</td>
                    <td>${accountType}</td>
                </tr>
            `;
        }).join('');

        this.managedSection.innerHTML = `
            <table class="positions-table managed-account-table">
                <thead>
                    <tr>
                        <th>Account</th>
                        <th>Capability</th>
                        <th>Status</th>
                        <th>Account Type</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }


    _updatePositions(positions) {
        if (!this.positionsWrapper) return;

        if (!positions || positions.length === 0) {
            this.positionsWrapper.innerHTML = '<p class="placeholder">No open positions for this account.</p>';
            return;
        }

        const header = [
            'Instrument', 'Size', 'Direction', 'Mark Price', 'Delta', 'Gamma', 'Theta', 'Vega', 'Unrealized PnL', 'Realized PnL'
        ];

        const rows = positions.map(position => `
            <tr>
                <td>${position.instrument_name || '-'}</td>
                <td>${this._formatNumber(position.size)}</td>
                <td>${position.direction || '-'}</td>
                <td>${this._formatNumber(position.mark_price)}</td>
                <td>${this._formatNumber(position.delta)}</td>
                <td>${this._formatNumber(position.gamma)}</td>
                <td>${this._formatNumber(position.theta)}</td>
                <td>${this._formatNumber(position.vega)}</td>
                <td>${this._formatNumber(position.floating_profit_loss)}</td>
                <td>${this._formatNumber(position.realized_profit_loss)}</td>
            </tr>
        `).join('');

        this.positionsWrapper.innerHTML = `
            <table class="positions-table">
                <thead>
                    <tr>${header.map(label => `<th>${label}</th>`).join('')}</tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    _updateErrors(errors) {
        if (!this.errorsSection || !this.errorList) return;

        if (!errors) {
            this.errorsSection.hidden = true;
            this.errorList.innerHTML = '';
            return;
        }

        this.errorsSection.hidden = false;
        this.errorList.innerHTML = Object.entries(errors).map(
            ([key, message]) => `<li><strong>${key}:</strong> ${message}</li>`
        ).join('');
    }

    _renderErrorState(error) {
        const message = error?.message || 'Failed to load account data.';
        this.positionsWrapper.innerHTML = `<p class="placeholder">${message}</p>`;
        this.summarySection.innerHTML = `<p class="placeholder">${message}</p>`;
        if (this.assetsSection) {
            this.assetsSection.innerHTML = `<p class="placeholder">${message}</p>`;
        }
        if (this.managedSection) {
            this.managedSection.innerHTML = `<p class="placeholder">${message}</p>`;
        }
        this.wechatSection.innerHTML = `<p class="placeholder">${message}</p>`;
        this._resetRefreshButton();
    }

    _renderFatalError(message) {
        document.body.innerHTML = `
            <div class="fatal-error">
                <h1>Account Detail</h1>
                <p>${message}</p>
                <a href="/" class="btn btn-primary">Back to Dashboard</a>
            </div>
        `;
    }

    _resetRefreshButton() {
        if (this.refreshButton) {
            this.refreshButton.disabled = false;
            this.refreshButton.textContent = 'Refresh';
        }
    }

    _formatNumber(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return '-';
        }
        if (Math.abs(Number(value)) >= 1000) {
            return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
        }
        return Number(value).toFixed(2);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AccountDetailPage();
});
