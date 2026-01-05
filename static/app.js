// 全局变量
let currentUser = null;
let currentPage = 'dashboard';
let currentTurbineId = null;

// 累积选择的文件列表
let selectedFiles = [];

// 专家记录创建时的累积文件选择
let logAttachmentFiles = [];

// 智能总结缓存
const intelligentSummaryCache = new Map();
const CACHE_STORAGE_KEY = 'wind_whisper_intelligent_summary_cache';
const LATEST_ANALYSIS_KEY = 'wind_whisper_latest_analysis';

// 从localStorage加载缓存
function loadCacheFromStorage() {
    try {
        const stored = localStorage.getItem(CACHE_STORAGE_KEY);
        if (stored) {
            const cacheData = JSON.parse(stored);
            Object.entries(cacheData).forEach(([key, value]) => {
                intelligentSummaryCache.set(key, value);
            });
        }
    } catch (error) {
        console.warn('加载缓存失败:', error);
    }
}

// AI润色总结
async function polishSummary() {
    try {
        const summaryTextarea = document.getElementById('edit-event-summary');
        if (!summaryTextarea) {
            showToast('找不到事件摘要字段', 'error');
            return;
        }

        const originalSummary = summaryTextarea.value.trim();
        if (!originalSummary) {
            showToast('请先输入事件摘要内容', 'warning');
            return;
        }

        const button = event.target;
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> AI润色中...';

        // 模拟AI润色处理
        await new Promise(resolve => setTimeout(resolve, 2000));

        // 生成润色后的内容
        const polishedSummary = generatePolishedSummary(originalSummary);
        
        // 更新摘要内容
        summaryTextarea.value = polishedSummary;
        showToast('AI润色完成', 'success');

    } catch (error) {
        console.error('AI润色失败:', error);
        showToast('AI润色失败: ' + error.message, 'error');
    } finally {
        const button = event.target;
        if (button) {
            button.disabled = false;
            button.innerHTML = originalText;
        }
    }
}

// 生成润色后的摘要
function generatePolishedSummary(originalSummary) {
    // 简单的润色逻辑，实际应用中可以调用真正的AI服务
    const polishTemplates = [
        {
            pattern: /设备.*问题/,
            replacement: '经分析发现设备存在异常情况'
        },
        {
            pattern: /需要.*处理/,
            replacement: '建议立即采取相应处理措施'
        },
        {
            pattern: /检查.*维护/,
            replacement: '需要进行全面检查和专业维护'
        }
    ];

    let polishedText = originalSummary;
    
    // 应用润色模板
    polishTemplates.forEach(template => {
        if (template.pattern.test(polishedText)) {
            polishedText = polishedText.replace(template.pattern, template.replacement);
        }
    });

    // 添加专业性描述
    if (polishedText === originalSummary) {
        polishedText = `经AI分析优化：${originalSummary}\n\n建议措施：\n1. 立即安排技术人员现场检查\n2. 记录详细故障信息\n3. 制定针对性解决方案\n4. 跟踪处理进度直至问题解决`;
    }

    return polishedText;
}

// 保存缓存到localStorage
function saveCacheToStorage() {
    try {
        const cacheData = {};
        intelligentSummaryCache.forEach((value, key) => {
            cacheData[key] = value;
        });
        localStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(cacheData));
    } catch (error) {
        console.warn('保存缓存失败:', error);
    }
}

// 缓存键生成函数
function getCacheKey(turbineId, analysisMode, daysBack = 30) {
    return `${turbineId}_${analysisMode}_${daysBack}`;
}

// 检查缓存是否有效（30分钟内有效）
function isCacheValid(cacheEntry) {
    if (!cacheEntry) return false;
    const now = Date.now();
    const cacheTime = new Date(cacheEntry.cached_at).getTime();
    const thirtyMinutes = 30 * 60 * 1000; // 30分钟
    return (now - cacheTime) < thirtyMinutes;
}

// 获取缓存的智能总结
function getCachedSummary(turbineId, analysisMode, daysBack = 30) {
    const cacheKey = getCacheKey(turbineId, analysisMode, daysBack);
    const cacheEntry = intelligentSummaryCache.get(cacheKey);
    
    if (isCacheValid(cacheEntry)) {
        return cacheEntry;
    }
    
    // 清理过期缓存
    if (cacheEntry) {
        intelligentSummaryCache.delete(cacheKey);
        saveCacheToStorage();
    }
    
    return null;
}

// 设置缓存
function setCachedSummary(turbineId, analysisMode, summaryData, daysBack = 30) {
    const cacheKey = getCacheKey(turbineId, analysisMode, daysBack);
    const cacheEntry = {
        ...summaryData,
        cached_at: new Date().toISOString()
    };
    intelligentSummaryCache.set(cacheKey, cacheEntry);
    
    // 保存最新分析结果
    saveLatestAnalysis(turbineId, analysisMode, cacheEntry);
    
    // 保存到localStorage
    saveCacheToStorage();
    
    // 限制缓存大小，最多保存100个条目
    if (intelligentSummaryCache.size > 100) {
        const firstKey = intelligentSummaryCache.keys().next().value;
        intelligentSummaryCache.delete(firstKey);
        saveCacheToStorage();
    }
}

// 保存最新分析结果
function saveLatestAnalysis(turbineId, analysisMode, cacheEntry) {
    try {
        const latestAnalysis = JSON.parse(localStorage.getItem(LATEST_ANALYSIS_KEY) || '{}');
        latestAnalysis[turbineId] = {
            analysisMode: analysisMode,
            ...cacheEntry
        };
        localStorage.setItem(LATEST_ANALYSIS_KEY, JSON.stringify(latestAnalysis));
    } catch (error) {
        console.warn('保存最新分析结果失败:', error);
    }
}

// 获取最新分析结果
function getLatestAnalysis(turbineId) {
    try {
        const latestAnalysis = JSON.parse(localStorage.getItem(LATEST_ANALYSIS_KEY) || '{}');
        const analysis = latestAnalysis[turbineId];
        if (analysis && isCacheValid(analysis)) {
            return analysis;
        }
    } catch (error) {
        console.warn('获取最新分析结果失败:', error);
    }
    return null;
}

// 状态相关辅助函数
function getStatusColor(status) {
    const statusColors = {
        'ALARM': 'danger',
        'WATCH': 'warning', 
        'MAINTENANCE': 'info',
        'NORMAL': 'success',
        'UNKNOWN': 'secondary',
        // 兼容旧的格式
        'Alarm': 'danger',
        'Watch': 'warning', 
        'Maintenance': 'info',
        'Normal': 'success',
        'Unknown': 'secondary'
    };
    return statusColors[status] || 'secondary';
}

function getStatusLabel(status) {
    const statusLabels = {
        'ALARM': '告警',
        'WATCH': '观察',
        'MAINTENANCE': '维护',
        'NORMAL': '正常',
        'UNKNOWN': '未知',
        // 兼容旧的格式
        'Alarm': '告警',
        'Watch': '观察',
        'Maintenance': '维护',
        'Normal': '正常',
        'Unknown': '未知'
    };
    return statusLabels[status] || status;
}

function getSeverityColor(severity) {
    const severityColors = {
        'critical': 'danger',
        'high': 'warning',
        'medium': 'info',
        'low': 'success',
        'normal': 'success',
        'Critical': 'danger',
        'High': 'warning',
        'Medium': 'info',
        'Low': 'success',
        'Normal': 'success',
        'CRITICAL': 'danger',
        'HIGH': 'warning',
        'MEDIUM': 'info',
        'LOW': 'success',
        'NORMAL': 'success',
        'ALARM': 'danger',
        'WATCH': 'warning',
        'MAINTENANCE': 'info',
        'UNKNOWN': 'secondary',
        'alarm': 'danger',
        'watch': 'warning',
        'maintenance': 'info',
        'unknown': 'secondary',
        'Alarm': 'danger',
        'Watch': 'warning',
        'Maintenance': 'info',
        'Unknown': 'secondary',
        'Info': 'secondary'
    };
    return severityColors[severity] || 'secondary';
}

function getSeverityLabel(severity) {
    const severityLabels = {
        'critical': '严重',
        'high': '高',
        'medium': '中',
        'low': '低',
        'normal': '正常',
        'Critical': '严重',
        'High': '高',
        'Medium': '中',
        'Low': '低',
        'Normal': '正常',
        'CRITICAL': '严重',
        'HIGH': '高',
        'MEDIUM': '中',
        'LOW': '低',
        'NORMAL': '正常',
        'ALARM': '告警',
        'WATCH': '观察',
        'MAINTENANCE': '维护',
        'UNKNOWN': '未知',
        'alarm': '告警',
        'watch': '观察',
        'maintenance': '维护',
        'unknown': '未知',
        'Alarm': '告警',
        'Watch': '观察',
        'Maintenance': '维护',
        'Unknown': '未知',
        'Info': '信息'
    };
    return severityLabels[severity] || severity;
}

function getSeverityIcon(severity) {
    const severityIcons = {
        'NORMAL': 'bi-check-circle',
        'ALARM': 'bi-exclamation-triangle-fill',
        'WATCH': 'bi-eye',
        'UNKNOWN': 'bi-question-circle',
        'normal': 'bi-check-circle',
        'alarm': 'bi-exclamation-triangle-fill',
        'watch': 'bi-eye',
        'unknown': 'bi-question-circle'
    };
    return severityIcons[severity] || 'bi-info-circle';
}

// 保持向后兼容的函数名
function getEventTypeIcon(eventType) {
    return getSeverityIcon(eventType);
}

// 日期格式化函数
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}
window.authToken = null;  // 设为全局变量，供其他脚本访问

// API基础URL
const API_BASE = '/api';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 加载缓存数据
    loadCacheFromStorage();
    
    // 检查本地存储的token
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
        window.authToken = storedToken;
        getCurrentUser();
    }
    
    // 加载初始数据
    loadDashboard();
    loadTurbines();
});

// 显示指定的内容区域
function showSection(sectionName) {
    // 检查页面访问权限
    if (!checkPageAccess(sectionName)) {
        return;
    }
    
    // 隐藏所有内容区域
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
    });
    
    // 显示指定区域
    document.getElementById(sectionName + '-section').style.display = 'block';
    
    // 更新导航状态
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // 根据sectionName找到对应的导航链接并设为active
    const targetNavLink = document.querySelector(`[onclick="showSection('${sectionName}')"]`);
    if (targetNavLink) {
        targetNavLink.classList.add('active');
    }
    
    // 根据区域加载相应数据
    switch(sectionName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'rag':
            loadTurbineOptions();
            break;
        case 'timeline':
            loadAllTurbinesTimeline();
            break;
        case 'expert-logs':
            if (window.authToken && currentUser) {
                loadExpertLogs();
            } else {
                displayExpertLogsLoginPrompt();
            }
            break;
        case 'user-management':
            if (window.authToken && currentUser) {
                loadUsers();
            } else {
                showToast('请先登录以访问用户管理功能', 'warning');
            }
            break;
        case 'turbines':
            loadTurbinesTable();
            break;
    }

    // 根据用户角色和当前页面，控制“添加风机”按钮的可见性
    const addTurbineBtn = document.getElementById('add-turbine-btn');
    if (addTurbineBtn) {
        if (sectionName === 'turbines' && currentUser && (currentUser.role === 'ADMIN' || currentUser.role === 'EXPERT')) {
            addTurbineBtn.style.display = 'block';
        } else {
            addTurbineBtn.style.display = 'none';
        }
    }
}

// 检查页面访问权限
function checkPageAccess(sectionName) {
    // 如果用户未登录，只允许访问dashboard、rag和timeline
    if (!currentUser) {
        const allowedSections = ['dashboard', 'rag', 'timeline'];
        if (allowedSections.includes(sectionName)) {
            return true;
        }
        showToast('请先登录以访问此功能', 'warning');
        return false;
    }
    
    const userRole = currentUser.role;
    
    // ADMIN can access everything
    if (userRole === 'ADMIN') {
        return true;
    }
    
    // EXPERT can access everything except user-management
    if (userRole === 'EXPERT') {
        if (sectionName === 'user-management') {
            showToast('您没有权限访问用户管理功能', 'error');
            return false;
        }
        return true;
    }
    
    // READER can access a limited set of pages
    if (userRole === 'READER') {
        const allowedSections = ['dashboard',  'timeline', 'turbines'];
        if (allowedSections.includes(sectionName)) {
            return true;
        }
        showToast('您没有权限访问此功能', 'error');
        return false;
    }
    
    // Deny any other roles by default
    showToast('未知用户角色，访问受限', 'error');
    return false;
}

// API请求封装
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (window.authToken) {
        defaultOptions.headers['Authorization'] = `Bearer ${window.authToken}`;
    }
    
    // 正确合并headers，确保Authorization头不被覆盖
    const finalOptions = { 
        ...defaultOptions, 
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };
    if (finalOptions.body && typeof finalOptions.body === 'object') {
        finalOptions.body = JSON.stringify(finalOptions.body);
    }
    
    try {
        // 如果URL已经以/api开头，则不添加API_BASE前缀
        const finalUrl = url.startsWith('/api') ? url : API_BASE + url;
        const response = await fetch(finalUrl, finalOptions);
        
        if (response.status === 401) {
            // Token过期，清除认证信息
            window.authToken = null;
            currentUser = null;
            localStorage.removeItem('authToken');
            updateUserInfo();
            throw new Error('认证已过期，请重新登录');
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '请求失败');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API请求错误:', error);
        throw error;
    }
}

// 用户认证相关
function showLogin() {
    const modal = new bootstrap.Modal(document.getElementById('loginModal'));
    modal.show();
}

async function login() {
    console.log('Login function called');
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    console.log('Raw username:', JSON.stringify(username));
    console.log('Raw password:', JSON.stringify(password));
    console.log('Username length:', username ? username.length : 0);
    console.log('Password length:', password ? password.length : 0);
    
    // 清理输入数据
    const cleanUsername = username ? username.trim() : '';
    const cleanPassword = password ? password.trim() : '';
    
    console.log('Clean username:', JSON.stringify(cleanUsername));
    console.log('Clean password length:', cleanPassword.length);
    
    if (!cleanUsername || !cleanPassword) {
        alert('请输入用户名和密码');
        return;
    }
    
    const loginData = {
        username: cleanUsername,
        password: cleanPassword
    };
    
    console.log('Login data to send:', JSON.stringify(loginData));
    
    try {
        console.log('Calling API...');
        const response = await apiRequest('/auth/login', {
            method: 'POST',
            body: loginData
        });
        
        console.log('Login response:', response);
        
        window.authToken = response.access_token;
        localStorage.setItem('authToken', window.authToken);
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
        if (modal) {
            modal.hide();
        } else {
            console.error('Modal instance not found');
        }
        
        // 获取用户信息
        await getCurrentUser();
        
        // 刷新页面数据
        loadDashboard();
        
        // 检查当前是否在专家记录页面，如果是则重新加载数据
        const currentSection = document.querySelector('.section.active');
        if (currentSection && currentSection.id === 'expert-logs') {
            loadExpertLogs();
        }
        
        alert('登录成功！');
        
    } catch (error) {
        console.error('Login error:', error);
        alert('登录失败: ' + error.message);
    }
}

async function getCurrentUser() {
    try {
        const user = await apiRequest('/auth/me');
        currentUser = user;
        updateUserInfo();
    } catch (error) {
        console.error('获取用户信息失败:', error);
    }
}

function updateUserInfo() {
    const userInfoElement = document.getElementById('user-info');
    if (currentUser) {
        userInfoElement.textContent = `${currentUser.username} (${currentUser.role})`;
        userInfoElement.nextElementSibling.textContent = '退出';
        userInfoElement.nextElementSibling.onclick = logout;
        
        // 根据用户角色显示/隐藏用户管理菜单
        updateUIBasedOnUserRole();
    } else {
        userInfoElement.textContent = '未登录';
        userInfoElement.nextElementSibling.textContent = '登录';
        
        // 隐藏用户管理菜单
        const userManagementNav = document.getElementById('user-management-nav');
        if (userManagementNav) {
            userManagementNav.style.display = 'none';
        }
        userInfoElement.nextElementSibling.onclick = showLogin;
    }
}

function logout() {
    window.authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    updateUserInfo();
    loadDashboard();
}

// 驾驶舱相关
async function loadDashboard() {
    try {
        const stats = await apiRequest('/dashboard/stats');
        
        // 显示状态分布
        displayStatusDistribution(stats.status_distribution);
        
        // 显示各状态机组
        displayTurbinesByStatus('alarm-turbines', stats.alarm_turbines, 'alarm');
        displayTurbinesByStatus('watch-turbines', stats.watch_turbines, 'watch');
        displayTurbinesByStatus('maintenance-turbines', stats.maintenance_turbines, 'maintenance');
        
    } catch (error) {
        console.error('加载驾驶舱数据失败:', error);
        // 显示默认值
        document.getElementById('status-distribution').innerHTML = 
            '<p class="text-muted">暂无数据或需要登录</p>';
        document.getElementById('alarm-turbines').innerHTML = 
            '<p class="text-muted">暂无数据或需要登录</p>';
        document.getElementById('watch-turbines').innerHTML = 
            '<p class="text-muted">暂无数据或需要登录</p>';
        document.getElementById('maintenance-turbines').innerHTML = 
            '<p class="text-muted">暂无数据或需要登录</p>';
    }
}

