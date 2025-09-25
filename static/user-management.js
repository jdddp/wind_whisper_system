// 用户管理相关函数
let currentUsersPage = 1;
const usersPerPage = 10;
let allUsers = [];

// 根据用户角色显示/隐藏功能
function updateUIBasedOnUserRole() {
    if (!currentUser) {
        // 未登录时隐藏所有需要权限的菜单
        hideAllRestrictedMenus();
        return;
    }
    
    const userRole = currentUser.role;
    
    // 用户管理菜单项 - 只有ADMIN角色可以访问
    const userManagementNav = document.getElementById('user-management-nav');
    if (userRole === 'ADMIN') {
        if (userManagementNav) userManagementNav.style.display = 'block';
    } else {
        if (userManagementNav) userManagementNav.style.display = 'none';
    }
    
    // 专家记录菜单项 - 只有ADMIN和EXPERT角色可以访问
    const expertLogsNav = document.querySelector('a[onclick="showSection(\'expert-logs\')"]');
    if (expertLogsNav) {
        const expertLogsNavItem = expertLogsNav.closest('.nav-item');
        if (userRole === 'ADMIN' || userRole === 'EXPERT') {
            if (expertLogsNavItem) expertLogsNavItem.style.display = 'block';
        } else {
            if (expertLogsNavItem) expertLogsNavItem.style.display = 'none';
        }
    }
    
    // 风机管理菜单项 - 只有ADMIN和EXPERT角色可以访问
    const turbinesNav = document.querySelector('a[onclick="showSection(\'turbines\')"]');
    if (turbinesNav) {
        const turbinesNavItem = turbinesNav.closest('.nav-item');
        if (userRole === 'ADMIN' || userRole === 'EXPERT') {
            if (turbinesNavItem) turbinesNavItem.style.display = 'block';
        } else {
            if (turbinesNavItem) turbinesNavItem.style.display = 'none';
        }
    }
    
    // 驾驶舱、RAG问答、时间线 - 所有角色都可以访问，保持显示
    const dashboardNav = document.querySelector('a[onclick="showSection(\'dashboard\')"]');
    const ragNav = document.querySelector('a[onclick="showSection(\'rag\')"]');
    const timelineNav = document.querySelector('a[onclick="showSection(\'timeline\')"]');
    
    if (dashboardNav) {
        const dashboardNavItem = dashboardNav.closest('.nav-item');
        if (dashboardNavItem) dashboardNavItem.style.display = 'block';
    }
    if (ragNav) {
        const ragNavItem = ragNav.closest('.nav-item');
        if (ragNavItem) ragNavItem.style.display = 'block';
    }
    if (timelineNav) {
        const timelineNavItem = timelineNav.closest('.nav-item');
        if (timelineNavItem) timelineNavItem.style.display = 'block';
    }
}

// 隐藏所有需要权限的菜单项
function hideAllRestrictedMenus() {
    const userManagementNav = document.getElementById('user-management-nav');
    const expertLogsNav = document.querySelector('a[onclick="showSection(\'expert-logs\')"]');
    const turbinesNav = document.querySelector('a[onclick="showSection(\'turbines\')"]');
    
    if (userManagementNav) userManagementNav.style.display = 'none';
    
    if (expertLogsNav) {
        const expertLogsNavItem = expertLogsNav.closest('.nav-item');
        if (expertLogsNavItem) expertLogsNavItem.style.display = 'none';
    }
    
    if (turbinesNav) {
        const turbinesNavItem = turbinesNav.closest('.nav-item');
        if (turbinesNavItem) turbinesNavItem.style.display = 'none';
    }
}

// 加载用户列表
async function loadUsers(page = 1, role = '', search = '') {
    // 检查用户权限
    if (!currentUser || currentUser.role !== 'ADMIN') {
        showToast('您没有权限访问用户管理功能', 'error');
        return;
    }
    
    try {
        const params = new URLSearchParams({
            page: page.toString(),
            size: usersPerPage.toString()
        });
        
        if (role) params.append('role', role);
        if (search) params.append('search', search);
        
        const response = await apiRequest(`/auth/users?${params}`);
        
        if (response.users) {
            allUsers = response.users;
            displayUsersTable(response.users);
            displayUsersPagination(response.total, page);
        }
    } catch (error) {
        console.error('加载用户列表失败:', error);
        showToast('加载用户列表失败', 'error');
    }
}

