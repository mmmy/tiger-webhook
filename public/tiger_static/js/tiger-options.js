const state = {
    accounts: [],
    expirations: [],
    formatter: new Intl.DateTimeFormat('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    })
};

document.addEventListener('DOMContentLoaded', () => {
    const accountSelect = document.getElementById('account-select');
    const underlyingInput = document.getElementById('underlying-input');
    const optionTypeSelect = document.getElementById('option-type-select');
    const expirationSelect = document.getElementById('expiration-select');
    const minDaysInput = document.getElementById('min-days-input');
    const maxDaysInput = document.getElementById('max-days-input');
    const minStrikeInput = document.getElementById('min-strike-input');
    const maxStrikeInput = document.getElementById('max-strike-input');
    const summaryAccount = document.getElementById('summary-account');
    const summaryUnderlying = document.getElementById('summary-underlying');
    const summaryExpiration = document.getElementById('summary-expiration');
    const summaryCount = document.getElementById('summary-count');
    const summaryUpdated = document.getElementById('summary-updated');
    const statusSection = document.getElementById('status-section');
    const statusMessage = document.getElementById('status-message');
    const tableWrapper = document.getElementById('options-table-wrapper');
    const form = document.getElementById('options-form');
    const resetButton = document.getElementById('reset-button');

    const setStatus = (message, type = 'error') => {
        if (!message) {
            statusSection.hidden = true;
            statusMessage.textContent = '';
            statusSection.classList.remove('status--success');
            return;
        }
        statusSection.hidden = false;
        statusMessage.textContent = message;
        if (type === 'success') {
            statusSection.classList.add('status--success');
        } else {
            statusSection.classList.remove('status--success');
        }
    };

    const renderPlaceholder = (text) => {
        tableWrapper.innerHTML = '<p class="placeholder">' + text + '</p>';
    };

    const formatExpiry = (timestamp) => {
        if (!timestamp) {
            return '-';
        }
        const dateValue = timestamp > 1000000000000 ? timestamp : timestamp * 1000;
        return state.formatter.format(new Date(dateValue));
    };

    const formatDaysToExpiry = (timestamp) => {
        if (!timestamp) {
            return '-';
        }
        const now = Date.now();
        const ts = timestamp > 1000000000000 ? timestamp : timestamp * 1000;
        const diff = ts - now;
        if (diff <= 0) {
            return '已到期';
        }
        return Math.round(diff / (24 * 3600 * 1000));
    };

    const buildRow = (option) => {
        const row = document.createElement('tr');

        const cells = [
            option.instrument_name || option.symbol || '-',
            option.option_type || '-',
            option.strike != null ? Number(option.strike).toFixed(2) : '-',
            formatExpiry(option.expiration_timestamp),
            formatDaysToExpiry(option.expiration_timestamp),
            option.calculated_delta != null ? Number(option.calculated_delta).toFixed(3) :
                (option.delta != null ? Number(option.delta).toFixed(3) : '-'),
            option.underlying_price != null ? Number(option.underlying_price).toFixed(2) : '-',
            option.currency || 'USD'
        ];

        cells.forEach((value, index) => {
            const cell = document.createElement('td');
            if (index === 1 && value !== '-') {
                const tag = document.createElement('span');
                const normalized = String(value).toLowerCase();
                tag.textContent = normalized.toUpperCase();
                tag.className = 'tag ' + (normalized === 'put' ? 'tag--put' : 'tag--call');
                cell.appendChild(tag);
            } else {
                cell.textContent = value;
            }
            row.appendChild(cell);
        });

        return row;
    };

    const buildRowWithoutType = (option) => {
        const row = document.createElement('tr');

        const cells = [
            option.instrument_name || option.symbol || '-',
            option.strike != null ? Number(option.strike).toFixed(2) : '-',
            option.calculated_delta != null ? Number(option.calculated_delta).toFixed(3) :
                (option.delta != null ? Number(option.delta).toFixed(3) : '-'),
            option.underlying_price != null ? Number(option.underlying_price).toFixed(2) : '-',
            option.currency || 'USD'
        ];

        cells.forEach((value) => {
            const cell = document.createElement('td');
            cell.textContent = value;
            row.appendChild(cell);
        });

        return row;
    };

    const renderTable = (options) => {
        if (!options || options.length === 0) {
            renderPlaceholder('没有符合条件的期权。');
            return;
        }

        // Separate call and put options
        const callOptions = options.filter(option => {
            const optionType = (option.option_type || '').toLowerCase();
            return optionType === 'call';
        });

        const putOptions = options.filter(option => {
            const optionType = (option.option_type || '').toLowerCase();
            return optionType === 'put';
        });

        // Create the main container
        const container = document.createElement('div');
        container.className = 'options-split-container';

        // Create call options section
        const callSection = document.createElement('div');
        callSection.className = 'options-section options-section--call';

        const callHeader = document.createElement('h3');
        callHeader.className = 'options-section__header';
        callHeader.innerHTML = '<span class="tag tag--call">CALL</span> 看涨期权';
        callSection.appendChild(callHeader);

        if (callOptions.length > 0) {
            const callTable = createOptionsTable(callOptions);
            callSection.appendChild(callTable);
        } else {
            const callPlaceholder = document.createElement('p');
            callPlaceholder.className = 'placeholder';
            callPlaceholder.textContent = '没有符合条件的看涨期权';
            callSection.appendChild(callPlaceholder);
        }

        // Create put options section
        const putSection = document.createElement('div');
        putSection.className = 'options-section options-section--put';

        const putHeader = document.createElement('h3');
        putHeader.className = 'options-section__header';
        putHeader.innerHTML = '<span class="tag tag--put">PUT</span> 看跌期权';
        putSection.appendChild(putHeader);

        if (putOptions.length > 0) {
            const putTable = createOptionsTable(putOptions);
            putSection.appendChild(putTable);
        } else {
            const putPlaceholder = document.createElement('p');
            putPlaceholder.className = 'placeholder';
            putPlaceholder.textContent = '没有符合条件的看跌期权';
            putSection.appendChild(putPlaceholder);
        }

        container.appendChild(callSection);
        container.appendChild(putSection);

        tableWrapper.innerHTML = '';
        tableWrapper.appendChild(container);
    };

    const createOptionsTable = (options) => {
        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        // Remove the '类型' column since we're separating by type
        // Remove the '到期时间' and '剩余天数' columns since all options have the same expiration date
        const headers = ['合约', '行权价', 'Delta', '标的价', '货币'];

        headers.forEach((title) => {
            const th = document.createElement('th');
            th.textContent = title;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);

        const tbody = document.createElement('tbody');
        options.forEach((option) => {
            tbody.appendChild(buildRowWithoutType(option));
        });

        table.appendChild(thead);
        table.appendChild(tbody);
        return table;
    };

    const buildQuery = () => {
        const params = new URLSearchParams();
        if (underlyingInput.value) {
            params.set('underlying', underlyingInput.value.trim());
        }
        if (accountSelect.value) {
            params.set('accountName', accountSelect.value);
        }
        if (expirationSelect.value) {
            params.set('expiryTs', expirationSelect.value);
        }
        if (optionTypeSelect.value) {
            params.set('optionType', optionTypeSelect.value);
        }
        if (minDaysInput.value) {
            params.set('minDays', minDaysInput.value);
        }
        if (maxDaysInput.value) {
            params.set('maxDays', maxDaysInput.value);
        }
        if (minStrikeInput.value) {
            params.set('minStrike', minStrikeInput.value);
        }
        if (maxStrikeInput.value) {
            params.set('maxStrike', maxStrikeInput.value);
        }
        return params.toString();
    };

    const setSummary = (payload) => {
        summaryAccount.textContent = payload.account_name || '-';
        summaryUnderlying.textContent = payload.underlying || '-';
        if (payload.expiry_timestamp) {
            const ts = Number(payload.expiry_timestamp);
            const dateValue = ts > 1000000000000 ? ts : ts * 1000;
            summaryExpiration.textContent = state.formatter.format(new Date(dateValue));
        } else {
            summaryExpiration.textContent = '-';
        }
        summaryCount.textContent = payload.count != null ? payload.count : 0;
        summaryUpdated.textContent = state.formatter.format(new Date());
    };

    const fetchOptions = async () => {
        const underlying = underlyingInput.value.trim();
        if (!underlying) {
            setStatus('请输入标的代码。');
            return;
        }

        if (!expirationSelect.value) {
            setStatus('请选择到期日后再查询。');
            return;
        }

        setStatus('正在加载期权数据...', 'success');
        renderPlaceholder('<span class="loading">请求中...</span>');

        try {
            const response = await fetch('/api/tiger/options?' + buildQuery());
            const payload = await response.json();

            if (!response.ok) {
                throw new Error(payload && payload.detail ? payload.detail : '加载期权失败');
            }

            renderTable(payload.options);
            setSummary(payload);
            setStatus(payload.message || '加载完成', 'success');
        } catch (error) {
            console.error('Failed to load options', error);
            setStatus(error.message || '加载期权失败');
            renderPlaceholder('加载失败，请稍后重试。');
        }
    };

    const populateAccounts = (accounts) => {
        accountSelect.innerHTML = '';
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = accounts.length ? '自动选择第一个启用账户' : '无可用账户';
        accountSelect.appendChild(defaultOption);

        accounts.forEach((account) => {
            const option = document.createElement('option');
            option.value = account.name;
            const labelParts = [account.name];
            if (account.description) {
                labelParts.push(account.description);
            } else if (account.market) {
                labelParts.push(account.market);
            }
            option.textContent = labelParts.join(' - ');
            accountSelect.appendChild(option);
        });
    };

    const populateExpirations = (expirations) => {
        expirationSelect.innerHTML = '';

        if (!expirations || expirations.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = '无可用到期日';
            expirationSelect.appendChild(option);
            expirationSelect.disabled = true;
            return;
        }

        expirationSelect.disabled = false;

        expirations.forEach((item) => {
            const option = document.createElement('option');
            option.value = item.timestamp;
            option.textContent = item.date + ' (' + item.days_to_expiry + ' 天)';
            expirationSelect.appendChild(option);
        });
    };

    const loadAccounts = async () => {
        try {
            const resp = await fetch('/api/accounts?enabled_only=true');
            const data = await resp.json();
            if (!resp.ok) {
                throw new Error(data && data.detail ? data.detail : '无法加载账户列表');
            }
            state.accounts = data.accounts || [];
            populateAccounts(state.accounts);
        } catch (error) {
            console.error('Failed to load accounts', error);
            populateAccounts([]);
            setStatus(error.message || '无法加载账户列表');
        }
    };

    const fetchExpirations = async (autoFetchOptions = false) => {
        const underlying = underlyingInput.value.trim();
        if (!underlying) {
            setStatus('请输入标的代码以加载到期日。');
            populateExpirations([]);
            return;
        }

        try {
            setStatus('正在加载到期日...', 'success');
            const query = new URLSearchParams();
            query.set('underlying', underlying);
            if (accountSelect.value) {
                query.set('accountName', accountSelect.value);
            }
            const resp = await fetch('/api/tiger/options/expirations?' + query.toString());
            const data = await resp.json();
            if (!resp.ok) {
                throw new Error(data && data.detail ? data.detail : '加载到期日失败');
            }
            state.expirations = data.expirations || [];
            populateExpirations(state.expirations);
            setStatus('共加载 ' + state.expirations.length + ' 个到期日。', 'success');
            if (autoFetchOptions && state.expirations.length > 0) {
                fetchOptions();
            } else {
                renderPlaceholder('请选择到期日并点击查询。');
            }
        } catch (error) {
            console.error('Failed to load expirations', error);
            populateExpirations([]);
            renderPlaceholder('请先加载到期日再查询。');
            setStatus(error.message || '加载到期日失败');
        }
    };

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        fetchOptions();
    });

    resetButton.addEventListener('click', () => {
        optionTypeSelect.value = '';
        minDaysInput.value = '';
        maxDaysInput.value = '';
        minStrikeInput.value = '';
        maxStrikeInput.value = '';
        if (state.expirations.length > 0) {
            expirationSelect.selectedIndex = 0;
        }
        renderPlaceholder('已重置筛选条件，请重新查询。');
        setStatus('筛选条件已重置', 'success');
        fetchExpirations(false);
    });

    accountSelect.addEventListener('change', () => {
        fetchExpirations(false);
    });

    underlyingInput.addEventListener('change', () => {
        fetchExpirations(false);
    });

    loadAccounts().then(() => fetchExpirations(true));
});