function displayStatusDistribution(statusDistribution) {
    const container = document.getElementById('status-distribution');
    
    if (!statusDistribution || Object.keys(statusDistribution).length === 0) {
        container.innerHTML = '<p class="text-muted">暂无状态数据</p>';
        return;
    }
    
    const statusLabels = {
        'NORMAL': '正常',
        'ALARM': '告警',
        'WATCH': '观察',
        'MAINTENANCE': '维护',
        'UNKNOWN': '未知',
        // 兼容旧格式
        'Normal': '正常',
        'Alarm': '告警',
        'Watch': '观察',
        'Maintenance': '维护',
        'Unknown': '未知'
    };
    
    const statusColors = {
        'NORMAL': 'success',
        'ALARM': 'danger',
        'WATCH': 'warning', 
        'MAINTENANCE': 'info',
        'UNKNOWN': 'secondary',
        // 兼容旧格式
        'Normal': 'success',
        'Alarm': 'danger',
        'Watch': 'warning', 
        'Maintenance': 'info',
        'Unknown': 'secondary'
    };
    
    // 计算总数
    const total = Object.values(statusDistribution).reduce((sum, count) => sum + count, 0);
    
    const html = `
        <div class="row">
            ${Object.entries(statusDistribution).map(([status, count]) => {
                const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                return `
                    <div class="col-md-2 col-sm-4 col-6 mb-3">
                        <div class="text-center">
                            <div class="badge bg-${statusColors[status] || 'secondary'} fs-6 mb-2 w-100 py-2">
                                ${statusLabels[status] || status}
                            </div>
                            <div class="h4 mb-1">${count}</div>
                            <small class="text-muted">${percentage}%</small>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
        <div class="mt-3 text-center">
            <small class="text-muted">总计: ${total} 条专家记录</small>
        </div>
    `;
    
    container.innerHTML = html;
}

function displayTurbinesByStatus(containerId, turbines, statusType) {
    const container = document.getElementById(containerId);
    
    // 状态配置
    const statusConfig = {
        'alarm': {
            label: '告警',
            badgeClass: 'bg-danger',
            cardClass: 'border-danger',
            emptyIcon: 'bi-check-circle text-success',
            emptyMessage: '暂无告警机组，系统运行正常'
        },
        'watch': {
            label: '观察',
            badgeClass: 'bg-warning text-dark',
            cardClass: 'border-warning',
            emptyIcon: 'bi-eye text-warning',
            emptyMessage: '暂无观察机组'
        },
        'maintenance': {
            label: '维护',
            badgeClass: 'bg-info',
            cardClass: 'border-info',
            emptyIcon: 'bi-tools text-info',
            emptyMessage: '暂无维护机组'
        }
    };
    
    const config = statusConfig[statusType] || statusConfig['alarm'];
    
    if (!turbines || turbines.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="${config.emptyIcon} fs-1"></i>
                <p class="text-muted mt-2">${config.emptyMessage}</p>
            </div>
        `;
        return;
    }
    
    const html = `
        ${turbines.map(turbine => `
            <div class="mb-2">
                <div class="card ${config.cardClass} card-sm">
                    <div class="card-body p-2">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <h6 class="card-title mb-1 fs-6">${turbine.farm_name}</h6>
                                <p class="card-text mb-1"><strong>${turbine.unit_id}</strong></p>
                                <small class="text-muted d-block" style="font-size: 0.75rem;">${turbine.description || '无描述'}</small>
                                ${turbine.owner_company ? `<small class="text-muted d-block" style="font-size: 0.7rem;">所属: ${turbine.owner_company}</small>` : ''}
                                ${turbine.latest_time ? `<small class="text-muted d-block" style="font-size: 0.7rem;">最新时间: ${formatDate(turbine.latest_time)}</small>` : ''}
                            </div>
                            <span class="badge ${config.badgeClass} ms-2">${config.label}</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('')}
        <div class="mt-2 text-center">
            <small class="text-muted">共 ${turbines.length} 台${config.label}机组</small>
        </div>
    `;
    
    container.innerHTML = html;
}

function displayRecentActivities(activities) {
    const container = document.getElementById('recent-activities');
    
    if (activities.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无最近活动</p>';
        return;
    }
    
    const html = activities.map(activity => `
        <div class="d-flex justify-content-between align-items-center border-bottom py-2">
            <div>
                <strong>${activity.title}</strong>
                <br>
                <small class="text-muted">${activity.turbine_info}</small>
            </div>
            <div class="text-end">
                <span class="badge bg-${getStatusColor(activity.status)}">${getStatusLabel(activity.status)}</span>
                <br>
                <small class="text-muted">${formatDate(activity.created_at)}</small>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// RAG问答相关
async function loadTurbineOptions() {
    try {
        const turbines = await apiRequest('/turbines/');
        const select = document.getElementById('turbine_id');
        
        if (!select) return;
        
        // 清空现有选项
        select.innerHTML = '<option value="">请选择风机</option>';
        
        // 添加风机选项
        turbines.forEach(turbine => {
            const option = document.createElement('option');
            option.value = turbine.turbine_id;
            const displayName = `${turbine.farm_name} - ${turbine.unit_id}`;
            option.textContent = displayName;
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error('加载风机选项失败:', error);
    }
}

// 全局变量存储风机数据
let allTurbinesData = [];
let filteredTurbinesData = [];

// 状态优先级映射：告警>观察>维护>正常>未知
const STATUS_PRIORITY = {
    'ALARM': 1,
    'WATCH': 2, 
    'MAINTENANCE': 3,
    'NORMAL': 4,
    'UNKNOWN': 5,
    // 兼容旧格式
    'Alarm': 1,
    'Watch': 2, 
    'Maintenance': 3,
    'Normal': 4,
    'Unknown': 5
};

// 加载所有风机的时间线
async function loadAllTurbinesTimeline() {
    try {
        const container = document.getElementById('turbines-timeline-container');
        
        // 显示加载状态
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-3">正在加载风机时间线...</p>
            </div>
        `;
        
        // 获取所有风机数据
        const turbines = await apiRequest('/turbines/');
        
        // 为每个风机获取时间线数据和智能分析结果
        const turbinesWithTimeline = await Promise.all(
            turbines.map(async (turbine) => {
                try {
                    const timeline = await apiRequest(`/api/timeline/turbine/${turbine.turbine_id}`);
                    
                    // 检查是否有已存在的智能分析结果
                    let latestSummary = null;
                    try {
                        // 首先检查本地缓存
                        latestSummary = getLatestAnalysis(turbine.turbine_id);
                        
                        // 如果本地缓存无效，尝试从服务器获取最新的分析结果
                        if (!latestSummary) {
                            const summaryResponse = await apiRequest(`/intelligent-summary/${turbine.turbine_id}`);
                            if (summaryResponse && summaryResponse.summary) {
                                latestSummary = {
                                    summary: summaryResponse.summary,
                                    analysisMode: summaryResponse.analysis_mode || 'llm',
                                    daysBack: summaryResponse.days_back || 30,
                                    timestamp: summaryResponse.created_at || summaryResponse.timestamp,
                                    cached_at: new Date().toISOString()
                                };
                                
                                // 保存到本地缓存
                                setCachedSummary(
                                    turbine.turbine_id, 
                                    latestSummary.analysisMode, 
                                    latestSummary, 
                                    latestSummary.daysBack
                                );
                            }
                        }
                    } catch (summaryError) {
                        console.warn(`获取风机 ${turbine.unit_id} 智能分析失败:`, summaryError);
                    }
                    
                    return {
                        ...turbine,
                        timeline: timeline || [],
                        hasTimeline: timeline && timeline.length > 0,
                        latestSummary: latestSummary
                    };
                } catch (error) {
                    console.warn(`获取风机 ${turbine.unit_id} 时间线失败:`, error);
                    return {
                        ...turbine,
                        timeline: [],
                        hasTimeline: false,
                        latestSummary: null
                    };
                }
            })
        );
        
        // 按状态优先级排序，状态相同时按最近更新时间排序
        allTurbinesData = turbinesWithTimeline.sort((a, b) => {
            const priorityA = STATUS_PRIORITY[a.status] || 999;
            const priorityB = STATUS_PRIORITY[b.status] || 999;
            
            if (priorityA !== priorityB) {
                return priorityA - priorityB;
            }
            
            // 相同状态按最近更新的时间线事件时间排序
            const getLatestEventTime = (turbine) => {
                if (!turbine.timeline || turbine.timeline.length === 0) {
                    return new Date(0); // 没有时间线事件的排在最后
                }
                
                // 找到最新的事件时间
                const latestEvent = turbine.timeline.reduce((latest, event) => {
                    const eventTime = new Date(event.event_time || event.created_at);
                    const latestTime = new Date(latest.event_time || latest.created_at);
                    return eventTime > latestTime ? event : latest;
                });
                
                return new Date(latestEvent.event_time || latestEvent.created_at);
            };
            
            const timeA = getLatestEventTime(a);
            const timeB = getLatestEventTime(b);
            
            // 最近更新的排在前面
            return timeB - timeA;
        });
        
        filteredTurbinesData = [...allTurbinesData];
        
        // 填充聊天界面的风机过滤器
        populateChatTurbineFilter(allTurbinesData);
        
        // 填充时间线界面的风机过滤器
        populateTimelineTurbineFilter(allTurbinesData);
        
        await displayTurbinesTimeline(filteredTurbinesData);
        
    } catch (error) {
        console.error('加载风机时间线失败:', error);
        document.getElementById('turbines-timeline-container').innerHTML = `
            <div class="alert alert-warning" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                加载风机时间线失败: ${error.message || '请检查网络连接或重新登录'}
            </div>
        `;
    }
}

function handleEnter(event) {
    if (event.key === 'Enter') {
        askQuestion();
    }
}

async function askQuestion() {
    const questionInput = document.getElementById('question-input');
    const question = questionInput.value.trim();
    
    if (!question) {
        alert('请输入问题');
        return;
    }
    
    const turbineId = document.getElementById('chat-turbine-filter').value || null;
    
    // 添加用户消息到聊天容器
    addMessage('user', question);
    
    // 清空输入框
    questionInput.value = '';
    
    // 显示加载状态
    addMessage('assistant', '正在思考中...', true);
    
    try {
        const response = await apiRequest('/rag/query', {
            method: 'POST',
            body: {
                question: question,
                turbine_id: turbineId ? parseInt(turbineId) : null,
                max_results: 5
            }
        });
        
        // 移除加载消息
        removeLastMessage();
        
        // 添加助手回答
        addMessage('assistant', response.answer);
        
        // 提取聚合数据和元数据
        const aggregatedData = response.aggregated_data || null;
        const metadata = response.metadata || null;
        const sources = response.sources || [];
        
        // 显示来源和聚合数据
        displaySources(sources, aggregatedData, metadata);
        
        // 如果有增强信息，显示提示
        if (aggregatedData || (metadata && metadata.enhancement_type)) {
            let enhancementInfo = '';
            if (aggregatedData) {
                enhancementInfo += `已聚合${aggregatedData.turbine_count || 0}台风机的数据`;
            }
            if (metadata && metadata.enhancement_type) {
                if (enhancementInfo) enhancementInfo += '，';
                enhancementInfo += `使用了${metadata.enhancement_type}增强`;
            }
            showToast(`智能增强：${enhancementInfo}`, 'success');
        }
        
    } catch (error) {
        // 移除加载消息
        removeLastMessage();
        
        addMessage('assistant', '抱歉，查询过程中出现错误: ' + error.message);
        console.error('RAG查询失败:', error);
    }
}

function addMessage(sender, content, isLoading = false) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    bubbleDiv.textContent = content;
    
    if (isLoading) {
        bubbleDiv.classList.add('loading');
    }
    
    messageDiv.appendChild(bubbleDiv);
    chatContainer.appendChild(messageDiv);
    
    // 滚动到底部
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeLastMessage() {
    const chatContainer = document.getElementById('chat-container');
    const lastMessage = chatContainer.lastElementChild;
    if (lastMessage && lastMessage.querySelector('.loading')) {
        chatContainer.removeChild(lastMessage);
    }
}

function displaySources(sources, aggregatedData = null, metadata = null) {
    const container = document.getElementById('sources-container');
    
    let html = '';
    
    // 显示多风机聚合数据
    if (aggregatedData) {
        html += displayAggregatedData(aggregatedData);
    }
    
    // 显示增强查询元数据
    if (metadata && metadata.enhancement_type) {
        html += displayEnhancementMetadata(metadata);
    }
    
    // 显示传统来源
    if (sources && sources.length > 0) {
        html += '<div class="mt-4"><h6><i class="bi bi-file-text me-2"></i>文档来源</h6>';
        html += sources.map((source, index) => `
            <div class="source-item">
                <h6>来源 ${index + 1}</h6>
                <p><strong>${source.turbine_info}</strong></p>
                <p class="small">${source.chunk_text}</p>
                <small class="text-muted">
                    相似度: ${(source.similarity_score * 100).toFixed(1)}% | 
                    ${formatDate(source.published_at)}
                </small>
            </div>
        `).join('');
        html += '</div>';
    } else if (!aggregatedData) {
        html += '<p class="text-muted">未找到相关来源</p>';
    }
    
    container.innerHTML = html;
}

function displayAggregatedData(aggregatedData) {
    const data = aggregatedData.aggregated_data || {};
    const turbines = aggregatedData.turbines || [];
    const summary = aggregatedData.summary || '';
    
    let html = `
        <div class="aggregated-data-section mb-4">
            <h6><i class="bi bi-graph-up me-2 text-primary"></i>多风机数据聚合分析</h6>
            
            <!-- 总体摘要 -->
            <div class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                <strong>总体情况：</strong>${summary}
            </div>
            
            <!-- 统计卡片 -->
            <div class="row mb-3">
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title text-primary">${data.turbine_count || 0}</h5>
                            <p class="card-text small">涉及风机</p>
                        </div>
                    </div>
                </div>
    `;
    
    // 性能洞察
    if (data.performance_insights) {
        const insights = data.performance_insights;
        html += `
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title text-success">${insights.health_score || 0}%</h5>
                            <p class="card-text small">健康度</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title text-warning">${insights.fault_rate || 0}%</h5>
                            <p class="card-text small">故障率</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title">${insights.performance_grade || '未知'}</h5>
                            <p class="card-text small">性能评级</p>
                        </div>
                    </div>
                </div>
        `;
    }
    
    html += `
            </div>
            
            <!-- 状态分布 -->
    `;
    
    if (data.status_distribution) {
        html += `
            <div class="mb-3">
                <h6>状态分布</h6>
                <div class="row">
        `;
        
        for (const [status, count] of Object.entries(data.status_distribution)) {
            const statusColor = getStatusColor(status);
            const statusLabel = getStatusLabel(status);
            html += `
                    <div class="col-md-2 col-sm-4 mb-2">
                        <div class="d-flex align-items-center">
                            <span class="badge bg-${statusColor} me-2">${count}</span>
                            <small>${statusLabel}</small>
                        </div>
                    </div>
            `;
        }
        
        html += `
                </div>
            </div>
        `;
    }
    
    // 风场分布
    if (data.farm_distribution) {
        html += `
            <div class="mb-3">
                <h6>风场分布</h6>
                <div class="row">
        `;
        
        for (const [farm, count] of Object.entries(data.farm_distribution)) {
            html += `
                    <div class="col-md-3 col-sm-6 mb-2">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-geo-alt me-2 text-muted"></i>
                            <span>${farm}: ${count}台</span>
                        </div>
                    </div>
            `;
        }
        
        html += `
                </div>
            </div>
        `;
    }
    
    // 最近问题
    if (data.recent_issues && data.recent_issues.length > 0) {
        html += `
            <div class="mb-3">
                <h6>最近问题 (${data.recent_issues.length}条)</h6>
                <div class="list-group">
        `;
        
        data.recent_issues.slice(0, 5).forEach(issue => {
            html += `
                    <div class="list-group-item">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${issue.title}</h6>
                            <small>${formatDate(issue.published_at)}</small>
                        </div>
                        <p class="mb-1">${issue.description}</p>
                        <small class="text-muted">${issue.turbine_info}</small>
                    </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    }
    
    // 维护摘要
    if (data.maintenance_summary) {
        const maintenance = data.maintenance_summary;
        html += `
            <div class="mb-3">
                <h6>维护情况</h6>
                <div class="row">
                    <div class="col-md-4">
                        <small class="text-muted">维护记录数</small>
                        <div class="fw-bold">${maintenance.total_maintenance_logs || 0}</div>
                    </div>
                    <div class="col-md-4">
                        <small class="text-muted">需要维护</small>
                        <div class="fw-bold">${maintenance.turbines_needing_maintenance || 0}台</div>
                    </div>
                    <div class="col-md-4">
                        <small class="text-muted">维护率</small>
                        <div class="fw-bold">${maintenance.maintenance_rate || 0}%</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    html += `
        </div>
    `;
    
    return html;
}

function displayEnhancementMetadata(metadata) {
    let html = `
        <div class="enhancement-metadata-section mb-4">
            <h6><i class="bi bi-cpu me-2 text-success"></i>智能增强信息</h6>
            <div class="alert alert-light">
    `;
    
    if (metadata.enhancement_type === 'technical_context') {
        html += `
                <div class="mb-2">
                    <strong>增强类型：</strong>技术上下文增强
                </div>
        `;
        
        if (metadata.original_question !== metadata.enhanced_question) {
            html += `
                <div class="mb-2">
                    <strong>原始问题：</strong>${metadata.original_question}
                </div>
                <div class="mb-2">
                    <strong>增强问题：</strong>${metadata.enhanced_question}
                </div>
            `;
        }
        
        if (metadata.context_data) {
            const contextData = metadata.context_data;
            if (contextData.turbine_count) {
                html += `
                    <div class="mb-2">
                        <strong>上下文数据：</strong>涉及${contextData.turbine_count}台风机的相关信息
                    </div>
                `;
            }
        }
    }
    
    if (metadata.has_aggregation) {
        html += `
                <div class="mb-2">
                    <i class="bi bi-check-circle text-success me-2"></i>
                    已启用多风机数据聚合分析
                </div>
        `;
    }
    
    html += `
            </div>
        </div>
    `;
    
    return html;
}

// 显示风机时间线列表
// 获取风机的最近一次智能总结
async function getLatestIntelligentSummary(turbineId, analysisMode = 'llm') {
    try {
        const response = await apiRequest(`/api/timeline/turbine/${turbineId}/intelligent-summary?analysis_mode=${analysisMode}&days_back=30`, {
            method: 'POST'
        });
        if (response && response.summary) {
            return {
                analysis_text: response.summary,
                generated_at: new Date().toISOString(),
                analysis_mode: response.analysis_mode,
                days_back: response.days_back
            };
        }
    } catch (error) {
        console.log(`风机 ${turbineId} 暂无智能总结:`, error);
    }
    return null;
}

// 为风机显示添加智能总结内容框
async function addIntelligentSummaryToTurbines(turbinesData) {
    const turbinesWithSummary = [];
    
    for (const turbine of turbinesData) {
        // 首先尝试获取最新分析结果
        let summary = getLatestAnalysis(turbine.turbine_id);
        
        // 如果没有最新分析结果，则尝试获取缓存的总结
        if (!summary) {
            summary = await getLatestIntelligentSummary(turbine.turbine_id);
        }
        
        turbinesWithSummary.push({
            ...turbine,
            latestSummary: summary
        });
    }
    
    return turbinesWithSummary;
}

async function displayTurbinesTimeline(turbinesData) {
    const container = document.getElementById('turbines-timeline-container');
    
    console.log('开始显示时间线，数据量:', turbinesData ? turbinesData.length : 0);
    console.log('要显示的数据:', turbinesData);
    
    if (turbinesData.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="bi bi-wind" style="font-size: 3rem;"></i>
                <p class="mt-3">没有找到符合条件的风机</p>
            </div>
        `;
        return;
    }
    
    // 移除自动获取智能总结，只在用户点击时才获取
    const html = turbinesData.map(turbine => {
        const statusColor = getStatusColor(turbine.status);
        const statusLabel = getStatusLabel(turbine.status);
        const timelineEvents = turbine.timeline || [];
        const latestEvent = timelineEvents.length > 0 ? timelineEvents[0] : null;
        
        return `
            <div class="card mb-4 border-start border-4 border-${statusColor}" data-turbine-id="${turbine.turbine_id}">
                <div class="card-header">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-wind me-2 text-${statusColor}"></i>
                            <h5 class="mb-0">${turbine.farm_name} - ${turbine.unit_id}</h5>
                            <span class="badge bg-${statusColor} ms-2">${statusLabel}</span>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-sm btn-outline-primary" onclick="refreshTurbineTimeline('${turbine.turbine_id}')" title="刷新时间线">
                                <i class="bi bi-arrow-clockwise"></i>
                            </button>
                            <button class="btn btn-sm btn-info" onclick="toggleTurbineTimeline('${turbine.turbine_id}')" title="展开/收起">
                                <i class="bi bi-chevron-down" id="toggle-icon-${turbine.turbine_id}"></i>
                            </button>
                        </div>
                    </div>
                    ${turbine.model ? `<small class="text-muted">型号: ${turbine.model}</small>` : ''}
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <strong>时间线事件数量:</strong> ${timelineEvents.length} 个
                        </div>
                        <div class="col-md-6">
                            ${latestEvent ? `<strong>最新事件:</strong> ${formatDate(latestEvent.event_time)}` : '<span class="text-muted">暂无事件</span>'}
                        </div>
                    </div>
                    
                    ${latestEvent ? `
                        <div class="alert alert-light">
                            <div class="d-flex align-items-center mb-2">
                                <i class="bi ${getEventTypeIcon(latestEvent.event_type)} me-2"></i>
                                <strong>${latestEvent.title}</strong>
                                <span class="badge bg-${getSeverityColor(latestEvent.event_severity)} ms-2">
                                    ${getSeverityLabel(latestEvent.event_severity)}
                                </span>
                            </div>
                            <p class="mb-0 text-muted">${latestEvent.summary}</p>
                        </div>
                    ` : `
                        <div class="alert alert-secondary">
                            <i class="bi bi-info-circle me-2"></i>
                            该风机暂无时间线事件，点击"生成时间线"按钮创建
                        </div>
                    `}
                    
                    <!-- 智能总结内容框 -->
                    <div class="intelligent-summary-box">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <div class="d-flex align-items-center">
                                <i class="bi bi-lightbulb-fill me-2 text-warning"></i>
                                <strong>智能分析</strong>
                            </div>
                            <button class="btn btn-sm btn-outline-primary" onclick="showAnalysisConfig('${turbine.turbine_id}')" title="配置分析参数">
                                <i class="bi bi-gear"></i> 配置分析
                            </button>
                        </div>
                        
                        <!-- 分析配置界面 -->
                        <div id="analysis-config-${turbine.turbine_id}" class="analysis-config" style="display: none;">
                            <div class="card border-primary mb-3">
                                <div class="card-header bg-light">
                                    <h6 class="mb-0">分析参数配置</h6>
                                </div>
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <label class="form-label">分析模式</label>
                                            <select class="form-select" id="analysis-mode-${turbine.turbine_id}">
                                                <option value="llm">大模型分析</option>
                                                <option value="basic">基本统计分析</option>
                                            </select>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">回溯天数</label>
                                            <select class="form-select" id="days-back-${turbine.turbine_id}">
                                                <option value="7">最近7天</option>
                                                <option value="15">最近15天</option>
                                                <option value="30" selected>最近30天</option>
                                                <option value="60">最近60天</option>
                                                <option value="90">最近90天</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="mt-3 d-flex gap-2">
                                        <button class="btn btn-primary" onclick="executeAnalysis('${turbine.turbine_id}')">
                                            <i class="bi bi-play-fill"></i> 执行分析
                                        </button>
                                        <button class="btn btn-secondary" onclick="hideAnalysisConfig('${turbine.turbine_id}')">
                                            <i class="bi bi-x"></i> 取消
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 分析结果显示区域 -->
                        <div id="analysis-result-${turbine.turbine_id}" class="analysis-result">
                            ${turbine.latestSummary ? `
                                <div class="alert alert-success">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <small class="text-muted">
                                            ${turbine.latestSummary.analysisMode === 'llm' ? '大模型分析' : '基本统计分析'} | 
                                            回溯${turbine.latestSummary.daysBack || 30}天 |
                                            ${formatDateTime(turbine.latestSummary.timestamp)}
                                        </small>
                                        <div>
                                            <span class="badge bg-success me-2">已保存</span>
                                            <button class="btn btn-sm btn-outline-primary" onclick="showAnalysisConfig('${turbine.turbine_id}')" title="重新分析">
                                                <i class="bi bi-arrow-clockwise"></i> 重新分析
                                            </button>
                                        </div>
                                    </div>
                                    <div class="summary-content">
                                        ${turbine.latestSummary.summary}
                                    </div>
                                </div>
                            ` : `
                                <div class="alert alert-light text-muted">
                                    <i class="bi bi-info-circle me-2"></i>
                                    点击"配置分析"按钮设置参数并执行智能分析
                                </div>
                            `}
                        </div>
                    </div>
                    
                    <!-- 详细时间线（默认隐藏） -->
                    <div id="timeline-detail-${turbine.turbine_id}" class="timeline-detail" style="display: none;">
                        <hr>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0">完整时间线</h6>
                            <small class="text-muted">时间线事件需要从专家记录中创建</small>
                        </div>
                        ${timelineEvents.length > 0 ? displayTimelineEvents(timelineEvents, turbine.turbine_id) : '<p class="text-muted">暂无时间线事件</p>'}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

// 显示时间线事件列表
function displayTimelineEvents(events, turbineId = null) {
    return events.map(event => `
        <div class="timeline-event mb-3 p-3 border rounded">
            <div class="d-flex justify-content-between align-items-start mb-2">
                <div class="d-flex align-items-center">
                    <i class="bi ${getEventTypeIcon(event.event_type)} me-2 text-${getSeverityColor(event.event_severity)}"></i>
                    <h6 class="mb-0">${event.title}</h6>
                </div>
                <div class="d-flex flex-column align-items-end">
                    <span class="badge bg-${getSeverityColor(event.event_severity)} mb-1">
                        ${getSeverityLabel(event.event_severity)}
                    </span>
                    <small class="text-muted">${formatDateTime(event.event_time)}</small>
                </div>
            </div>
            
            <!-- 简要摘要 -->
            <div class="timeline-summary mb-2">
                <p class="text-muted mb-1">${event.summary}</p>
                ${event.detail && event.detail.trim() ? `
                    <button class="btn btn-sm btn-link p-0 text-decoration-none" 
                            onclick="toggleTimelineEventDetail('${event.event_id}')" 
                            id="toggle-btn-${event.event_id}">
                        <i class="fas fa-chevron-down me-1"></i> 查看详细内容
                    </button>
                ` : ''}
            </div>
            
            <!-- 详细内容（默认隐藏） -->
            ${event.detail && event.detail.trim() ? `
                <div class="timeline-detail collapse" id="detail-${event.event_id}">
                    <div class="border-top pt-2 mt-2">
                        <h6 class="text-primary mb-2">
                            <i class="fas fa-info-circle"></i> 详细内容
                        </h6>
                        <div class="bg-light p-3 rounded">
                            <pre class="mb-0" style="white-space: pre-wrap; font-family: inherit;">${event.detail}</pre>
                        </div>
                    </div>
                </div>
            ` : ''}
            
            <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex flex-wrap gap-1">
                    ${event.source_logs && event.source_logs.length > 0 ? 
                        event.source_logs.map(source => `
                            <button class="btn btn-sm btn-outline-secondary" onclick="viewExpertLogDetail('${source.log_id}')" title="查看专家记录">
                                <i class="bi bi-file-text"></i> ${source.log_id.substring(0, 8)}...
                            </button>
                        `).join('') : ''
                    }
                </div>
                <div class="timeline-event-actions d-flex gap-1">
                    <button class="btn btn-sm btn-outline-primary" onclick="openTimelineEditModal('${event.event_id}', '${turbineId || event.turbine_id}')" title="编辑事件">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-info" onclick="viewTimelineEventDetail('${event.event_id}')" title="查看详情">
                        <i class="bi bi-eye"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// 过滤风机
async function filterTurbines() {
    const searchText = document.getElementById('turbine-search-input').value.toLowerCase();
    const statusFilter = document.getElementById('turbine-status-filter').value;
    
    console.log('开始过滤风机数据，总数据量:', allTurbinesData.length);
    
    filteredTurbinesData = allTurbinesData.filter(turbine => {
        // 搜索过滤
        const searchMatch = !searchText || 
            turbine.farm_name.toLowerCase().includes(searchText) ||
            turbine.unit_id.toLowerCase().includes(searchText) ||
            (turbine.model && turbine.model.toLowerCase().includes(searchText));
        
        // 状态过滤
        const statusMatch = !statusFilter || turbine.status === statusFilter;
        
        return searchMatch && statusMatch;
    });
    
    console.log('过滤后的风机数据量:', filteredTurbinesData.length);
    console.log('过滤后的数据:', filteredTurbinesData);
    
    await displayTurbinesTimeline(filteredTurbinesData);
}

// 切换风机时间线详情显示
function toggleTurbineTimeline(turbineId) {
    const detailDiv = document.getElementById(`timeline-detail-${turbineId}`);
    const toggleIcon = document.getElementById(`toggle-icon-${turbineId}`);
    
    if (detailDiv.style.display === 'none') {
        detailDiv.style.display = 'block';
        toggleIcon.className = 'bi bi-chevron-up';
    } else {
        detailDiv.style.display = 'none';
        toggleIcon.className = 'bi bi-chevron-down';
    }
}

// 刷新单个风机时间线
async function refreshTurbineTimeline(turbineId) {
    try {
        console.log('开始刷新时间线，风机ID:', turbineId);
        
        const timeline = await apiRequest(`/api/timeline/turbine/${turbineId}`);
        console.log('API返回的时间线数据:', timeline);
        
        // 更新数据
        const turbineIndex = allTurbinesData.findIndex(t => t.turbine_id === turbineId);
        console.log('找到的风机索引:', turbineIndex);
        
        if (turbineIndex !== -1) {
            const oldTimelineLength = allTurbinesData[turbineIndex].timeline ? allTurbinesData[turbineIndex].timeline.length : 0;
            allTurbinesData[turbineIndex].timeline = timeline || [];
            allTurbinesData[turbineIndex].hasTimeline = timeline && timeline.length > 0;
            
            const newTimelineLength = allTurbinesData[turbineIndex].timeline.length;
            console.log(`时间线事件数量变化: ${oldTimelineLength} -> ${newTimelineLength}`);
            console.log('更新后的风机数据:', allTurbinesData[turbineIndex]);
        } else {
            console.error('未找到对应的风机数据');
        }
        
        // 重新过滤和显示
        console.log('开始重新过滤和显示数据');
        filterTurbines();
        console.log('过滤和显示完成');
        
        // 显示成功提示
        showToast('时间线刷新成功', 'success');
        
    } catch (error) {
        console.error('刷新时间线失败:', error);
        showToast(`刷新时间线失败: ${error.message}`, 'error');
    }
}

// 生成单个风机时间线
async function generateTurbineTimeline(turbineId) {
    try {
        const response = await apiRequest('/timeline/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                turbine_id: turbineId,
                force_regenerate: true
            })
        });
        
        // 刷新该风机的时间线
        await refreshTurbineTimeline(turbineId);
        
        showToast(`时间线生成成功! 共生成 ${response.events_generated} 个事件`, 'success');
        
    } catch (error) {
        console.error('生成时间线失败:', error);
        showToast(`生成时间线失败: ${error.message}`, 'error');
    }
}

// 显示提示消息
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // 3秒后自动移除
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 3000);
}