// 显示用户表格
function displayUsersTable(users) {
    const tbody = document.getElementById('users-table-body');
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">暂无用户数据</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.user_id}</td>
            <td>${user.username}</td>
            <td>
                <span class="badge bg-${getRoleBadgeColor(user.role)}">
                    ${getRoleLabel(user.role)}
                </span>
            </td>
            <td>${formatDateTime(user.created_at)}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editUser('${user.user_id}')" title="编辑">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteUser('${user.user_id}', '${user.username}')" 
                            title="删除" ${user.user_id === currentUser.user_id ? 'disabled' : ''}>
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// 显示用户分页
function displayUsersPagination(total, currentPage) {
    const totalPages = Math.ceil(total / usersPerPage);
    const pagination = document.getElementById('users-pagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let paginationHTML = '';
    
    // 上一页
    if (currentPage > 1) {
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadUsers(${currentPage - 1}, document.getElementById('user-role-filter').value, document.getElementById('user-search').value)">上一页</a>
            </li>
        `;
    }
    
    // 页码
    for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
        paginationHTML += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="loadUsers(${i}, document.getElementById('user-role-filter').value, document.getElementById('user-search').value)">${i}</a>
            </li>
        `;
    }
    
    // 下一页
    if (currentPage < totalPages) {
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadUsers(${currentPage + 1}, document.getElementById('user-role-filter').value, document.getElementById('user-search').value)">下一页</a>
            </li>
        `;
    }
    
    pagination.innerHTML = paginationHTML;
}

// 获取角色标签颜色
function getRoleBadgeColor(role) {
    switch (role) {
        case 'ADMIN': return 'danger';
        case 'EXPERT': return 'warning';
        case 'READER': return 'primary';
        default: return 'secondary';
    }
}

// 获取角色标签
function getRoleLabel(role) {
    switch (role) {
        case 'ADMIN': return '管理员';
        case 'EXPERT': return '专家';
        case 'READER': return '普通用户';
        default: return '未知';
    }
}

// 搜索用户
function searchUsers() {
    const search = document.getElementById('user-search').value;
    const role = document.getElementById('user-role-filter').value;
    loadUsers(1, role, search);
}

// 显示创建用户模态框
function showCreateUserModal() {
    // 检查用户权限
    if (!currentUser || currentUser.role !== 'ADMIN') {
        showToast('您没有权限创建用户', 'error');
        return;
    }
    
    // 管理员可以创建所有角色
    const roleSelect = document.getElementById('create-role');
    roleSelect.innerHTML = `
        <option value="">请选择角色</option>
        <option value="READER">普通用户</option>
        <option value="EXPERT">专家用户</option>
        <option value="ADMIN">管理员</option>
    `;
    
    // 清空表单
    document.getElementById('create-user-form').reset();
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('createUserModal'));
    modal.show();
}

// 创建用户
async function createUser() {
    // 检查用户权限
    if (!currentUser || currentUser.role !== 'ADMIN') {
        showToast('您没有权限创建用户', 'error');
        return;
    }
    
    const username = document.getElementById('create-username').value;
    const password = document.getElementById('create-password').value;
    const role = document.getElementById('create-role').value;
    
    if (!username || !password || !role) {
        showToast('请填写所有必填字段', 'error');
        return;
    }
    
    try {
        await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                username,
                password,
                role
            })
        });
        
        showToast('用户创建成功', 'success');
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('createUserModal'));
        modal.hide();
        
        // 重新加载用户列表
        loadUsers();
        
    } catch (error) {
        console.error('创建用户失败:', error);
        showToast(error.message || '创建用户失败', 'error');
    }
}

// 编辑用户
async function editUser(userId) {
    // 检查用户权限
    if (!currentUser || currentUser.role !== 'ADMIN') {
        showToast('您没有权限编辑用户', 'error');
        return;
    }
    
    try {
        const response = await apiRequest(`/auth/users/${userId}`);
        
        // 填充表单
        document.getElementById('edit-user-id').value = response.user_id;
        document.getElementById('edit-username').value = response.username;
        document.getElementById('edit-password').value = '';
        
        // 管理员可以编辑所有角色
        const roleSelect = document.getElementById('edit-role');
        roleSelect.innerHTML = `
            <option value="READER">普通用户</option>
            <option value="EXPERT">专家用户</option>
            <option value="ADMIN">管理员</option>
        `;
        
        roleSelect.value = response.role;
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
        modal.show();
        
    } catch (error) {
        console.error('获取用户信息失败:', error);
        showToast('获取用户信息失败', 'error');
    }
}

// 更新用户
async function updateUser() {
    // 检查用户权限
    if (!currentUser || currentUser.role !== 'ADMIN') {
        showToast('您没有权限更新用户', 'error');
        return;
    }
    
    const userId = document.getElementById('edit-user-id').value;
    const password = document.getElementById('edit-password').value;
    const role = document.getElementById('edit-role').value;
    
    const updateData = { role };
    if (password) {
        updateData.password = password;
    }
    
    try {
        await apiRequest(`/auth/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });
        
        showToast('用户更新成功', 'success');
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
        modal.hide();
        
        // 重新加载用户列表
        loadUsers();
        
    } catch (error) {
        console.error('更新用户失败:', error);
        showToast(error.message || '更新用户失败', 'error');
    }
}

// 删除用户
async function deleteUser(userId, username) {
    // 检查用户权限
    if (!currentUser || currentUser.role !== 'ADMIN') {
        showToast('您没有权限删除用户', 'error');
        return;
    }
    
    if (userId === currentUser.user_id) {
        showToast('不能删除自己的账户', 'error');
        return;
    }
    
    if (!confirm(`确定要删除用户 "${username}" 吗？此操作不可撤销。`)) {
        return;
    }
    
    try {
        await apiRequest(`/auth/users/${userId}`, {
            method: 'DELETE'
        });
        
        showToast('用户删除成功', 'success');
        
        // 重新加载用户列表
        loadUsers();
        
    } catch (error) {
        console.error('删除用户失败:', error);
        showToast(error.message || '删除用户失败', 'error');
    }
}

// 页面加载时初始化用户管理功能
document.addEventListener('DOMContentLoaded', function() {
    // 监听用户登录状态变化
    const originalUpdateUserInfo = window.updateUserInfo;
    window.updateUserInfo = function() {
        if (originalUpdateUserInfo) {
            originalUpdateUserInfo();
        }
        updateUIBasedOnUserRole();
    };
});