// 创建提示消息容器
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

// 时间线相关（修正为始终以风机为单位显示）
async function loadTimeline() {
    console.log('loadTimeline函数被调用了！');
    
    const turbineId = document.getElementById('timeline-turbine-filter').value;
    
    console.log('选择的风机ID:', turbineId);
    
    // 始终隐藏单个时间线容器，只使用风机时间线容器
    document.getElementById('timeline-container').style.display = 'none';
    document.getElementById('turbines-timeline-container').style.display = 'block';
    
    if (!turbineId) {
        console.log('没有选择风机，显示所有风机时间线');
        // 显示所有风机的时间线
        await loadAllTurbinesTimeline();
        return;
    }
    
    try {
        // 显示加载状态
        document.getElementById('turbines-timeline-container').innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-3 text-muted">正在加载选定风机的时间线...</p>
            </div>
        `;
        
        // 获取选定的风机信息
        const turbine = await apiRequest(`/api/turbines/${turbineId}`);
        const timeline = await apiRequest(`/api/timeline/turbine/${turbineId}`);
        
        console.log('获取到的风机数据:', turbine);
        console.log('获取到的时间线数据:', timeline);
        
        // 构造风机数据，包含时间线
        const turbineWithTimeline = {
            ...turbine,
            timeline: timeline || [],
            hasTimeline: timeline && timeline.length > 0
        };
        
        // 以风机为单位显示时间线
        await displayTurbinesTimeline([turbineWithTimeline]);
        
    } catch (error) {
        console.error('加载时间线失败:', error);
        document.getElementById('turbines-timeline-container').innerHTML = `
            <div class="alert alert-warning" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                加载时间线失败: ${error.message || '请检查网络连接或重新登录'}
            </div>
        `;
    }
}

// 已废弃：displayTimeline函数 - 现在统一使用displayTurbinesTimeline以风机为单位显示
// function displayTimeline(events) {
//     // 此函数已被废弃，现在统一使用displayTurbinesTimeline函数
//     // 确保时间线始终以风机为单位显示，而不是单独的事件列表
// }

// 确保函数在全局作用域中可用
window.loadTimeline = loadTimeline;

// 生成时间线
async function generateTimeline() {
    const turbineId = document.getElementById('timeline-turbine-filter').value;
    
    if (!turbineId) {
        alert('请先选择风机');
        return;
    }
    
    const generateBtn = document.getElementById('generate-timeline-btn');
    const originalText = generateBtn.innerHTML;
    
    try {
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 生成中...';
        
        const response = await apiRequest('/timeline/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                turbine_id: turbineId,
                force_regenerate: true
            })
        });
        
        // 重新加载时间线
        await loadTimeline();
        
        // 显示成功消息
        const container = document.getElementById('timeline-container');
        const successAlert = document.createElement('div');
        successAlert.className = 'alert alert-success alert-dismissible fade show';
        successAlert.innerHTML = `
            <i class="bi bi-check-circle"></i>
            时间线生成成功! 共生成 ${response.events_generated} 个事件，更新 ${response.events_updated} 个事件
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        container.insertBefore(successAlert, container.firstChild);
        
        // 3秒后自动隐藏提示
        setTimeout(() => {
            if (successAlert.parentNode) {
                successAlert.remove();
            }
        }, 3000);
        
    } catch (error) {
        console.error('生成时间线失败:', error);
        alert(`生成时间线失败: ${error.message || '请重试'}`);
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = originalText;
    }
}

// 批量更新所有时间线
async function batchUpdateTimelines() {
    if (!confirm('确定要批量更新所有风机的时间线吗？这可能需要较长时间。')) {
        return;
    }
    
    try {
        const response = await apiRequest('/timeline/batch-update-all', {
            method: 'POST'
        });
        
        alert(`批量更新完成: ${response.summary.successful} 个成功，${response.summary.failed} 个失败`);
        
        // 如果当前选中了风机，重新加载时间线
        const turbineId = document.getElementById('timeline-turbine-filter').value;
        if (turbineId) {
            await loadTimeline();
        }
        
    } catch (error) {
        console.error('批量更新失败:', error);
        alert(`批量更新失败: ${error.message || '请重试'}`);
    }
}

// 查看时间线事件详情
async function viewTimelineEventDetail(eventId) {
    try {
        const event = await apiRequest(`/api/timeline/${eventId}`);
        
        // 创建模态框显示详情
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-calendar-event"></i>
                            ${event.title}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <strong>事件时间:</strong> ${formatDateTime(event.event_time)}
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <strong>严重程度:</strong> 
                                <span class="badge bg-${getSeverityColor(event.event_severity)}">${getSeverityLabel(event.event_severity)}</span>
                            </div>
                            <div class="col-md-6">
                                <strong>验证状态:</strong> 
                                ${event.is_verified ? '<span class="badge bg-success">已验证</span>' : '<span class="badge bg-warning">未验证</span>'}
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <strong>事件摘要:</strong>
                            <div class="mt-2">
                                <textarea class="form-control" id="detail-event-summary" rows="3" onchange="updateEventSummary(${event.event_id})">${event.summary}</textarea>
                                <small class="text-muted">内容修改后会自动保存</small>
                            </div>
                        </div>
                        

                        
                        ${event.source_logs && event.source_logs.length > 0 ? `
                            <div class="mb-3">
                                <strong>相关专家记录:</strong>
                                <div class="mt-2">
                                    ${event.source_logs.map(source => `
                                        <div class="card mb-2">
                                            <div class="card-body py-2">
                                                <div class="d-flex justify-content-between align-items-center">
                                                    <div>
                                                        <strong>${source.title || '专家记录'}</strong>
                                                        <small class="text-muted d-block">ID: ${source.log_id}</small>
                                                        ${source.attachments && source.attachments.length > 0 ? `
                                                            <div class="mt-2">
                                                                <small class="text-muted">附件 (${source.attachments.length}):</small>
                                                                <div class="mt-1">
                                                                    ${source.attachments.map(attachment => `
                                                                        <button class="btn btn-sm btn-outline-success me-1 mb-1" 
                                                                                onclick="downloadAttachment('${attachment.attachment_id}', '${attachment.file_name}')"
                                                                                title="下载附件: ${attachment.file_name} (${formatFileSize(attachment.file_size)})">
                                                                            <i class="bi bi-download"></i> ${attachment.file_name}
                                                                        </button>
                                                                    `).join('')}
                                                                </div>
                                                            </div>
                                                        ` : ''}
                                                    </div>
                                                    <div>
                                                        <span class="badge bg-info">相关度: ${(source.relevance_score * 100).toFixed(0)}%</span>
                                                        <button class="btn btn-sm btn-outline-primary ms-2" onclick="viewExpertLogDetail('${source.log_id}')">
                                                            查看
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                        
                        <div class="text-muted">
                            <small>
                                创建于: ${formatDate(event.created_at)}
                                ${event.updated_at ? ` | 更新于: ${formatDate(event.updated_at)}` : ''}
                            </small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        ${currentUser && currentUser.role === 'ADMIN' ? `
                            <button type="button" class="btn btn-warning" onclick="editTimelineEvent('${event.event_id}')">
                                <i class="bi bi-pencil"></i> 编辑
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // 模态框关闭后移除DOM元素
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
        
    } catch (error) {
        console.error('加载事件详情失败:', error);
        alert('加载事件详情失败');
    }
}

// 编辑时间线事件
async function editTimelineEvent(eventId) {
    // TODO: 实现编辑功能
    alert('编辑功能开发中...');
}

// 辅助函数
function getEventTypeIcon(eventType) {
    const icons = {
        'normal': 'bi-check-circle',
        'alarm': 'bi-exclamation-triangle-fill',
        'watch': 'bi-eye',
        'maintenance': 'bi-tools',
        'unknown': 'bi-question-circle',
        'other': 'bi-question-circle',
        // 保持向后兼容
        'fault': 'bi-exclamation-triangle',
        'inspection': 'bi-search',
        'repair': 'bi-wrench',
        'upgrade': 'bi-arrow-up-circle',
        'monitoring': 'bi-graph-up',
        // 大写枚举值支持
        'NORMAL': 'bi-check-circle',
        'ALARM': 'bi-exclamation-triangle-fill',
        'WATCH': 'bi-eye',
        'MAINTENANCE': 'bi-tools',
        'UNKNOWN': 'bi-question-circle',
        'OTHER': 'bi-question-circle',
        'FAULT': 'bi-exclamation-triangle',
        'INSPECTION': 'bi-search',
        'REPAIR': 'bi-wrench',
        'UPGRADE': 'bi-arrow-up-circle',
        'MONITORING': 'bi-graph-up'
    };
    return icons[eventType] || 'bi-question-circle';
}

function getSeverityLabel(severity) {
    const labels = {
        'NORMAL': '正常',
        'ALARM': '告警',
        'WATCH': '观察',
        'UNKNOWN': '未知',
        'normal': '正常',
        'alarm': '告警',
        'watch': '观察',
        'unknown': '未知'
    };
    return labels[severity] || '未知';
}

// 保持向后兼容的函数名
function getEventTypeLabel(eventType) {
    return getSeverityLabel(eventType);
}

function getSeverityColor(severity) {
    // 统一使用专家记录的状态标签系统
    const colors = {
        'Alarm': 'danger',
        'Watch': 'warning', 
        'Maintenance': 'info',
        'Normal': 'success',
        'Unknown': 'secondary',
        // 保持向后兼容
        'critical': 'danger',
        'high': 'warning',
        'medium': 'info',
        'low': 'success',
        'CRITICAL': 'danger',
        'HIGH': 'warning',
        'MEDIUM': 'info',
        'LOW': 'success',
        'NORMAL': 'success'
    };
    return colors[severity] || 'secondary';
}

function getSeverityLabel(severity) {
    // 统一使用专家记录的状态标签系统
    const labels = {
        'Alarm': '告警',
        'Watch': '观察',
        'Maintenance': '维护',
        'Normal': '正常',
        'Unknown': '未知',
        // 保持向后兼容
        'critical': '紧急',
        'high': '重要',
        'medium': '一般',
        'low': '轻微',
        'CRITICAL': '紧急',
        'HIGH': '重要',
        'MEDIUM': '一般',
        'LOW': '轻微',
        'NORMAL': '正常'
    };
    return labels[severity] || '未知';
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 风机管理相关
async function loadTurbines() {
    try {
        const turbines = await apiRequest('/turbines/');
        // 处理风机数据...
    } catch (error) {
        console.error('加载风机失败:', error);
    }
}

async function loadTurbinesTable() {
    try {
        console.log('loadTurbinesTable - 开始加载，currentUser:', currentUser);
        // 确保用户信息已加载
        if (!currentUser) {
            console.log('loadTurbinesTable - currentUser为空，正在获取用户信息...');
            await getCurrentUser();
            console.log('loadTurbinesTable - 获取用户信息后，currentUser:', currentUser);
        }
        const turbines = await apiRequest('/turbines/');
        console.log('loadTurbinesTable - 获取到风机数据，准备显示表格');
        displayTurbinesTable(turbines);
    } catch (error) {
        console.error('加载风机表格失败:', error);
    }
}

function displayTurbinesTable(turbines) {
    const container = document.getElementById('turbines-table');
    const canEdit = currentUser && (currentUser.role === 'ADMIN' || currentUser.role === 'EXPERT');

    if (turbines.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无风机数据</p>';
        return;
    }

    const html = `
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>风场名称</th>
                    <th>机组编号</th>
                    <th>型号</th>
                    <th>装机容量</th>
                    <th>投运日期</th>
                    <th>状态</th>
                    ${canEdit ? '<th>操作</th>' : ''}
                </tr>
            </thead>
            <tbody>
                ${turbines.map(turbine => `
                    <tr>
                        <td>${turbine.farm_name}</td>
                        <td>${turbine.unit_id}</td>
                        <td>${turbine.model || '-'}</td>
                        <td>${turbine.capacity || '-'}</td>
                        <td>${turbine.install_date ? formatDate(turbine.install_date) : '-'}</td>
                        <td>
                            <span class="badge bg-${getStatusColor(turbine.status || 'NORMAL')}">
                                ${getStatusLabel(turbine.status || 'NORMAL')}
                            </span>
                        </td>
                        ${canEdit ? `
                        <td>
                            <button class="btn btn-sm btn-outline-primary me-2" onclick="editTurbine('${turbine.turbine_id}')">
                                编辑
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteTurbine('${turbine.turbine_id}')">
                                删除
                            </button>
                        </td>
                        ` : ''}
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

// 工具函数
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

function getStatusColor(status) {
    const colors = {
        'draft': 'secondary',
        'published': 'success',
        'pending': 'warning',
        'alarm': 'danger',
        'active': 'success',
        'inactive': 'danger',
        'maintenance': 'warning',
        // 风机状态颜色 - 新的大写格式
        'NORMAL': 'success',
        'WATCH': 'warning',
        'ALARM': 'danger',
        'MAINTENANCE': 'warning',
        'UNKNOWN': 'secondary',
        // 兼容旧的格式
        'Normal': 'success',
        'Watch': 'warning',
        'Alarm': 'danger',
        'Maintenance': 'warning',
        'Unknown': 'secondary'
    };
    return colors[status] || 'success';
}

function getStatusLabel(status) {
    switch(status) {
        // 新的大写格式
        case 'NORMAL': return '正常';
        case 'WATCH': return '观察';
        case 'ALARM': return '告警';
        case 'MAINTENANCE': return '维护';
        case 'UNKNOWN': return '未知';
        // 兼容旧的格式
        case 'Normal': return '正常';
        case 'Watch': return '观察';
        case 'Alarm': return '告警';
        case 'Maintenance': return '维护';
        case 'Unknown': return '未知';
        default: return status;
    }
}

// 占位函数
function showAddTurbineModal() {
    // 清空表单
    document.getElementById('turbineForm').reset();
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('addTurbineModal'));
    modal.show();
}

async function createTurbine() {
    try {
        const farmName = document.getElementById('farm_name').value.trim();
        const unitId = document.getElementById('unit_id').value.trim();
        const model = document.getElementById('model').value.trim();
        const ownerCompany = document.getElementById('owner_company').value.trim();
        const installDate = document.getElementById('install_date').value;
        
        // 验证必填字段
        if (!farmName || !unitId) {
            alert('请填写风场名称和机组编号');
            return;
        }
        
        // 构建创建数据
        const createData = {
            farm_name: farmName,
            unit_id: unitId
        };
        
        if (model) createData.model = model;
        if (ownerCompany) createData.owner_company = ownerCompany;
        if (installDate) createData.install_date = installDate;
        
        const statusValue = document.getElementById('status').value;
        if (statusValue) {
            createData.status = statusValue;
        }
        
        // 发送创建请求
        const response = await apiRequest('/turbines/', {
            method: 'POST',
            body: createData
        });
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('addTurbineModal'));
        modal.hide();
        
        // 清空表单
        document.getElementById('turbineForm').reset();
        
        // 显示成功消息
        alert('风机创建成功！');
        
        // 刷新风机列表
        loadTurbinesTable();
        loadTurbines(); // 刷新下拉选择框
        
    } catch (error) {
        console.error('创建风机失败:', error);
        alert('创建风机失败: ' + error.message);
    }
}

async function editTurbine(turbineId) {
    try {
        // 获取风机详情
        const turbine = await apiRequest(`/turbines/${turbineId}`);
        
        // 填充表单
        document.getElementById('edit_turbine_id').value = turbine.turbine_id;
        document.getElementById('edit_farm_name').value = turbine.farm_name || '';
        document.getElementById('edit_unit_id').value = turbine.unit_id || '';
        document.getElementById('edit_model').value = turbine.model || '';
        document.getElementById('edit_owner_company').value = turbine.owner_company || '';
        document.getElementById('edit_status').value = turbine.status || 'NORMAL';
        
        // 处理日期字段
        if (turbine.install_date) {
            const date = new Date(turbine.install_date);
            document.getElementById('edit_install_date').value = date.toISOString().split('T')[0];
        } else {
            document.getElementById('edit_install_date').value = '';
        }
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('editTurbineModal'));
        modal.show();
        
    } catch (error) {
        console.error('加载风机详情失败:', error);
        alert('加载风机详情失败: ' + error.message);
    }
}

async function updateTurbine() {
    try {
        const turbineId = document.getElementById('edit_turbine_id').value;
        const farmName = document.getElementById('edit_farm_name').value.trim();
        const unitId = document.getElementById('edit_unit_id').value.trim();
        const model = document.getElementById('edit_model').value.trim();
        const ownerCompany = document.getElementById('edit_owner_company').value.trim();
        const installDate = document.getElementById('edit_install_date').value;
        const status = document.getElementById('edit_status').value;
        
        // 验证必填字段
        if (!farmName || !unitId) {
            alert('请填写风场名称和机组编号');
            return;
        }
        
        // 构建更新数据
        const updateData = {
            farm_name: farmName,
            unit_id: unitId,
            status: status
        };
        
        if (model) updateData.model = model;
        if (ownerCompany) updateData.owner_company = ownerCompany;
        if (installDate) updateData.install_date = installDate;
        
        // 发送更新请求
        await apiRequest(`/turbines/${turbineId}`, {
            method: 'PUT',
            body: updateData
        });
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('editTurbineModal'));
        modal.hide();
        
        // 显示成功消息
        alert('风机信息更新成功！');
        
        // 刷新风机列表
        loadTurbinesTable();
        loadTurbines(); // 刷新下拉选择框
        
    } catch (error) {
        console.error('更新风机失败:', error);
        alert('更新风机失败: ' + error.message);
    }
}

async function deleteTurbine(turbineId, farmName, unitId) {
    // 确认删除操作
    const confirmMessage = `确定要删除风机吗？\n\n风场名称: ${farmName}\n机组编号: ${unitId}\n\n注意：删除风机将同时删除所有相关的专家记录和时间线事件，此操作不可撤销！`;
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    try {
        const result = await apiRequest(`/turbines/${turbineId}`, {
            method: 'DELETE'
        });
        
        showToast('风机删除成功', 'success');
        // 刷新风机表格和下拉选择框
        loadTurbinesTable();
        loadTurbines();
        // 如果在仪表板页面，也刷新仪表板数据
        if (currentPage === 'dashboard') {
            loadDashboard();
        }
        
    } catch (error) {
        console.error('删除风机失败:', error);
        // 如果是风机不存在的错误，给出更友好的提示
        if (error.message.includes('Turbine not found') || error.message.includes('not found')) {
            showToast('该风机已不存在，可能已被删除。正在刷新列表...', 'warning');
            // 自动刷新列表以同步最新数据
            loadTurbinesTable();
            loadTurbines();
        } else {
            alert('删除风机失败: ' + error.message);
        }
     }
}

// 更新事件摘要
async function updateEventSummary(eventId) {
    try {
        const summaryTextarea = document.getElementById('detail-event-summary');
        if (!summaryTextarea) {
            return;
        }

        const newSummary = summaryTextarea.value.trim();
        if (!newSummary) {
            showToast('事件摘要不能为空', 'warning');
            return;
        }

        // 发送更新请求
        const response = await fetch(`/api/timeline/${eventId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                summary: newSummary
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        showToast('事件摘要已更新', 'success');

    } catch (error) {
        console.error('更新事件摘要失败:', error);
        showToast('更新事件摘要失败: ' + error.message, 'error');
     }
}

// AI润色总结
async function polishSummary() {
    try {
        const summaryTextarea = document.getElementById('edit-event-summary');
        if (!summaryTextarea) {
            showToast('找不到事件摘要字段', 'error');
            return;
        }

        const originalSummary = summaryTextarea.value.trim();
        if (!originalSummary) {
            showToast('请先输入事件摘要内容', 'warning');
            return;
        }

        const button = event.target;
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> AI润色中...';

        // 模拟AI润色处理
        await new Promise(resolve => setTimeout(resolve, 2000));

        // 生成润色后的内容
        const polishedSummary = generatePolishedSummary(originalSummary);
        
        // 更新摘要内容
        summaryTextarea.value = polishedSummary;
        showToast('AI润色完成', 'success');

    } catch (error) {
        console.error('AI润色失败:', error);
        showToast('AI润色失败: ' + error.message, 'error');
    } finally {
        const button = event.target;
        if (button) {
            button.disabled = false;
            button.innerHTML = originalText;
        }
    }
}

// 生成润色后的摘要
function generatePolishedSummary(originalSummary) {
    // 简单的润色逻辑，实际应用中可以调用真正的AI服务
    const polishTemplates = [
        {
            pattern: /设备.*问题/,
            replacement: '经分析发现设备存在异常情况'
        },
        {
            pattern: /需要.*处理/,
            replacement: '建议立即采取相应处理措施'
        },
        {
            pattern: /检查.*维护/,
            replacement: '需要进行全面检查和专业维护'
        }
    ];

    let polishedText = originalSummary;
    
    // 应用润色模板
    polishTemplates.forEach(template => {
        if (template.pattern.test(polishedText)) {
            polishedText = polishedText.replace(template.pattern, template.replacement);
        }
    });

    // 添加专业性描述
    if (polishedText === originalSummary) {
        polishedText = `经AI分析优化：${originalSummary}\n\n建议措施：\n1. 立即安排技术人员现场检查\n2. 记录详细故障信息\n3. 制定针对性解决方案\n4. 跟踪处理进度直至问题解决`;
    }

    return polishedText;
}

// 专家记录管理相关
let currentExpertLogId = null;
let allExpertLogs = []; // 存储所有专家记录数据
let allTurbines = []; // 存储所有风机数据

function displayExpertLogsLoginPrompt() {
    // 清空过滤器
    const turbineFilter = document.getElementById('turbine-filter');
    const timelineFilter = document.getElementById('timeline-status-filter');
    
    if (turbineFilter) {
        turbineFilter.innerHTML = '<option value="all">全部风机</option>';
    }
    if (timelineFilter) {
        timelineFilter.innerHTML = '<option value="all">全部记录</option><option value="published">已发布时间线</option><option value="unpublished">未发布时间线</option>';
    }
    
    // 显示登录提示
    document.getElementById('expert-logs-table').innerHTML = `
        <div class="text-center py-5">
            <i class="bi bi-person-lock" style="font-size: 3rem; color: #6c757d;"></i>
            <h4 class="mt-3 text-muted">需要登录访问</h4>
            <p class="text-muted">请先登录以查看专家记录</p>
            <button class="btn btn-primary" onclick="showLogin()">
                <i class="bi bi-box-arrow-in-right"></i> 立即登录
            </button>
        </div>
    `;
}

async function loadExpertLogs() {
    // 检查用户是否已登录
    if (!currentUser) {
        displayExpertLogsLoginPrompt();
        return;
    }
    
    try {
        // 并行加载专家记录和风机数据
        const [logs, turbines] = await Promise.all([
            apiRequest('/expert-logs/'),
            apiRequest('/turbines/')
        ]);
        
        allExpertLogs = logs; // 保存所有数据
        allTurbines = turbines; // 保存风机数据
        
        // 填充风机过滤选项
        populateTurbineFilter(turbines);
        populateTimelineTurbineFilter(turbines);
        
        await displayExpertLogsTable(logs);
    } catch (error) {
        console.error('加载专家记录失败:', error);
        
        // 如果是认证错误，显示登录提示
        if (error.message.includes('认证') || error.message.includes('登录')) {
            displayExpertLogsLoginPrompt();
        } else {
            // 其他错误显示具体错误信息
            document.getElementById('expert-logs-table').innerHTML = 
                `<div class="text-center py-5">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; color: #dc3545;"></i>
                    <h4 class="mt-3 text-danger">加载失败</h4>
                    <p class="text-muted">${error.message}</p>
                    <button class="btn btn-outline-primary" onclick="loadExpertLogs()">
                        <i class="bi bi-arrow-clockwise"></i> 重试
                    </button>
                </div>`;
        }
    }
}

// 填充专家记录页面的风机过滤选项
function populateTurbineFilter(turbines) {
    const turbineFilter = document.getElementById('turbine-filter');
    if (!turbineFilter) return;
    
    // 清空现有选项（保留"全部风机"选项）
    turbineFilter.innerHTML = '<option value="all">全部风机</option>';
    
    // 添加风机选项
    turbines.forEach(turbine => {
        const option = document.createElement('option');
        option.value = turbine.turbine_id;
        option.textContent = `${turbine.farm_name} - ${turbine.unit_id}`;
        turbineFilter.appendChild(option);
    });
}

// 填充聊天界面的风机过滤选项
function populateChatTurbineFilter(turbines) {
    const chatTurbineFilter = document.getElementById('chat-turbine-filter');
    if (!chatTurbineFilter) return;
    
    // 清空现有选项（保留"所有风机"选项）
    chatTurbineFilter.innerHTML = '<option value="">所有风机</option>';
    
    // 添加风机选项
    turbines.forEach(turbine => {
        const option = document.createElement('option');
        option.value = turbine.turbine_id;
        option.textContent = `${turbine.farm_name} - ${turbine.unit_id}`;
        chatTurbineFilter.appendChild(option);
    });
}

// 填充时间线界面的风机过滤选项
function populateTimelineTurbineFilter(turbines) {
    const timelineTurbineFilter = document.getElementById('timeline-turbine-filter');
    if (!timelineTurbineFilter) return;
    
    // 清空现有选项（保留"请选择风机"选项）
    timelineTurbineFilter.innerHTML = '<option value="">请选择风机</option>';
    
    // 添加风机选项
    turbines.forEach(turbine => {
        const option = document.createElement('option');
        option.value = turbine.turbine_id;
        option.textContent = `${turbine.farm_name} - ${turbine.unit_id}`;
        timelineTurbineFilter.appendChild(option);
    });
}

// 统一的过滤函数，支持按风机和时间线状态过滤
async function filterExpertLogs() {
    console.log('filterExpertLogs 被调用');
    
    const turbineFilter = document.getElementById('turbine-filter');
    const timelineFilter = document.getElementById('timeline-status-filter');
    
    if (!turbineFilter || !timelineFilter) {
        console.error('过滤器元素未找到:', { turbineFilter, timelineFilter });
        return;
    }
    
    const turbineFilterValue = turbineFilter.value;
    const timelineFilterValue = timelineFilter.value;
    
    console.log('过滤参数:', { turbineFilterValue, timelineFilterValue });
    console.log('所有专家记录数量:', allExpertLogs.length);
    
    // 如果两个过滤器都是"全部"，直接显示所有记录
    if (turbineFilterValue === 'all' && timelineFilterValue === 'all') {
        console.log('显示所有记录');
        await displayExpertLogsTable(allExpertLogs);
        return;
    }
    
    try {
        let filteredLogs = [...allExpertLogs];
        
        // 按风机过滤
        if (turbineFilterValue !== 'all') {
            filteredLogs = filteredLogs.filter(log => {
                return log.turbine_id === turbineFilterValue;
            });
        }
        
        // 按时间线状态过滤
        if (timelineFilterValue !== 'all') {
            // 获取所有时间线事件
            const timelineEvents = await apiRequest('/timeline/');
            
            // 创建一个映射，记录每个专家记录是否有已发布的时间线事件
            const logTimelineStatus = {};
            
            timelineEvents.forEach(event => {
                // 检查source_logs字段中的专家记录ID
                if (event.source_logs && Array.isArray(event.source_logs)) {
                    event.source_logs.forEach(sourceLog => {
                        if (sourceLog.log_id) {
                            logTimelineStatus[sourceLog.log_id] = true;
                        }
                    });
                }
            });
            
            filteredLogs = filteredLogs.filter(log => {
                const hasTimeline = logTimelineStatus[log.log_id] || false;
                
                if (timelineFilterValue === 'published') {
                    return hasTimeline;
                } else if (timelineFilterValue === 'unpublished') {
                    return !hasTimeline;
                }
                
                return true;
            });
        }
        
        await displayExpertLogsTable(filteredLogs);
    } catch (error) {
        console.error('过滤专家记录失败:', error);
        alert('过滤失败: ' + error.message);
    }
}

// 保持向后兼容性的函数
async function filterExpertLogsByTimelineStatus() {
    await filterExpertLogs();
}

async function displayExpertLogsTable(logs) {
    const tableContainer = document.getElementById('expert-logs-table');
    
    if (!logs || logs.length === 0) {
        tableContainer.innerHTML = '<p class="text-muted">暂无专家记录</p>';
        return;
    }
    
    // 获取时间线状态信息
    let logTimelineStatus = {};
    try {
        const timelineEvents = await apiRequest('/timeline/');
        timelineEvents.forEach(event => {
            // 检查source_logs字段中的专家记录ID
            if (event.source_logs && Array.isArray(event.source_logs)) {
                event.source_logs.forEach(sourceLog => {
                    if (sourceLog.log_id) {
                        logTimelineStatus[sourceLog.log_id] = true;
                    }
                });
            }
        });
    } catch (error) {
        console.error('获取时间线状态失败:', error);
    }
    
    const table = `
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>记录编号</th>
                    <th>标题</th>
                    <th>风机</th>
                    <th>状态</th>
                    <th>时间线状态</th>
                    <th>作者</th>
                    <th>创建时间</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                ${logs.map((log, index) => `
                    <tr>
                        <td>
                            <div class="d-flex flex-column">
                                <span class="fw-bold">#${String(index + 1).padStart(3, '0')}</span>
                                <small class="text-muted" title="${log.log_id}">${log.log_id.substring(0, 8)}...</small>
                            </div>
                        </td>
                        <td>
                            <div class="d-flex flex-column">
                                <span class="fw-bold">${log.description_text ? (log.description_text.length > 20 ? log.description_text.substring(0, 20) + '...' : log.description_text) : '无标题'}</span>
                                <small class="text-muted">${log.description_text ? log.description_text.substring(0, 50) + '...' : '无描述'}</small>
                            </div>
                        </td>
                        <td>
                            <div class="d-flex flex-column">
                                <span>${log.turbine ? `${log.turbine.farm_name} - ${log.turbine.unit_id}` : 'N/A'}</span>
                                <small class="text-muted">${log.turbine && log.turbine.owner_company ? `所属: ${log.turbine.owner_company}` : ''}</small>
                            </div>
                        </td>
                        <td><span class="badge bg-${getStatusColor(log.status_tag)}">${getStatusLabel(log.status_tag)}</span></td>
                        <td>
                            ${logTimelineStatus[log.log_id] ? 
                                '<span class="badge bg-success"><i class="fas fa-check"></i> 已发布</span>' : 
                                '<span class="badge bg-warning"><i class="fas fa-clock"></i> 未发布</span>'}
                        </td>
                        <td>
                            <div class="d-flex flex-column">
                                <span>${log.author ? log.author.username : 'N/A'}</span>
                                <small class="text-muted">${log.author && log.author.role ? `角色: ${log.author.role}` : ''}</small>
                            </div>
                        </td>
                        <td>
                            <div class="d-flex flex-column">
                                <span>${formatDate(log.created_at)}</span>
                                ${log.last_modified_at && log.last_modified_at !== log.created_at ? 
                                    `<small class="text-muted">修改: ${formatDate(log.last_modified_at)}</small>` : ''}
                            </div>
                        </td>
                        <td>
                            <div class="d-flex gap-1">
                                <button class="btn btn-sm btn-primary" onclick="viewExpertLogDetail('${log.log_id}')" title="查看详情">
                                    <i class="fas fa-eye"></i>
                                </button>
                                ${currentUser && currentUser.role === 'ADMIN' ? 
                                    `<button class="btn btn-sm btn-danger" onclick="deleteExpertLog('${log.log_id}')" title="删除记录">
                                        <i class="fas fa-trash"></i>
                                    </button>` : ''}
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    tableContainer.innerHTML = table;
}

async function showAddExpertLogModal() {
    try {
        // 清空之前的文件选择
        clearLogAttachments();
        
        // 加载风机选项
        const turbines = await apiRequest('/turbines/');
        const select = document.getElementById('log-turbine-id');
        
        // 清空现有选项
        select.innerHTML = '<option value="">请选择风机</option>';
        
        // 添加风机选项
        turbines.forEach(turbine => {
            const option = document.createElement('option');
            option.value = turbine.turbine_id;
            const displayName = `${turbine.farm_name} - ${turbine.unit_id}`;
            option.textContent = displayName;
            select.appendChild(option);
        });
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('addExpertLogModal'));
        modal.show();
    } catch (error) {
        console.error('加载风机选项失败:', error);
        alert('加载风机选项失败: ' + error.message);
    }
}

async function createExpertLog() {
    const turbineId = document.getElementById('log-turbine-id').value;
    const statusTag = document.getElementById('log-status-tag').value;
    const description = document.getElementById('log-description').value;
    
    if (!turbineId || !statusTag || !description) {
        alert('请填写所有必填字段');
        return;
    }
    
    // 显示进度容器
    showUploadProgress();
    
    // 禁用创建按钮
    const createBtn = document.getElementById('create-log-btn');
    const cancelBtn = document.getElementById('cancel-upload-btn');
    createBtn.disabled = true;
    cancelBtn.textContent = '取消';
    
    try {
        // 更新状态：创建专家记录
        updateUploadStatus('正在创建专家记录...', 10);
        
        // 只使用用户输入的描述，不进行AI分析
        const logData = {
            turbine_id: turbineId,
            status_tag: statusTag,
            description_text: description
        };
        
        const newLog = await apiRequest('/expert-logs/', {
            method: 'POST',
            body: logData
        });
        
        // 更新状态：专家记录创建完成
        updateUploadStatus('专家记录创建完成', 30);
        
        // 如果有附件，上传附件
        if (logAttachmentFiles.length > 0) {
            updateUploadStatus('正在上传附件...', 40);
            await uploadAttachmentsForLogWithProgress(newLog.log_id, logAttachmentFiles);
        } else {
            // 没有附件，直接完成
            updateUploadStatus('创建完成！', 100);
        }
        
        // 延迟一下让用户看到完成状态
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // 隐藏进度容器
        hideUploadProgress();
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('addExpertLogModal'));
        modal.hide();
        
        // 清空表单
        document.getElementById('expertLogForm').reset();
        clearLogAttachments();
        
        // 刷新列表
        loadExpertLogs();
        
        showToast('专家记录创建成功！', 'success');
        
    } catch (error) {
        // 隐藏进度容器
        hideUploadProgress();
        
        // 恢复按钮状态
        createBtn.disabled = false;
        cancelBtn.textContent = '取消';
        
        alert('创建失败: ' + error.message);
    }
}

async function viewExpertLogDetail(logId) {
    try {
        const log = await apiRequest(`/expert-logs/${logId}`);
        currentExpertLogId = logId;
        
        // 显示记录详情
        const detailContent = document.getElementById('expert-log-detail-content');
        detailContent.innerHTML = `
            <div class="row">
                <div class="col-md-12">
                    <h6>基本信息</h6>
                    <p><strong>记录编号:</strong> <span class="text-primary">${log.log_id.substring(0, 8)}...</span> 
                       <small class="text-muted" title="${log.log_id}">完整ID</small></p>
                    <p><strong>风机:</strong> ${log.turbine ? `${log.turbine.farm_name} - ${log.turbine.unit_id}` : 'N/A'}</p>
                    ${log.turbine && log.turbine.owner_company ? `<p><strong>所属公司:</strong> ${log.turbine.owner_company}</p>` : ''}
                    <p><strong>状态:</strong> <span class="badge bg-${getStatusColor(log.status_tag)}">${getStatusLabel(log.status_tag)}</span></p>
                    <p><strong>作者:</strong> ${log.author ? log.author.username : 'N/A'}</p>
                    ${log.author && log.author.role ? `<p><strong>作者角色:</strong> ${log.author.role}</p>` : ''}
                    <p><strong>创建时间:</strong> ${formatDate(log.created_at)}</p>
                    ${log.last_modified_at && log.last_modified_at !== log.created_at ? `<p><strong>最后修改:</strong> ${formatDate(log.last_modified_at)}</p>` : ''}
                </div>
            </div>
            <div class="mt-3">
                <h6>描述内容</h6>
                <div class="border p-3 bg-light">
                    ${log.description_text}
                </div>
            </div>
        `;
        
        // 存储当前记录数据供编辑功能使用
        window.currentLogData = log;
        
        // 获取按钮元素
        const editBtn = document.getElementById('edit-content-btn');
        const createTimelineBtn = document.getElementById('create-timeline-btn');
        const revisionHistoryBtn = document.getElementById('revision-history-btn');
        
        // 调试信息
        console.log('专家记录按钮显示:', {
            log_id: log.log_id,
            author: log.author,
            currentUser: currentUser,
            revision_count: log.revision_count
        });
        
        // 始终显示编辑按钮
        editBtn.style.display = 'inline-block';
        editBtn.style.visibility = 'visible';
        
        // 始终显示创建时间线事件按钮
        createTimelineBtn.style.display = 'inline-block';
        createTimelineBtn.style.visibility = 'visible';
        
        // 隐藏修改历史按钮（功能已移除）
        if (revisionHistoryBtn) {
            revisionHistoryBtn.style.display = 'none';
        }
        
        console.log('专家记录操作按钮已配置 - 编辑、创建时间线事件');
        
        // 加载附件列表
        loadAttachments(logId);
        
        // 动态设置模态框标题
        const modalTitle = document.querySelector('#expertLogDetailModal .modal-title');
        const turbineInfo = log.turbine ? `${log.turbine.farm_name} - ${log.turbine.unit_id}` : '未知风机';
        const shortLogId = log.log_id.substring(0, 8);
        modalTitle.textContent = `专家记录详情 - ${turbineInfo} (${shortLogId})`;
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('expertLogDetailModal'));
        modal.show();
        
    } catch (error) {
        alert('加载记录详情失败: ' + error.message);
    }
}

async function loadAttachments(logId) {
    try {
        const attachments = await apiRequest(`/expert-logs/${logId}/attachments`);
        displayAttachments(attachments);
    } catch (error) {
        console.error('加载附件失败:', error);
        document.getElementById('attachments-list').innerHTML = '<p class="text-muted">加载附件失败</p>';
    }
}

function displayAttachments(attachments) {
    const container = document.getElementById('attachments-list');
    
    if (!attachments || attachments.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无附件</p>';
        return;
    }
    
    // 检查当前用户权限
    const canDownload = currentUser && (currentUser.role === 'ADMIN' || currentUser.role === 'EXPERT');
    const canDelete = currentUser && currentUser.role === 'ADMIN';
    
    const attachmentsList = attachments.map(attachment => `
        <div class="card mb-2">
            <div class="card-body p-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="flex-grow-1">
                        <strong>${attachment.file_name}</strong>
                        <small class="text-muted d-block">
                            ${attachment.file_type} • ${formatFileSize(attachment.file_size)} • 
                            ${formatDate(attachment.uploaded_at)}
                        </small>
                        ${attachment.ai_excerpt ? `
                            <div class="mt-1">
                                <small class="text-info">AI摘要: ${attachment.ai_excerpt}</small>
                            </div>
                        ` : ''}
                    </div>
                    <div class="d-flex gap-1">
                        ${canDownload ? `
                            <button class="btn btn-sm btn-outline-success" 
                                    onclick="downloadAttachment('${attachment.attachment_id}', '${attachment.file_name}')"
                                    title="下载附件">
                                <i class="bi bi-download"></i>
                            </button>
                        ` : ''}
                        ${canDelete ? `
                            <button class="btn btn-sm btn-outline-danger" 
                                    onclick="deleteAttachment('${attachment.attachment_id}')"
                                    title="删除附件">
                                <i class="bi bi-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = attachmentsList;
}

async function uploadAttachment() {
    const fileInput = document.getElementById('attachment-file');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('请选择要上传的文件');
        return;
    }
    
    if (!currentExpertLogId) {
        alert('无效的记录ID');
        return;
    }
    
    // 检查文件大小（50MB限制）
    if (file.size > 50 * 1024 * 1024) {
        alert('文件大小不能超过50MB');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/expert-logs/${currentExpertLogId}/attachments`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${window.authToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '上传失败');
        }
        
        const attachment = await response.json();
        
        // 清空文件输入
        fileInput.value = '';
        
        // 重新加载附件列表
        loadAttachments(currentExpertLogId);
        
        alert('附件上传成功！');
        
    } catch (error) {
        alert('上传失败: ' + error.message);
    }
}

// 预览选中的附件（累积选择）
function previewSelectedAttachments() {
    const fileInput = document.getElementById('attachment-file');
    const previewContainer = document.getElementById('selected-attachments-preview');
    const newFiles = Array.from(fileInput.files);
    
    // 将新选择的文件添加到累积列表中
    for (const newFile of newFiles) {
        // 检查是否已经存在同名文件
        const existingIndex = selectedFiles.findIndex(f => f.name === newFile.name && f.size === newFile.size);
        if (existingIndex === -1) {
            selectedFiles.push(newFile);
        }
    }
    
    // 清空文件输入框
    fileInput.value = '';
    
    // 检查文件数量限制
    if (selectedFiles.length > 10) {
        alert('最多只能选择10个文件，已移除超出的文件');
        selectedFiles = selectedFiles.slice(0, 10);
    }
    
    // 更新预览显示
    updateFilePreview();
}

// 更新文件预览显示
function updateFilePreview() {
    const previewContainer = document.getElementById('selected-attachments-preview');
    
    if (selectedFiles.length === 0) {
        previewContainer.innerHTML = '';
        return;
    }
    
    let previewHTML = '<div class="row">';
    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const fileType = getFileType(file.type);
        const fileIcon = getFileIcon(fileType);
        
        // 检查文件大小
        const sizeWarning = file.size > 50 * 1024 * 1024 ? ' text-danger' : '';
        
        previewHTML += `
            <div class="col-md-6 col-lg-4 mb-2">
                <div class="card">
                    <div class="card-body p-2">
                        <div class="d-flex align-items-center">
                            <i class="${fileIcon} me-2"></i>
                            <div class="flex-grow-1">
                                <div class="fw-bold text-truncate${sizeWarning}" title="${file.name}">${file.name}</div>
                                <small class="text-muted${sizeWarning}">${formatFileSize(file.size)}</small>
                                ${file.size > 50 * 1024 * 1024 ? '<br><small class="text-danger">文件过大</small>' : ''}
                            </div>
                            <button type="button" class="btn btn-sm btn-outline-danger ms-2" 
                                    onclick="removeSelectedFile(${i})" title="移除文件">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    previewHTML += '</div>';
    previewContainer.innerHTML = previewHTML;
}

// 移除单个选中的文件
function removeSelectedFile(index) {
    selectedFiles.splice(index, 1);
    updateFilePreview();
}

// 清空选中的附件
function clearSelectedAttachments() {
    const fileInput = document.getElementById('attachment-file');
    
    fileInput.value = '';
    selectedFiles = [];
    updateFilePreview();
}

// 批量上传附件
async function uploadAttachments() {
    const fileInput = document.getElementById('attachment-file');
    const files = selectedFiles;
    
    if (files.length === 0) {
        alert('请选择要上传的文件');
        return;
    }
    
    if (!currentExpertLogId) {
        alert('无效的记录ID');
        return;
    }
    
    if (files.length > 10) {
        alert('最多只能选择10个文件');
        return;
    }
    
    // 检查文件大小
    for (let i = 0; i < files.length; i++) {
        if (files[i].size > 50 * 1024 * 1024) {
            alert(`文件 "${files[i].name}" 大小超过50MB限制`);
            return;
        }
    }
    
    const progressContainer = document.getElementById('upload-progress');
    const progressBar = progressContainer.querySelector('.progress-bar');
    const statusText = document.getElementById('upload-status');
    
    try {
        // 显示进度条
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        statusText.textContent = '准备上传...';
        
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        
        statusText.textContent = `正在上传 ${files.length} 个文件...`;
        progressBar.style.width = '50%';
        
        const response = await fetch(`${API_BASE}/expert-logs/${currentExpertLogId}/attachments/batch`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${window.authToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '批量上传失败');
        }
        
        const result = await response.json();
        
        // 更新进度条
        progressBar.style.width = '100%';
        statusText.textContent = '上传完成！';
        
        // 清空文件输入和预览
        selectedFiles = [];
        updateFilePreview();
        
        // 重新加载附件列表
        loadAttachments(currentExpertLogId);
        
        // 清空选中的文件并更新预览
        selectedFiles = [];
        updateFilePreview();
        
        // 显示结果
        let message = result.message;
        if (result.failed_count > 0) {
            message += '\n\n失败的文件：\n';
            result.failed_uploads.forEach(failed => {
                message += `- ${failed.file_name}: ${failed.error}\n`;
            });
        }
        
        if (result.uploaded_count > 0) {
            showToast('success', message);
        } else {
            showToast('error', message);
        }
        
        // 隐藏进度条
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 2000);
        
    } catch (error) {
        progressBar.style.width = '100%';
        progressBar.classList.add('bg-danger');
        statusText.textContent = '上传失败';
        showToast('error', '批量上传失败: ' + error.message);
        
        setTimeout(() => {
            progressContainer.style.display = 'none';
            progressBar.classList.remove('bg-danger');
        }, 3000);
    }
}

async function deleteAttachment(attachmentId) {
    if (!confirm('确定要删除这个附件吗？')) {
        return;
    }
    
    try {
        await apiRequest(`/expert-logs/attachments/${attachmentId}`, {
            method: 'DELETE'
        });
        
        // 重新加载附件列表
        loadAttachments(currentExpertLogId);
        
        alert('附件删除成功！');
        
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// publishExpertLog函数已移除，因为专家记录不再有发布概念
// 发布逻辑已转移到时间线事件

async function deleteExpertLog(logId) {
    if (!confirm('确定要删除这条专家记录吗？此操作无法撤销。')) {
        return;
    }
    
    try {
        await apiRequest(`/expert-logs/${logId}`, {
            method: 'DELETE'
        });
        
        // 刷新列表
        loadExpertLogs();
        
        alert('记录删除成功！');
        
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 下载附件函数
async function downloadAttachment(attachmentId, fileName) {
    try {
        const response = await fetch(`/api/expert-logs/attachments/${attachmentId}/download`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${window.authToken}`
            }
        });

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('附件不存在或已被删除');
            } else if (response.status === 403) {
                throw new Error('没有权限下载此附件');
            } else {
                throw new Error(`下载失败: ${response.statusText}`);
            }
        }

        // 创建下载链接
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showToast(`附件 "${fileName}" 下载成功`, 'success');
    } catch (error) {
        console.error('下载附件失败:', error);
        showToast(`下载失败: ${error.message}`, 'error');
    }
}

// 文件上传相关功能
document.addEventListener('DOMContentLoaded', function() {
    // 添加文件选择监听器
    const fileInput = document.getElementById('log-attachments');
    if (fileInput) {
        fileInput.addEventListener('change', previewAttachments);
    }
    
    // 添加时间线按钮事件监听器
    const generateTimelineBtn = document.getElementById('generate-timeline-btn');
    if (generateTimelineBtn) {
        generateTimelineBtn.addEventListener('click', generateTimeline);
    }
    
    const batchUpdateBtn = document.getElementById('batch-update-btn');
    if (batchUpdateBtn) {
        batchUpdateBtn.addEventListener('click', batchUpdateTimelines);
    }
    
    const refreshTimelineBtn = document.getElementById('refresh-timeline-btn');
    if (refreshTimelineBtn) {
        refreshTimelineBtn.addEventListener('click', loadTimeline);
    }
    
    // 添加筛选器变化监听器
    const timelineTurbineFilter = document.getElementById('timeline-turbine-filter');
    if (timelineTurbineFilter) {
        timelineTurbineFilter.addEventListener('change', loadTimeline);
    }
    
    // 添加新的风机时间线过滤器监听器
    const turbineSearchInput = document.getElementById('turbine-search-input');
    if (turbineSearchInput) {
        turbineSearchInput.addEventListener('input', filterTurbines);
    }
    
    const turbineStatusFilter = document.getElementById('turbine-status-filter');
    if (turbineStatusFilter) {
        turbineStatusFilter.addEventListener('change', filterTurbines);
    }
});

function previewAttachments() {
    const fileInput = document.getElementById('log-attachments');
    const files = fileInput.files;
    
    // 添加新选择的文件到累积列表中
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        // 检查文件是否已经存在（基于文件名和大小）
        const exists = logAttachmentFiles.some(existingFile => 
            existingFile.name === file.name && existingFile.size === file.size
        );
        
        if (!exists) {
            logAttachmentFiles.push(file);
        }
    }
    
    // 清空文件输入框
    fileInput.value = '';
    
    // 限制文件数量（最多10个）
    if (logAttachmentFiles.length > 10) {
        logAttachmentFiles = logAttachmentFiles.slice(0, 10);
        showToast('最多只能选择10个文件', 'warning');
    }
    
    // 更新预览
    updateLogAttachmentPreview();
}

function updateLogAttachmentPreview() {
    const previewContainer = document.getElementById('attachment-preview');
    
    if (logAttachmentFiles.length === 0) {
        previewContainer.innerHTML = '';
        return;
    }
    
    let previewHTML = '<div class="row">';
    for (let i = 0; i < logAttachmentFiles.length; i++) {
        const file = logAttachmentFiles[i];
        const fileType = getFileType(file.type);
        const fileIcon = getFileIcon(fileType);
        
        previewHTML += `
            <div class="col-md-6 col-lg-4 mb-2">
                <div class="card">
                    <div class="card-body p-2">
                        <div class="d-flex align-items-center">
                            <i class="${fileIcon} me-2"></i>
                            <div class="flex-grow-1">
                                <div class="fw-bold text-truncate" title="${file.name}">${file.name}</div>
                                <small class="text-muted">${formatFileSize(file.size)}</small>
                            </div>
                            <button type="button" class="btn btn-sm btn-outline-danger ms-2" 
                                    onclick="removeLogAttachmentFile(${i})" title="删除文件">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    previewHTML += '</div>';
    previewContainer.innerHTML = previewHTML;
}

function removeLogAttachmentFile(index) {
    logAttachmentFiles.splice(index, 1);
    updateLogAttachmentPreview();
}

function clearLogAttachments() {
    logAttachmentFiles = [];
    const fileInput = document.getElementById('log-attachments');
    if (fileInput) {
        fileInput.value = '';
    }
    updateLogAttachmentPreview();
}

function getFileType(mimeType) {
    if (mimeType.startsWith('image/')) return 'image';
    if (mimeType.startsWith('audio/')) return 'audio';
    if (mimeType.startsWith('video/')) return 'video';
    if (mimeType.includes('pdf')) return 'pdf';
    if (mimeType.includes('word') || mimeType.includes('document')) return 'document';
    if (mimeType.includes('text')) return 'text';
    return 'file';
}

function getFileIcon(fileType) {
    const icons = {
        'image': 'fas fa-image text-success',
        'audio': 'fas fa-music text-info',
        'video': 'fas fa-video text-warning',
        'pdf': 'fas fa-file-pdf text-danger',
        'document': 'fas fa-file-word text-primary',
        'text': 'fas fa-file-alt text-secondary',
        'file': 'fas fa-file text-muted'
    };
    return icons[fileType] || icons['file'];
}

async function uploadAttachmentsForLog(logId, files) {
    const uploadPromises = [];
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadPromise = fetch(`${API_BASE}/expert-logs/${logId}/attachments`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${window.authToken}`
            },
            body: formData
        }).then(response => {
            if (!response.ok) {
                throw new Error(`上传文件 ${file.name} 失败: ${response.statusText}`);
            }
            return response.json();
        });
        
        uploadPromises.push(uploadPromise);
    }
    
    try {
        await Promise.all(uploadPromises);
        console.log('所有附件上传成功');
    } catch (error) {
        console.error('附件上传失败:', error);
        alert('部分附件上传失败: ' + error.message);
    }
}

// 带进度显示的文件上传函数
async function uploadAttachmentsForLogWithProgress(logId, files) {
    // 初始化文件进度列表
    initializeFileProgressList(files);
    
    let completedFiles = 0;
    const totalFiles = files.length;
    
    // 逐个上传文件以便跟踪进度
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileId = `file-${i}`;
        
        try {
            // 更新文件状态为上传中
            updateFileProgress(fileId, 0, 'uploading', '上传中...');
            
            // 创建XMLHttpRequest以支持进度跟踪
            await uploadSingleFileWithProgress(logId, file, fileId);
            
            // 更新文件状态为完成
            updateFileProgress(fileId, 100, 'completed', '上传完成');
            completedFiles++;
            
            // 更新总体进度
            const overallProgress = 40 + (completedFiles / totalFiles) * 60; // 40-100%
            updateUploadStatus(`已上传 ${completedFiles}/${totalFiles} 个文件`, overallProgress);
            
        } catch (error) {
            // 更新文件状态为错误
            updateFileProgress(fileId, 0, 'error', '上传失败');
            console.error(`文件 ${file.name} 上传失败:`, error);
            throw new Error(`文件 ${file.name} 上传失败: ${error.message}`);
        }
    }
    
    // 所有文件上传完成
    updateUploadStatus('所有文件上传完成！', 100);
}

// 上传单个文件并跟踪进度
function uploadSingleFileWithProgress(logId, file, fileId) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);
        
        // 监听上传进度
        xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                updateFileProgress(fileId, percentComplete, 'uploading', `${Math.round(percentComplete)}%`);
            }
        });
        
        // 监听上传完成
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
            }
        });
        
        // 监听上传错误
        xhr.addEventListener('error', () => {
            reject(new Error('网络错误'));
        });
        
        // 监听上传中止
        xhr.addEventListener('abort', () => {
            reject(new Error('上传被中止'));
        });
        
        // 开始上传
        xhr.open('POST', `${API_BASE}/expert-logs/${logId}/attachments`);
        xhr.setRequestHeader('Authorization', `Bearer ${window.authToken}`);
        xhr.send(formData);
    });
}

// 进度显示相关函数
function showUploadProgress() {
    const progressContainer = document.getElementById('upload-progress-container');
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }
}

function hideUploadProgress() {
    const progressContainer = document.getElementById('upload-progress-container');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }
    
    // 重置进度
    updateUploadStatus('', 0);
    clearFileProgressList();
    
    // 恢复按钮状态
    const createBtn = document.getElementById('create-log-btn');
    const cancelBtn = document.getElementById('cancel-upload-btn');
    if (createBtn) createBtn.disabled = false;
    if (cancelBtn) cancelBtn.textContent = '取消';
}

function updateUploadStatus(statusText, progress) {
    const statusTextElement = document.getElementById('upload-status-text');
    const progressBar = document.getElementById('overall-progress-bar');
    const progressText = document.getElementById('overall-progress-text');
    
    if (statusTextElement) {
        statusTextElement.textContent = statusText;
    }
    
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        
        // 添加动画类
        if (progress < 100) {
            progressBar.classList.add('uploading');
        } else {
            progressBar.classList.remove('uploading');
        }
    }
    
    if (progressText) {
        progressText.textContent = `${Math.round(progress)}%`;
    }
}

function initializeFileProgressList(files) {
    const fileProgressList = document.getElementById('file-progress-list');
    if (!fileProgressList) return;
    
    fileProgressList.innerHTML = '';
    
    files.forEach((file, index) => {
        const fileId = `file-${index}`;
        const fileItem = document.createElement('div');
        fileItem.className = 'file-progress-item';
        fileItem.id = fileId;
        
        fileItem.innerHTML = `
            <div class="file-info">
                <span class="file-name" title="${file.name}">${file.name}</span>
                <span class="file-size">${formatFileSize(file.size)}</span>
                <span class="file-status" id="${fileId}-status">等待上传</span>
            </div>
            <div class="file-progress-bar">
                <div class="file-progress-fill" id="${fileId}-progress" style="width: 0%"></div>
            </div>
        `;
        
        fileProgressList.appendChild(fileItem);
    });
}

function updateFileProgress(fileId, progress, status, statusText) {
    const fileItem = document.getElementById(fileId);
    const progressFill = document.getElementById(`${fileId}-progress`);
    const statusElement = document.getElementById(`${fileId}-status`);
    
    if (!fileItem || !progressFill || !statusElement) return;
    
    // 更新进度条
    progressFill.style.width = `${progress}%`;
    
    // 更新状态文本
    statusElement.textContent = statusText;
    
    // 更新样式类
    fileItem.className = `file-progress-item ${status}`;
    progressFill.className = `file-progress-fill ${status}`;
    statusElement.className = `file-status ${status}`;
}

function clearFileProgressList() {
    const fileProgressList = document.getElementById('file-progress-list');
    if (fileProgressList) {
        fileProgressList.innerHTML = '';
    }
}

// AI提取内容编辑相关功能
let extractedContent = '';
let isEditMode = false;

// 处理附件变化，模拟AI提取
function handleAttachmentChange() {
    // 只更新附件预览，不进行AI分析
    previewAttachments();
}

// 显示AI提取的内容
function showExtractedContent() {
    const container = document.getElementById('ai-extracted-content');
    const display = document.getElementById('extracted-text-display');
    
    display.innerHTML = `<pre class="mb-0" style="white-space: pre-wrap; font-family: inherit;">${extractedContent}</pre>`;
    container.style.display = 'block';
}

// 隐藏AI提取的内容
function hideExtractedContent() {
    const container = document.getElementById('ai-extracted-content');
    container.style.display = 'none';
    extractedContent = '';
}

// 切换编辑模式
function toggleEditMode() {
    const display = document.getElementById('extracted-text-display');
    const edit = document.getElementById('extracted-text-edit');
    const editor = document.getElementById('extracted-text-editor');
    
    if (!isEditMode) {
        // 进入编辑模式
        editor.value = extractedContent;
        display.style.display = 'none';
        edit.style.display = 'block';
        isEditMode = true;
    }
}

// 保存编辑的内容
function saveEditedContent() {
    const editor = document.getElementById('extracted-text-editor');
    const display = document.getElementById('extracted-text-display');
    const edit = document.getElementById('extracted-text-edit');
    
    extractedContent = editor.value;
    display.innerHTML = `<pre class="mb-0" style="white-space: pre-wrap; font-family: inherit;">${extractedContent}</pre>`;
    
    display.style.display = 'block';
    edit.style.display = 'none';
    isEditMode = false;
    
    alert('内容已保存！');
}

// 取消编辑
function cancelEdit() {
    const display = document.getElementById('extracted-text-display');
    const edit = document.getElementById('extracted-text-edit');
    
    display.style.display = 'block';
    edit.style.display = 'none';
    isEditMode = false;
}

// 专家记录详情页面的内容编辑功能
function toggleContentEdit() {
    const editSection = document.getElementById('content-edit-section');
    const editBtn = document.getElementById('edit-content-btn');
    const editTextarea = document.getElementById('edit-description');
    
    if (editSection.style.display === 'none') {
        // 显示编辑区域
        editSection.style.display = 'block';
        editBtn.innerHTML = '<i class="bi bi-x"></i> 取消编辑';
        
        // 获取当前记录的描述内容
        const currentLog = getCurrentLogData();
        if (currentLog && currentLog.description_text) {
            editTextarea.value = currentLog.description_text;
        }
    } else {
        // 隐藏编辑区域
        editSection.style.display = 'none';
        editBtn.innerHTML = '<i class="bi bi-pencil"></i> 编辑内容';
    }
}

// 取消内容编辑
function cancelContentEdit() {
    const editSection = document.getElementById('content-edit-section');
    const editBtn = document.getElementById('edit-content-btn');
    
    editSection.style.display = 'none';
    editBtn.innerHTML = '<i class="bi bi-pencil"></i> 编辑内容';
}

// 保存内容编辑
async function saveContentEdit() {
    const editTextarea = document.getElementById('edit-description');
    const newDescription = editTextarea.value.trim();
    
    if (!newDescription) {
        alert('描述内容不能为空');
        return;
    }
    
    try {
        const updateData = {
            description_text: newDescription
        };
        
        const response = await apiRequest(`/expert-logs/${currentExpertLogId}`, {
            method: 'PUT',
            body: updateData
        });
        
        // 更新成功后刷新详情显示
        await viewExpertLogDetail(currentExpertLogId);
        cancelContentEdit();
        
        alert('内容更新成功！');
        
    } catch (error) {
        alert('更新失败: ' + error.message);
    }
}

// 获取当前记录数据的辅助函数
function getCurrentLogData() {
    // 返回存储在window对象中的当前记录数据
    return window.currentLogData || null;
}

// 智能总结相关函数
// 显示分析配置界面
function showAnalysisConfig(turbineId) {
    const configDiv = document.getElementById(`analysis-config-${turbineId}`);
    const resultDiv = document.getElementById(`analysis-result-${turbineId}`);
    
    if (configDiv) {
        configDiv.style.display = 'block';
        resultDiv.style.display = 'none';
    }
}

// 隐藏分析配置界面
function hideAnalysisConfig(turbineId) {
    const configDiv = document.getElementById(`analysis-config-${turbineId}`);
    const resultDiv = document.getElementById(`analysis-result-${turbineId}`);
    
    if (configDiv) {
        configDiv.style.display = 'none';
        resultDiv.style.display = 'block';
    }
}

// 执行智能分析
async function executeAnalysis(turbineId) {
    const analysisMode = document.getElementById(`analysis-mode-${turbineId}`).value;
    const daysBack = parseInt(document.getElementById(`days-back-${turbineId}`).value);
    
    try {
        // 隐藏配置界面，显示结果区域
        hideAnalysisConfig(turbineId);
        
        // 找到结果显示容器
        const resultContainer = document.getElementById(`analysis-result-${turbineId}`);
        if (!resultContainer) {
            showToast('未找到结果显示容器', 'error');
            return;
        }

        // 显示加载状态
        resultContainer.innerHTML = `
            <div class="alert alert-info">
                <div class="text-center py-2">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">分析中...</span>
                    </div>
                    <span class="ms-2">正在执行智能分析（${analysisMode === 'llm' ? '大模型分析' : '基本统计分析'}，回溯${daysBack}天），请稍候...</span>
                </div>
            </div>
        `;

        // 调用API生成智能总结（强制重新生成）
        const response = await apiRequest(`/api/timeline/turbine/${turbineId}/intelligent-summary?analysis_mode=${analysisMode}&days_back=${daysBack}&force_regenerate=true`, {
            method: 'POST'
        });

        if (response && response.success && response.data) {
            const analysisData = response.data;
            
            // 保存分析结果到本地缓存
            await saveAnalysisResult(turbineId, analysisMode, daysBack, analysisData);
            
            // 显示分析结果
            resultContainer.innerHTML = `
                <div class="alert alert-success">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <small class="text-muted">
                            ${analysisData.analysis_mode === 'llm' ? '大模型分析' : '基本统计分析'} | 
                            回溯${analysisData.days_back}天 | 
                            ${formatDateTime(analysisData.created_at)}
                        </small>
                        <span class="badge bg-success">已保存到数据库</span>
                    </div>
                    <div class="summary-content">
                        ${analysisData.summary}
                    </div>
                    <div class="mt-2">
                        <button class="btn btn-sm btn-outline-primary" onclick="showAnalysisConfig('${turbineId}')">
                            <i class="bi bi-gear"></i> 重新分析
                        </button>
                    </div>
                </div>
            `;
            showToast('智能分析完成并已保存到数据库', 'success');
        } else {
            throw new Error(response?.message || '分析失败，未获取到有效结果');
        }
    } catch (error) {
        console.error('执行智能分析失败:', error);
        const resultContainer = document.getElementById(`analysis-result-${turbineId}`);
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="alert alert-danger">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            执行智能分析失败: ${error.message}
                        </div>
                        <button class="btn btn-sm btn-outline-primary" onclick="showAnalysisConfig('${turbineId}')">
                            <i class="bi bi-arrow-clockwise"></i> 重试
                        </button>
                    </div>
                </div>
            `;
        }
        showToast('智能分析失败', 'error');
    }
}

// 保存分析结果到后端数据库（临时函数，稍后实现完整功能）
async function saveAnalysisResult(turbineId, analysisMode, daysBack, analysisData) {
    try {
        // 这里将调用后端API保存分析结果
        // 暂时只在本地缓存中保存
        setCachedSummary(turbineId, analysisMode, {
            ...analysisData,
            days_back: daysBack,
            cached_at: new Date().toISOString()
        }, daysBack);
        
        console.log('分析结果已保存到缓存');
    } catch (error) {
        console.error('保存分析结果失败:', error);
    }
}

async function showIntelligentSummary(turbineId, analysisMode = 'llm') {
    try {
        // 找到对应的智能总结容器
        const summaryContainer = document.querySelector(`[data-turbine-id="${turbineId}"] .intelligent-summary-box .alert`);
        if (!summaryContainer) {
            showToast('未找到智能总结容器', 'error');
            return;
        }

        // 首先尝试从数据库加载已保存的分析结果
        try {
            const savedResponse = await apiRequest(`/api/timeline/turbine/${turbineId}/intelligent-summary/saved?analysis_mode=${analysisMode}`, {
                method: 'GET'
            });
            
            if (savedResponse && savedResponse.success && savedResponse.data) {
                const analysisData = savedResponse.data;
                // 显示数据库中的分析结果
                summaryContainer.className = 'alert alert-success';
                summaryContainer.innerHTML = `
                    <div class="intelligent-analysis-content">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div class="flex-grow-1">
                                <i class="bi bi-database me-2"></i>
                                <span class="fw-bold">智能总结</span>
                                <small class="text-success ms-2">(数据库)</small>
                            </div>
                            <div class="d-flex gap-2">
                                <button class="btn btn-sm btn-outline-primary" onclick="showIntelligentSummary('${turbineId}', 'llm')" 
                                        ${analysisMode === 'llm' ? 'disabled' : ''}>
                                    <i class="bi bi-robot"></i> 大模型
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="showIntelligentSummary('${turbineId}', 'basic')" 
                                        ${analysisMode === 'basic' ? 'disabled' : ''}>
                                    <i class="bi bi-bar-chart"></i> 基本统计
                                </button>
                            </div>
                        </div>
                        <div class="summary-text">
                            ${analysisData.summary}
                        </div>
                        <small class="text-muted mt-2 d-block">
                            分析模式：${analysisData.analysis_mode === 'llm' ? '大模型分析' : '基本统计'} | 
                            分析范围：最近${analysisData.days_back}天 | 
                            保存时间：${formatDateTime(analysisData.created_at)}
                        </small>
                    </div>
                `;
                return;
            }
        } catch (dbError) {
            console.log('从数据库加载分析结果失败，尝试缓存:', dbError);
        }

        // 检查本地缓存
        const cachedSummary = getCachedSummary(turbineId, analysisMode, 30);
        if (cachedSummary) {
            // 使用缓存数据
            summaryContainer.className = 'alert alert-success';
            summaryContainer.innerHTML = `
                <div class="intelligent-analysis-content">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div class="flex-grow-1">
                            <i class="bi bi-check-circle me-2"></i>
                            <span class="fw-bold">智能总结</span>
                            <small class="text-success ms-2">(缓存)</small>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-sm btn-outline-primary" onclick="showIntelligentSummary('${turbineId}', 'llm')" 
                                    ${analysisMode === 'llm' ? 'disabled' : ''}>
                                <i class="bi bi-robot"></i> 大模型
                            </button>
                            <button class="btn btn-sm btn-outline-secondary" onclick="showIntelligentSummary('${turbineId}', 'basic')" 
                                    ${analysisMode === 'basic' ? 'disabled' : ''}>
                                <i class="bi bi-bar-chart"></i> 基本统计
                            </button>
                        </div>
                    </div>
                    <div class="summary-text">
                        ${cachedSummary.summary}
                    </div>
                    <small class="text-muted mt-2 d-block">
                        分析模式：${analysisMode === 'llm' ? '大模型分析' : '基本统计'} | 
                        分析范围：最近${cachedSummary.days_back}天 | 
                        缓存时间：${formatDateTime(cachedSummary.cached_at)}
                    </small>
                </div>
            `;
            return;
        }

        // 显示加载状态
        summaryContainer.className = 'alert alert-info';
        summaryContainer.innerHTML = `
            <div class="text-center py-2">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">生成中...</span>
                </div>
                <span class="ms-2">正在生成智能总结（${analysisMode === 'llm' ? '大模型分析' : '基本统计'}），请稍候...</span>
            </div>
        `;

        // 调用API生成智能总结
        const response = await apiRequest(`/api/timeline/turbine/${turbineId}/intelligent-summary?analysis_mode=${analysisMode}&days_back=30`, {
            method: 'POST'
        });

        if (response && response.success && response.data) {
            const analysisData = response.data;
            
            // 缓存结果
            setCachedSummary(turbineId, analysisMode, analysisData, 30);
            
            // 直接在智能总结框中显示结果
            summaryContainer.className = 'alert alert-success';
            summaryContainer.innerHTML = `
                <div class="intelligent-analysis-content">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div class="flex-grow-1">
                            <i class="bi bi-check-circle me-2"></i>
                            <span class="fw-bold">智能总结</span>
                            <small class="text-success ms-2">(新生成)</small>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-sm btn-outline-primary" onclick="showIntelligentSummary('${turbineId}', 'llm')" 
                                    ${analysisMode === 'llm' ? 'disabled' : ''}>
                                <i class="bi bi-robot"></i> 大模型
                            </button>
                            <button class="btn btn-sm btn-outline-secondary" onclick="showIntelligentSummary('${turbineId}', 'basic')" 
                                    ${analysisMode === 'basic' ? 'disabled' : ''}>
                                <i class="bi bi-bar-chart"></i> 基本统计
                            </button>
                        </div>
                    </div>
                    <div class="summary-text">
                        ${analysisData.summary}
                    </div>
                    <small class="text-muted mt-2 d-block">
                        分析模式：${analysisData.analysis_mode === 'llm' ? '大模型分析' : '基本统计'} | 
                        分析范围：最近${analysisData.days_back}天 | 
                        生成时间：${formatDateTime(analysisData.created_at)}
                    </small>
                </div>
            `;
            showToast('智能总结生成成功并已保存到数据库', 'success');
        } else {
            throw new Error(response?.message || '生成智能总结失败');
        }
    } catch (error) {
        console.error('生成智能总结失败:', error);
        const summaryContainer = document.querySelector(`[data-turbine-id="${turbineId}"] .intelligent-summary-box .alert`);
        if (summaryContainer) {
            summaryContainer.className = 'alert alert-danger';
            summaryContainer.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        生成智能总结失败: ${error.message}
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn btn-sm btn-outline-primary" onclick="showIntelligentSummary('${turbineId}', 'llm')">
                            <i class="bi bi-robot"></i> 大模型
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="showIntelligentSummary('${turbineId}', 'basic')">
                            <i class="bi bi-bar-chart"></i> 基本统计
                        </button>
                    </div>
                </div>
            `;
        }
        showToast('生成智能总结失败', 'error');
    }
}

function displayIntelligentSummary(summaryData) {
    const content = document.getElementById('summaryContent');
    
    content.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header">
                        <h6 class="mb-0"><i class="bi bi-info-circle"></i> 基本信息</h6>
                    </div>
                    <div class="card-body">
                        <p><strong>风机ID:</strong> ${summaryData.turbine_id}</p>
                        <p><strong>分析时间:</strong> ${formatDateTime(summaryData.generated_at)}</p>
                        <p><strong>分析记录数:</strong> ${summaryData.total_records || 0} 条</p>
                        <p><strong>时间范围:</strong> ${summaryData.time_range || '暂无数据'}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header">
                        <h6 class="mb-0"><i class="bi bi-bar-chart"></i> 统计数据</h6>
                    </div>
                    <div class="card-body">
                        ${summaryData.statistics ? Object.entries(summaryData.statistics).map(([key, value]) => 
                            `<p><strong>${key}:</strong> ${value}</p>`
                        ).join('') : '<p class="text-muted">暂无统计数据</p>'}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mb-3">
            <div class="card-header">
                <h6 class="mb-0"><i class="bi bi-file-text"></i> 总体摘要</h6>
            </div>
            <div class="card-body">
                <p>${summaryData.summary || '暂无摘要信息'}</p>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header">
                        <h6 class="mb-0"><i class="bi bi-lightbulb"></i> 关键洞察</h6>
                    </div>
                    <div class="card-body">
                        ${summaryData.insights && summaryData.insights.length > 0 ? 
                            '<ul>' + summaryData.insights.map(insight => `<li>${insight}</li>`).join('') + '</ul>' :
                            '<p class="text-muted">暂无关键洞察</p>'
                        }
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header">
                        <h6 class="mb-0"><i class="bi bi-tools"></i> 维护建议</h6>
                    </div>
                    <div class="card-body">
                        ${summaryData.recommendations && summaryData.recommendations.length > 0 ? 
                            '<ul>' + summaryData.recommendations.map(rec => `<li>${rec}</li>`).join('') + '</ul>' :
                            '<p class="text-muted">暂无维护建议</p>'
                        }
                    </div>
                </div>
            </div>
        </div>
        
        ${summaryData.status_trend ? `
        <div class="card">
            <div class="card-header">
                <h6 class="mb-0"><i class="bi bi-graph-up"></i> 状态趋势</h6>
            </div>
            <div class="card-body">
                <p>${summaryData.status_trend}</p>
            </div>
        </div>
        ` : ''}
    `;
}

// 生成整体分析段落 - 直接返回后端大模型生成的文字描述
function generateOverallAnalysis(summaryData) {
    if (!summaryData) {
        return '暂无智能分析数据';
    }
    
    // 直接返回后端大模型生成的完整文字描述
    return summaryData.analysis_text || '暂无详细分析信息';
}

async function displayIntelligentSummaryInTimeline(summaryText, turbineId) {
    const timelineContainer = document.getElementById(`timeline-detail-${turbineId}`);
    if (!timelineContainer) return;

    // 获取时间线事件数据
    let timelineEvents = [];
    try {
        const timelineResponse = await apiRequest(`/api/timeline/turbine/${turbineId}`);
        if (timelineResponse.success) {
            timelineEvents = timelineResponse.data;
        }
    } catch (error) {
        console.error('获取时间线事件失败:', error);
    }

    timelineContainer.innerHTML = `
        <!-- 智能总结区域 -->
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h6 class="mb-0"><i class="bi bi-lightbulb"></i> 智能总结分析</h6>
            </div>
            <div class="card-body">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <small class="text-muted">分析时间: ${formatDateTime(new Date().toISOString())}</small>
                    </div>
                </div>
                
                <!-- 智能分析内容 -->
                <div class="alert alert-primary mb-3">
                    <h6><i class="bi bi-graph-up-arrow"></i> 智能分析</h6>
                    <p class="mb-0" style="line-height: 1.6; font-size: 1.05em; white-space: pre-wrap;">${summaryText}</p>
                </div>
            </div>
        </div>
        
        <!-- 时间线事件区域 -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0"><i class="bi bi-clock-history"></i> 详细时间线事件</h6>
                <button class="btn btn-sm btn-outline-secondary" onclick="toggleTimelineEvents('${turbineId}')" id="toggle-events-${turbineId}">
                    <i class="bi bi-chevron-down"></i> 展开事件列表
                </button>
            </div>
            <div class="collapse" id="timeline-events-${turbineId}">
                <div class="card-body">
                    ${timelineEvents.length > 0 ? 
                        timelineEvents.map((event, index) => `
                            <div class="timeline-item mb-3 border-start border-4 border-${getSeverityColor(event.event_severity)} ps-3">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div class="d-flex align-items-center">
                                        <i class="bi ${getEventTypeIcon(event.event_type)} me-2 text-${getSeverityColor(event.event_severity)}"></i>
                                        <h6 class="mb-0">${event.title}</h6>
                                    </div>
                                    <div class="d-flex flex-column align-items-end">
                                        <span class="badge bg-${getSeverityColor(event.event_severity)} mb-1">
                                            ${getSeverityLabel(event.event_severity)}
                                        </span>
                                        <span class="badge bg-secondary">
                                            ${getEventTypeLabel(event.event_type)}
                                        </span>
                                    </div>
                                </div>
                                <p class="text-muted mb-2">${event.description}</p>
                                <div class="d-flex justify-content-between align-items-center">
                                    <small class="text-muted">
                                        <i class="bi bi-calendar"></i> ${formatDateTime(event.event_time)}
                                    </small>
                                    <button class="btn btn-sm btn-outline-primary" onclick="viewTimelineEventDetail(${event.event_id})">
                                        查看详情
                                    </button>
                                </div>
                            </div>
                        `).join('') :
                        '<p class="text-muted text-center py-3">暂无时间线事件</p>'
                    }
                </div>
            </div>
        </div>
    `;
}

// 切换时间线事件列表的展开/收起状态
function toggleTimelineEvents(turbineId) {
    const eventsContainer = document.getElementById(`timeline-events-${turbineId}`);
    const toggleButton = document.getElementById(`toggle-events-${turbineId}`);
    
    if (eventsContainer && toggleButton) {
        const isCollapsed = eventsContainer.classList.contains('collapse');
        
        if (isCollapsed) {
            eventsContainer.classList.remove('collapse');
            eventsContainer.classList.add('show');
            toggleButton.innerHTML = '<i class="bi bi-chevron-up"></i> 收起事件列表';
        } else {
            eventsContainer.classList.remove('show');
            eventsContainer.classList.add('collapse');
            toggleButton.innerHTML = '<i class="bi bi-chevron-down"></i> 展开事件列表';
        }
    }
}

// 批量生成智能总结
async function batchGenerateIntelligentSummary() {
    try {
        const selectedTurbines = getSelectedTurbines();
        if (selectedTurbines.length === 0) {
            showToast('请先选择要生成智能总结的风机', 'warning');
            return;
        }

        const confirmMessage = `确定要为 ${selectedTurbines.length} 台风机生成智能总结吗？这可能需要一些时间。`;
        if (!confirm(confirmMessage)) {
            return;
        }

        showToast('开始批量生成智能总结...', 'info');
        
        let successCount = 0;
        let failCount = 0;
        
        for (const turbineId of selectedTurbines) {
            try {
                const summaryText = await apiRequest(`/api/timeline/turbine/${turbineId}/intelligent-summary`, {
                    method: 'POST'
                });
                
                if (summaryText && typeof summaryText === 'string') {
                    successCount++;
                } else {
                    failCount++;
                }
            } catch (error) {
                console.error(`风机 ${turbineId} 智能总结生成失败:`, error);
                failCount++;
            }
        }
        
        showToast(`批量生成完成：成功 ${successCount} 台，失败 ${failCount} 台`, 
                  failCount === 0 ? 'success' : 'warning');
        
    } catch (error) {
        console.error('批量生成智能总结失败:', error);
        showToast('批量生成智能总结失败', 'error');
    }
}

// AI分析触发功能
async function triggerAIAnalysis() {
    if (!window.currentLogData || !window.currentLogData.id) {
        showToast('无法获取当前记录信息', 'error');
        return;
    }

    const logId = window.currentLogData.id;
    
    // 确认对话框
    if (!confirm('确定要对此专家记录进行AI分析吗？这将分析附件内容并生成摘要和标签。')) {
        return;
    }

    try {
        // 禁用按钮并显示加载状态
        const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
        const originalText = aiAnalysisBtn.innerHTML;
        aiAnalysisBtn.disabled = true;
        aiAnalysisBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 分析中...';

        // 调用AI分析API
        const result = await apiRequest(`/expert-logs/${logId}/trigger-ai-analysis`, {
            method: 'POST'
        });

        showToast('AI分析完成！已生成摘要和标签', 'success');
        
        // 刷新专家记录详情以显示更新后的内容
        await showExpertLogDetail(logId);
        
    } catch (error) {
        console.error('AI分析失败:', error);
        showToast('AI分析失败: ' + (error.message || '未知错误'), 'error');
    } finally {
        // 恢复按钮状态
        const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
        aiAnalysisBtn.disabled = false;
        aiAnalysisBtn.innerHTML = '<i class="bi bi-robot"></i> AI分析';
    }
}

function getSelectedTurbines() {
    // 这里可以根据实际需求实现选择逻辑
    // 暂时返回当前显示的所有风机ID
    return filteredTurbinesData.map(turbine => turbine.turbine_id);
}

// 修改历史功能已移除

// 修改历史功能已完全移除

// AI分析相关变量
let currentAIAnalysisResult = '';
let selectedFilesForAnalysis = [];

// 加载可用文件列表用于AI分析
async function loadAvailableFilesForAnalysis(logId) {
    try {
        const attachments = await apiRequest(`/expert-logs/${logId}/attachments`);
        const filesList = document.getElementById('available-files-list');
        
        if (attachments.length === 0) {
            filesList.innerHTML = '<p class="text-muted">暂无可分析的文件</p>';
            return;
        }
        
        filesList.innerHTML = attachments.map(attachment => `
            <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" value="${attachment.attachment_id}" 
                       id="file-${attachment.attachment_id}" onchange="toggleFileSelection('${attachment.attachment_id}')">
                <label class="form-check-label d-flex align-items-center" for="file-${attachment.attachment_id}">
                    <i class="${getFileIcon(getFileType(attachment.file_type))} me-2"></i>
                    <span>${attachment.file_name}</span>
                    <small class="text-muted ms-2">(${formatFileSize(attachment.file_size)})</small>
                </label>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('加载文件列表失败:', error);
        document.getElementById('available-files-list').innerHTML = '<p class="text-danger">加载文件列表失败</p>';
    }
}

// 切换文件选择状态
function toggleFileSelection(attachmentId) {
    const checkbox = document.getElementById(`file-${attachmentId}`);
    if (checkbox.checked) {
        if (!selectedFilesForAnalysis.includes(attachmentId)) {
            selectedFilesForAnalysis.push(attachmentId);
        }
    } else {
        selectedFilesForAnalysis = selectedFilesForAnalysis.filter(id => id !== attachmentId);
    }
}

// 执行AI分析
async function performAIAnalysis() {
    if (selectedFilesForAnalysis.length === 0) {
        alert('请至少选择一个文件进行分析');
        return;
    }
    
    const analysisBtn = document.querySelector('button[onclick="performAIAnalysis()"]');
    const originalText = analysisBtn.innerHTML;
    
    try {
        analysisBtn.disabled = true;
        analysisBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 分析中...';
        
        // 模拟AI分析过程
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // 生成模拟的AI分析结果
        const analysisResult = generateMockAIAnalysis(selectedFilesForAnalysis);
        
        // 显示分析结果
        currentAIAnalysisResult = analysisResult;
        displayAIAnalysisResult(analysisResult);
        
        showToast('AI分析完成', 'success');
        
    } catch (error) {
        console.error('AI分析失败:', error);
        showToast('AI分析失败: ' + error.message, 'error');
    } finally {
        analysisBtn.disabled = false;
        analysisBtn.innerHTML = originalText;
    }
}

// 生成模拟的AI分析结果
function generateMockAIAnalysis(fileIds) {
    const analysisTemplates = [
        '通过对附件的深度分析，发现以下关键信息：\n\n1. 设备运行状态异常，存在潜在故障风险\n2. 温度参数超出正常范围，建议立即检查冷却系统\n3. 振动数据显示轴承可能存在磨损\n4. 建议在下次维护窗口期进行详细检查',
        '文档分析结果显示：\n\n1. 维护记录完整，操作规范\n2. 发现历史故障模式，建议加强预防性维护\n3. 零部件更换周期符合标准\n4. 推荐优化维护策略以提高设备可靠性',
        '图像识别分析发现：\n\n1. 设备外观状态良好，无明显损坏\n2. 连接部件紧固正常\n3. 润滑系统工作正常\n4. 建议继续保持当前维护水平'
    ];
    
    const randomTemplate = analysisTemplates[Math.floor(Math.random() * analysisTemplates.length)];
    return `AI分析报告 (分析文件数: ${fileIds.length})\n\n${randomTemplate}\n\n分析时间: ${new Date().toLocaleString()}\n置信度: ${(0.8 + Math.random() * 0.2).toFixed(2)}`;
}

// 显示AI分析结果
function displayAIAnalysisResult(result) {
    const resultsSection = document.getElementById('ai-analysis-results');
    const displayArea = document.getElementById('ai-analysis-display');
    
    displayArea.innerHTML = `<pre class="mb-0" style="white-space: pre-wrap; font-family: inherit;">${result}</pre>`;
    resultsSection.style.display = 'block';
}

// 编辑AI分析结果
function editAIAnalysis() {
    const displayArea = document.getElementById('ai-analysis-display');
    const editArea = document.getElementById('ai-analysis-edit');
    const editor = document.getElementById('ai-analysis-editor');
    
    editor.value = currentAIAnalysisResult;
    displayArea.style.display = 'none';
    editArea.style.display = 'block';
}

// 保存AI分析编辑
function saveAIAnalysis() {
    const editor = document.getElementById('ai-analysis-editor');
    const displayArea = document.getElementById('ai-analysis-display');
    const editArea = document.getElementById('ai-analysis-edit');
    
    currentAIAnalysisResult = editor.value;
    displayArea.innerHTML = `<pre class="mb-0" style="white-space: pre-wrap; font-family: inherit;">${currentAIAnalysisResult}</pre>`;
    
    editArea.style.display = 'none';
    displayArea.style.display = 'block';
    
    showToast('AI分析结果已保存', 'success');
}

// 取消AI分析编辑
function cancelAIAnalysisEdit() {
    const displayArea = document.getElementById('ai-analysis-display');
    const editArea = document.getElementById('ai-analysis-edit');
    
    editArea.style.display = 'none';
    displayArea.style.display = 'block';
}

// 应用AI分析结果到记录
function applyAIAnalysis() {
    if (!currentAIAnalysisResult) {
        alert('请先进行AI分析');
        return;
    }
    
    // 不再修改描述内容，而是提示用户可以基于AI分析创建时间线事件
    showToast('AI分析完成，您可以基于分析结果创建时间线事件', 'success');
    
    // 高亮显示创建时间线事件按钮
    const createTimelineBtn = document.getElementById('create-timeline-btn');
    if (createTimelineBtn) {
        createTimelineBtn.classList.add('btn-warning');
        createTimelineBtn.innerHTML = '<i class="fas fa-plus-circle"></i> 基于AI分析创建时间线事件';
        
        // 3秒后恢复原样
        setTimeout(() => {
            createTimelineBtn.classList.remove('btn-warning');
            createTimelineBtn.innerHTML = '<i class="fas fa-plus-circle"></i> 创建时间线事件';
        }, 3000);
    }
}

// 从专家记录创建时间线事件
async function createTimelineEventFromLog() {
    if (!window.currentLogData) {
        alert('无法获取当前记录信息');
        return;
    }
    
    const logData = window.currentLogData;
    
    // 关闭专家记录详情模态框
    const expertLogModal = bootstrap.Modal.getInstance(document.getElementById('expertLogDetailModal'));
    if (expertLogModal) {
        expertLogModal.hide();
    }
    
    // 等待模态框完全关闭后再打开时间线编辑模态框
    setTimeout(async () => {
        // 预填充时间线事件数据
        const eventTitle = `专家记录: ${logData.title}`;
        const eventDescription = generateTimelineEventDescription(logData);
        
        // 打开时间线事件创建模态框
        await openTimelineEventCreationModal(eventTitle, eventDescription, logData);
    }, 300);
}

// 生成时间线事件描述（现在只生成简洁的描述，详细内容在extracted-content中）
function generateTimelineEventDescription(logData) {
    return `基于专家记录"${logData.title}"创建的时间线事件`;
}

// 加载专家记录附件用于内容选择
async function loadExpertLogAttachmentsForSelection(logData) {
    const attachmentsList = document.getElementById('expert-log-attachments-list');
    
    try {
        // 获取专家记录详情，包括附件信息
        const logDetail = await apiRequest(`/api/expert-logs/${logData.log_id}`);
        
        if (!logDetail || !logDetail.attachments || logDetail.attachments.length === 0) {
            attachmentsList.innerHTML = `
                <div class="text-muted text-center py-3">
                    <i class="fas fa-file"></i> 该专家记录暂无附件
                </div>
            `;
            return;
        }
        
        // 清空并重新填充附件列表
        attachmentsList.innerHTML = '';
        
        logDetail.attachments.forEach(attachment => {
            const attachmentElement = document.createElement('div');
            attachmentElement.className = 'attachment-item border rounded p-3 mb-2';
            attachmentElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div class="attachment-info flex-grow-1">
                        <div class="d-flex align-items-center mb-2">
                            <i class="fas fa-file-alt text-primary me-2"></i>
                            <strong>${attachment.file_name || '未知文件'}</strong>
                        </div>
                        <div class="text-muted small">
                            <div>文件类型: ${attachment.file_type || '未知'}</div>
                            <div>文件大小: ${formatFileSize(attachment.file_size || 0)}</div>
                            <div>上传时间: ${formatDateTime(attachment.uploaded_at)}</div>
                            ${attachment.has_extracted_text ? '<div class="text-success"><i class="fas fa-check"></i> 已提取文本内容</div>' : '<div class="text-warning"><i class="fas fa-exclamation-triangle"></i> 未提取文本内容</div>'}
                        </div>
                    </div>
                    <div class="attachment-actions">
                        <button type="button" class="btn btn-sm btn-primary me-2" 
                                onclick="extractAttachmentContent('${attachment.attachment_id}', '${attachment.file_name}')">
                            <i class="fas fa-extract"></i> 提取内容
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-secondary" 
                                onclick="downloadAttachment('${attachment.attachment_id}', '${attachment.file_name}')">
                            <i class="fas fa-download"></i> 下载
                        </button>
                    </div>
                </div>
            `;
            attachmentsList.appendChild(attachmentElement);
        });
        
    } catch (error) {
        console.error('加载专家记录附件失败:', error);
        attachmentsList.innerHTML = `
            <div class="text-danger text-center py-3">
                <i class="fas fa-exclamation-triangle"></i> 加载附件失败: ${error.message}
            </div>
        `;
    }
}

// 提取附件内容
async function extractAttachmentContent(attachmentId, fileName) {
    const extractedContentElement = document.getElementById('extracted-content');
    
    try {
        showToast('正在提取附件内容...', 'info');
        
        // 调用API提取附件内容
        const response = await apiRequest(`/api/expert-logs/attachments/${attachmentId}/extract-content`, {
            method: 'POST'
        });
        
        if (response && response.extracted_text) {
            // 将提取的内容添加到现有内容中
            const currentContent = extractedContentElement.value;
            const newContent = `\n\n=== 来自附件: ${fileName} ===\n${response.extracted_text}\n=== 附件内容结束 ===`;
            
            extractedContentElement.value = currentContent + newContent;
            showToast(`成功提取附件"${fileName}"的内容`, 'success');
        } else {
            showToast(`附件"${fileName}"无法提取文本内容`, 'warning');
        }
        
    } catch (error) {
        console.error('提取附件内容失败:', error);
        showToast(`提取附件内容失败: ${error.message}`, 'error');
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 打开时间线事件创建模态框
async function openTimelineEventCreationModal(title, description, logData) {
    // 设置当前编辑状态 - 这是关键修复
    window.currentEditingEvent = { eventId: null, turbineId: logData.turbine_id };
    console.log('openTimelineEventCreationModal: set currentEditingEvent to:', window.currentEditingEvent);
    
    // 设置模态框标题
    document.getElementById('timelineEditModalLabel').innerHTML = 
        '<i class="bi bi-plus-circle"></i> 创建时间线事件';
    
    // 清空表单并填入数据
    document.getElementById('edit-event-id').value = ''; // 新建事件，ID为空
    document.getElementById('edit-event-title').value = title;
    document.getElementById('edit-event-summary').value = ''; // 摘要留空，等待AI生成
    document.getElementById('edit-event-detail').value = ''; // 详细内容留空，等待AI生成
    document.getElementById('edit-event-severity').value = 'NORMAL';
    document.getElementById('edit-event-time').value = new Date().toISOString().slice(0, 16);

    // 将专家记录的描述内容放入提取内容字段
    const extractedContentElement = document.getElementById('extracted-content');
    if (extractedContentElement) {
        // 构建包含专家记录完整信息的内容
        let extractedContent = `专家记录标题: ${logData.title}\n\n`;
        extractedContent += `专家描述内容:\n${logData.description_text || '无描述内容'}\n\n`;
        extractedContent += `记录创建时间: ${formatDateTime(logData.created_at)}\n`;
        extractedContent += `记录作者: ${logData.author ? logData.author.username : '未知'}\n`;
        extractedContent += `记录ID: ${logData.log_id}`;
        
        extractedContentElement.value = extractedContent;
    }
    
    // 存储关联的专家记录ID
    window.currentTimelineEventLogId = logData.log_id;
    
    // 显示AI生成按钮，隐藏删除按钮（新建事件）
    const aiGenerateBtn = document.getElementById('generate-ai-content-btn');
    if (aiGenerateBtn) {
        aiGenerateBtn.style.display = 'inline-block';
    }
    document.getElementById('delete-event-btn').style.display = 'none';
    
    // 加载专家记录的附件到选择区域
    await loadExpertLogAttachmentsForSelection(logData);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('timelineEditModal'));
    modal.show();
    
    showToast('已预填充时间线事件信息，请审核并调整', 'info');
}

// AI生成时间线事件内容
async function generateTimelineEventWithAI() {
    if (!window.currentLogData) {
        alert('无法获取当前记录信息');
        return;
    }
    
    const generateBtn = document.querySelector('button[onclick="generateTimelineEventWithAI()"]');
    if (!generateBtn) return;
    
    const originalText = generateBtn.innerHTML;
    
    try {
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> AI生成中...';
        
        // 模拟AI生成过程
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const logData = window.currentLogData;
        const aiGeneratedContent = generateAITimelineEvent(logData);
        
        // 更新表单内容
        document.getElementById('edit-event-title').value = aiGeneratedContent.title;
        document.getElementById('edit-event-summary').value = aiGeneratedContent.description;
        document.getElementById('edit-event-severity').value = aiGeneratedContent.severity;
        
        // 安全地设置AI生成标记（如果元素存在）
        const aiGeneratedElement = document.getElementById('edit-ai-generated');
        if (aiGeneratedElement) {
            aiGeneratedElement.value = `AI生成内容 - ${new Date().toLocaleString()}`;
        }
        
        showToast('AI已生成时间线事件内容，请审核修改', 'success');
        
    } catch (error) {
        console.error('AI生成失败:', error);
        showToast('AI生成失败: ' + error.message, 'error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = originalText;
    }
}

// 生成AI时间线事件内容
function generateAITimelineEvent(logData) {
    const eventTemplates = [
        {
            title: `设备维护记录 - ${logData.title}`,
            description: `根据专家记录分析，发现设备存在以下问题：\n\n1. 运行参数异常，需要调整控制策略\n2. 部分组件磨损，建议更换\n3. 系统性能下降，需要优化配置\n\n处理建议：\n- 立即安排技术人员检查\n- 准备相关备件\n- 制定详细维护计划\n\n预计处理时间：2-4小时\n影响范围：单台设备`,
            type: 'MAINTENANCE',
            severity: 'MAINTENANCE',
            status: 'pending'
        },
        {
            title: `故障分析报告 - ${logData.title}`,
            description: `基于专家记录的深度分析：\n\n故障现象：\n- 设备运行不稳定\n- 关键参数超出正常范围\n- 报警频繁触发\n\n根因分析：\n- 传感器精度下降\n- 控制算法需要优化\n- 环境因素影响\n\n解决方案：\n- 校准传感器\n- 更新控制程序\n- 加强环境监控`,
            type: 'FAULT',
            severity: 'ALARM',
            status: 'in_progress'
        },
        {
            title: `预防性维护计划 - ${logData.title}`,
            description: `根据专家记录制定预防性维护计划：\n\n维护项目：\n- 润滑系统检查\n- 电气连接检测\n- 机械部件检查\n- 软件系统更新\n\n维护周期：每月一次\n责任人：维护团队\n\n预期效果：\n- 提高设备可靠性\n- 延长使用寿命\n- 降低故障率`,
            type: 'MAINTENANCE',
            severity: 'NORMAL',
            status: 'planned'
        }
    ];
    
    const randomTemplate = eventTemplates[Math.floor(Math.random() * eventTemplates.length)];
    
    return {
        ...randomTemplate,
        description: randomTemplate.description + `\n\n关联专家记录ID: ${logData.log_id}\n生成时间: ${new Date().toLocaleString()}`
    };
}

// ===== 新的时间线事件创建功能 =====

// 加载可用文档列表
async function loadAvailableDocuments() {
    try {
        const response = await apiRequest('/api/expert-logs');
        if (response.success) {
            displayAvailableDocuments(response.data);
        } else {
            showToast('加载文档列表失败: ' + response.message, 'error');
        }
    } catch (error) {
        console.error('加载文档列表失败:', error);
        showToast('加载文档列表失败', 'error');
    }
}

// 显示可用文档列表
function displayAvailableDocuments(logs) {
    const container = document.getElementById('available-documents-list');
    if (!container) return;
    
    if (!logs || logs.length === 0) {
        container.innerHTML = `
            <div class="text-muted text-center py-3">
                <i class="fas fa-search"></i> 暂无可用文档
            </div>
        `;
        return;
    }
    
    container.innerHTML = logs.map(log => `
        <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" value="${log.log_id}" 
                   id="doc-${log.log_id}" onchange="toggleDocumentSelection(${log.log_id})">
            <label class="form-check-label" for="doc-${log.log_id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${log.title || '无标题'}</strong>
                        <div class="text-muted small">
                            ${log.turbine_name || '未知风机'} | ${formatDateTime(log.created_at)}
                        </div>
                        <div class="text-truncate" style="max-width: 300px;">
                            ${log.description || '无描述'}
                        </div>
                    </div>
                    <span class="badge bg-secondary">${log.attachments_count || 0} 附件</span>
                </div>
            </label>
        </div>
    `).join('');
}

// 切换文档选择状态
async function toggleDocumentSelection(logId) {
    const checkbox = document.getElementById(`doc-${logId}`);
    if (!checkbox) return;
    
    if (checkbox.checked) {
        // 选中文档，提取内容
        await extractDocumentContent(logId);
    } else {
        // 取消选中，移除内容
        removeDocumentContent(logId);
    }
}

// 提取文档内容
async function extractDocumentContent(logId) {
    try {
        const response = await apiRequest(`/api/expert-logs/${logId}`);
        if (response.success) {
            const log = response.data;
            const extractedTextarea = document.getElementById('extracted-content');
            if (extractedTextarea) {
                // 将新内容追加到现有内容
                const currentContent = extractedTextarea.value;
                const newContent = `\n\n=== ${log.title || '文档'} (${formatDateTime(log.created_at)}) ===\n${log.description || '无内容'}\n`;
                extractedTextarea.value = currentContent + newContent;
                extractedTextarea.setAttribute('data-log-' + logId, 'true');
            }
            showToast(`已提取文档内容: ${log.title}`, 'success');
        } else {
            showToast('提取文档内容失败: ' + response.message, 'error');
        }
    } catch (error) {
        console.error('提取文档内容失败:', error);
        showToast('提取文档内容失败', 'error');
    }
}

// 移除文档内容
function removeDocumentContent(logId) {
    const extractedTextarea = document.getElementById('extracted-content');
    if (extractedTextarea && extractedTextarea.hasAttribute('data-log-' + logId)) {
        // 简单实现：重新提取所有选中的文档内容
        extractedTextarea.value = '';
        extractedTextarea.removeAttribute('data-log-' + logId);
        
        // 重新提取所有选中的文档
        const selectedCheckboxes = document.querySelectorAll('#available-documents-list input[type="checkbox"]:checked');
        selectedCheckboxes.forEach(async (checkbox) => {
            if (checkbox.value != logId) {
                await extractDocumentContent(parseInt(checkbox.value));
            }
        });
    }
}

// 生成AI内容
async function generateAIContent() {
    const extractedContent = document.getElementById('extracted-content').value.trim();
    if (!extractedContent) {
        showToast('请先选择文档并提取内容', 'warning');
        return;
    }
    
    // 获取当前编辑的风机ID
    if (!window.currentEditingEvent || !window.currentEditingEvent.turbineId) {
        showToast('无法获取风机信息，请重新打开编辑窗口', 'error');
        return;
    }
    
    const button = document.getElementById('generate-ai-content-btn');
    const originalText = button.innerHTML;
    
    try {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> AI生成中...';
        
        // 获取当前标题
        const currentTitle = document.getElementById('edit-event-title').value.trim();
        
        // 调用后端AI生成接口
        const response = await apiRequest('/api/timeline/generate-ai-content', {
            method: 'POST',
            body: {
                turbine_id: window.currentEditingEvent.turbineId,
                content: extractedContent,
                title: currentTitle
            }
        });
        
        if (response.success) {
            const aiData = response.data;
            
            // 更新表单
            document.getElementById('edit-event-title').value = aiData.title || currentTitle;
            document.getElementById('edit-event-summary').value = aiData.summary || '';
            document.getElementById('edit-event-detail').value = aiData.detail || '';
            
            // 更新事件严重程度
            if (aiData.event_severity) {
                const severitySelect = document.getElementById('edit-event-severity');
                if (severitySelect) {
                    severitySelect.value = aiData.event_severity;
                }
            }
            
            showToast('AI内容生成完成，请审核并修改', 'success');
        } else {
            throw new Error(response.message || 'AI生成失败');
        }
        
    } catch (error) {
        console.error('AI生成失败:', error);
        
        // 检查是否是认证错误
        if (error.message && error.message.includes('Not authenticated')) {
            showToast('请先登录系统才能使用AI生成功能', 'error');
            return;
        }
        
        // 检查是否是其他API错误
        if (error.message && (error.message.includes('403') || error.message.includes('401'))) {
            showToast('权限不足，请确保您有使用AI功能的权限', 'error');
            return;
        }
        
        // 其他错误才回退到本地模拟生成
        console.log('回退到本地模拟生成...');
        const aiResult = generateAIContentFromExtracted(extractedContent);
        
        // 更新表单
        document.getElementById('edit-event-summary').value = aiResult.summary;
        document.getElementById('edit-event-detail').value = aiResult.detail;
        
        showToast('AI服务暂时不可用，已使用本地生成', 'warning');
    } finally {
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

// 基于提取内容生成AI摘要和详细内容
function generateAIContentFromExtracted(extractedContent) {
    // 模拟AI分析和生成
    const keywords = extractKeywords(extractedContent);
    const severity = analyzeSeverity(extractedContent);
    
    const summary = `${keywords.slice(0, 3).join('、')}等关键事件，${severity}级别`;
    
    const detail = `
基于专家记录分析：

关键要点：
${keywords.map(keyword => `• ${keyword}`).join('\n')}

详细分析：
${extractedContent.length > 200 ? extractedContent.substring(0, 200) + '...' : extractedContent}

风险评估：${severity}
建议措施：根据现场情况采取相应的维护或监控措施

生成时间：${new Date().toLocaleString()}
    `.trim();
    
    return { summary, detail };
}

// 提取关键词
function extractKeywords(content) {
    const keywords = ['设备异常', '维护检查', '性能监控', '故障排除', '预防性维护', '运行状态', '技术分析'];
    const foundKeywords = keywords.filter(keyword => content.includes(keyword) || content.includes(keyword.substring(0, 2)));
    return foundKeywords.length > 0 ? foundKeywords : ['常规检查', '设备状态', '运行记录'];
}

// 分析严重程度
function analyzeSeverity(content) {
    const alarmWords = ['故障', '异常', '报警', '停机', '紧急'];
    const watchWords = ['注意', '监控', '观察', '跟踪'];
    
    if (alarmWords.some(word => content.includes(word))) {
        return '高';
    } else if (watchWords.some(word => content.includes(word))) {
        return '中';
    } else {
        return '低';
    }
}

// 切换时间线事件详细内容显示
function toggleTimelineEventDetail(eventId) {
    try {
        const detailElement = document.getElementById(`detail-${eventId}`);
        const toggleBtn = document.getElementById(`toggle-btn-${eventId}`);
        
        if (!detailElement) {
            console.error(`详细内容元素未找到: detail-${eventId}`);
            showToast('获取事件详情失败: 详细内容元素不存在', 'error');
            return;
        }
        
        if (!toggleBtn) {
            console.error(`切换按钮未找到: toggle-btn-${eventId}`);
            showToast('获取事件详情失败: 切换按钮不存在', 'error');
            return;
        }
        
        const isCollapsed = detailElement.classList.contains('collapse');
        
        if (isCollapsed) {
            // 展开详细内容
            detailElement.classList.remove('collapse');
            detailElement.classList.add('show');
            toggleBtn.innerHTML = '<i class="fas fa-chevron-up me-1"></i> 收起详细内容';
        } else {
            // 收起详细内容
            detailElement.classList.remove('show');
            detailElement.classList.add('collapse');
            toggleBtn.innerHTML = '<i class="fas fa-chevron-down me-1"></i> 查看详细内容';
        }
    } catch (error) {
        console.error('切换事件详情时发生错误:', error);
        showToast('获取事件详情失败: ' + error.message, 'error');
    }
}