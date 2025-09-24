// 时间线事件编辑功能

// 当前编辑的事件 - 声明为全局变量
window.currentEditingEvent = null;

// 打开时间线事件编辑模态框
async function openTimelineEditModal(eventId, turbineId) {
    window.currentEditingEvent = { eventId, turbineId };
    
    try {
        // 获取事件详情
        const event = await apiRequest(`/api/timeline/${eventId}`);
        
        if (event.error) {
            showAlert('获取事件详情失败: ' + event.error, 'danger');
            return;
        }
        
        // 填充表单
        populateEditForm(event);
        
        // 显示删除按钮（编辑现有事件时）
        document.getElementById('delete-event-btn').style.display = 'inline-block';
        
        // 更新模态框标题
        document.getElementById('timelineEditModalLabel').innerHTML = 
            '<i class="bi bi-pencil-square"></i> 编辑时间线事件';
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('timelineEditModal'));
        modal.show();
    } catch (error) {
        console.error('获取事件详情失败:', error);
        showAlert('获取事件详情失败', 'danger');
    }
}

// 填充编辑表单
function populateEditForm(event) {
    document.getElementById('edit-event-id').value = event.event_id;
    
    // 格式化时间为datetime-local格式
    if (event.event_time) {
        const eventTime = new Date(event.event_time);
        const localTime = new Date(eventTime.getTime() - eventTime.getTimezoneOffset() * 60000);
        document.getElementById('edit-event-time').value = localTime.toISOString().slice(0, 16);
    }
    
    document.getElementById('edit-event-type').value = event.event_type || '';
    document.getElementById('edit-event-severity').value = event.event_severity || '';
    document.getElementById('edit-confidence-score').value = event.confidence_score || '';
    document.getElementById('edit-event-title').value = event.title || '';
    document.getElementById('edit-event-summary').value = event.summary || '';
    
    // 处理关键点数组
    if (event.key_points && Array.isArray(event.key_points)) {
        document.getElementById('edit-key-points').value = event.key_points.join('\n');
    } else {
        document.getElementById('edit-key-points').value = '';
    }
    
    document.getElementById('edit-ai-generated').value = event.ai_generated_content || '';
}

// 保存时间线事件
async function saveTimelineEvent() {
    console.log('saveTimelineEvent called, currentEditingEvent:', window.currentEditingEvent);
    if (!window.currentEditingEvent) {
        console.error('currentEditingEvent is null or undefined');
        showAlert('没有正在编辑的事件', 'danger');
        return;
    }
    
    const form = document.getElementById('timelineEditForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    // 收集表单数据
    const eventData = {
        event_time: document.getElementById('edit-event-time').value,
        event_type: document.getElementById('edit-event-type').value,
        event_severity: document.getElementById('edit-event-severity').value,
        confidence_score: parseFloat(document.getElementById('edit-confidence-score').value) || null,
        title: document.getElementById('edit-event-title').value,
        summary: document.getElementById('edit-event-summary').value,
        key_points: document.getElementById('edit-key-points').value
            .split('\n')
            .map(point => point.trim())
            .filter(point => point.length > 0),
        source_log_ids: []  // 添加source_log_ids字段，默认为空数组
    };
    
    // 根据是否有eventId决定是创建还是更新
    const isNewEvent = !window.currentEditingEvent.eventId;
    
    if (isNewEvent) {
        // 创建新事件，需要添加turbine_id
        eventData.turbine_id = window.currentEditingEvent.turbineId;
        
        // 如果是从专家记录创建，添加专家记录ID
        if (window.currentTimelineEventLogId) {
            eventData.source_log_ids = [window.currentTimelineEventLogId];
        }
    }
    
    const url = isNewEvent ? '/api/timeline/create' : `/api/timeline/${window.currentEditingEvent.eventId}`;
    const method = isNewEvent ? 'POST' : 'PUT';
    
    try {
        // 发送请求
        const result = await apiRequest(url, {
            method: method,
            body: eventData
        });
        
        console.log('API响应:', result);  // 添加调试信息
        
        // 成功响应包含event_id字段
        if (result && result.event_id) {
            showAlert(`事件${isNewEvent ? '创建' : '保存'}成功`, 'success');
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('timelineEditModal'));
            if (modal) {
                modal.hide();
            }
            
            // 刷新时间线显示 - 使用正确的turbineId
            const turbineId = isNewEvent ? eventData.turbine_id : window.currentEditingEvent.turbineId;
            if (turbineId) {
                // 设置时间线过滤器为当前风机
                document.getElementById('timeline-turbine-filter').value = turbineId;
                loadTimeline();
            }
            
            window.currentEditingEvent = null;
            window.currentTimelineEventLogId = null;  // 清理专家记录ID
        } else {
            console.error('API响应格式错误:', result);
            showAlert(`${isNewEvent ? '创建' : '保存'}失败: 响应格式错误`, 'danger');
        }
    } catch (error) {
        console.error(`${isNewEvent ? '创建' : '保存'}事件失败:`, error);
        showAlert(`${isNewEvent ? '创建' : '保存'}事件失败: ${error.message}`, 'danger');
    }
}

// 删除时间线事件
async function deleteTimelineEvent() {
    if (!window.currentEditingEvent) {
        showAlert('没有正在编辑的事件', 'danger');
        return;
    }
    
    if (!confirm('确定要删除这个时间线事件吗？此操作不可撤销。')) {
        return;
    }
    
    try {
        const result = await apiRequest(`/api/timeline/${window.currentEditingEvent.eventId}`, {
            method: 'DELETE'
        });
        
        if (result.error) {
            showAlert('删除失败: ' + result.error, 'danger');
            return;
        }
        
        showAlert('事件删除成功', 'success');
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('timelineEditModal'));
        modal.hide();
        
        // 刷新时间线显示
        if (window.currentEditingEvent.turbineId) {
            document.getElementById('timeline-turbine-filter').value = window.currentEditingEvent.turbineId;
            loadTimeline();
        }
        
        window.currentEditingEvent = null;
    } catch (error) {
        console.error('删除事件失败:', error);
        showAlert('删除事件失败: ' + error.message, 'danger');
    }
}

// 创建新的时间线事件
function createTimelineEvent(turbineId) {
    // 清空表单
    document.getElementById('timelineEditForm').reset();
    document.getElementById('edit-event-id').value = '';
    document.getElementById('edit-ai-generated').value = '';
    
    // 设置默认值
    const now = new Date();
    const localTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    document.getElementById('edit-event-time').value = localTime.toISOString().slice(0, 16);
    
    // 隐藏删除按钮（新建事件时）
    document.getElementById('delete-event-btn').style.display = 'none';
    
    // 更新模态框标题
    document.getElementById('timelineEditModalLabel').innerHTML = 
        '<i class="bi bi-plus-circle"></i> 创建时间线事件';
    
    // 设置当前编辑状态
    window.currentEditingEvent = { eventId: null, turbineId: turbineId };
    console.log('createTimelineEvent: set currentEditingEvent to:', window.currentEditingEvent);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('timelineEditModal'));
    modal.show();
}



// 批量编辑时间线事件
function batchEditTimelineEvents(turbineId) {
    // 获取选中的事件
    const selectedEvents = getSelectedTimelineEvents();
    
    if (selectedEvents.length === 0) {
        showAlert('请先选择要编辑的事件', 'warning');
        return;
    }
    
    // 显示批量编辑界面
    showBatchEditModal(selectedEvents, turbineId);
}

// 获取选中的时间线事件
function getSelectedTimelineEvents() {
    const checkboxes = document.querySelectorAll('.timeline-event-checkbox:checked');
    return Array.from(checkboxes).map(checkbox => checkbox.value);
}

// 显示批量编辑模态框
function showBatchEditModal(eventIds, turbineId) {
    // 这里可以实现批量编辑的界面
    // 暂时使用简单的确认对话框
    const action = prompt('批量操作选项:\n1. 批量删除\n2. 批量修改类型\n3. 批量修改严重程度\n\n请输入选项编号:');
    
    switch(action) {
        case '1':
            batchDeleteEvents(eventIds, turbineId);
            break;
        case '2':
            batchUpdateEventType(eventIds, turbineId);
            break;
        case '3':
            batchUpdateEventSeverity(eventIds, turbineId);
            break;
        default:
            showAlert('无效的选项', 'warning');
    }
}

// 批量删除事件
async function batchDeleteEvents(eventIds, turbineId) {
    if (!confirm(`确定要删除选中的 ${eventIds.length} 个事件吗？此操作不可撤销。`)) {
        return;
    }
    
    try {
        const results = await Promise.all(eventIds.map(eventId => 
            apiRequest(`/api/timeline/${eventId}`, { 
                method: 'DELETE'
            }).catch(error => ({ error: error.message }))
        ));
        
        const successCount = results.filter(r => !r.error).length;
        const errorCount = results.length - successCount;
        
        if (errorCount === 0) {
            showAlert(`成功删除 ${successCount} 个事件`, 'success');
        } else {
            showAlert(`删除完成：成功 ${successCount} 个，失败 ${errorCount} 个`, 'warning');
        }
        
        // 刷新时间线显示
        document.getElementById('timeline-turbine-filter').value = turbineId;
        loadTimeline();
    } catch (error) {
        console.error('批量删除失败:', error);
        showAlert('批量删除失败', 'danger');
    }
}

// 批量更新事件类型
function batchUpdateEventType(eventIds, turbineId) {
    const newType = prompt('请输入新的事件类型:\nMAINTENANCE - 维护\nFAULT - 故障\nINSPECTION - 检查\nREPAIR - 维修\nUPGRADE - 升级\nOTHER - 其他');
    
    if (!newType) return;
    
    const validTypes = ['MAINTENANCE', 'FAULT', 'INSPECTION', 'REPAIR', 'UPGRADE', 'OTHER'];
    if (!validTypes.includes(newType)) {
        showAlert('无效的事件类型', 'danger');
        return;
    }
    
    batchUpdateEvents(eventIds, { event_type: newType }, turbineId);
}

// 批量更新事件严重程度
function batchUpdateEventSeverity(eventIds, turbineId) {
    const newSeverity = prompt('请输入新的严重程度:\nLOW - 低\nMEDIUM - 中\nHIGH - 高\nCRITICAL - 严重');
    
    if (!newSeverity) return;
    
    const validSeverities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
    if (!validSeverities.includes(newSeverity)) {
        showAlert('无效的严重程度', 'danger');
        return;
    }
    
    batchUpdateEvents(eventIds, { severity: newSeverity }, turbineId);
}

// 批量更新事件
async function batchUpdateEvents(eventIds, updateData, turbineId) {
    try {
        const results = await Promise.all(eventIds.map(eventId => 
            apiRequest(`/api/timeline/${eventId}`, {
                method: 'PUT',
                body: updateData
            }).catch(error => ({ error: error.message }))
        ));
        
        const successCount = results.filter(r => !r.error).length;
        const errorCount = results.length - successCount;
        
        if (errorCount === 0) {
            showAlert(`成功更新 ${successCount} 个事件`, 'success');
        } else {
            showAlert(`更新完成：成功 ${successCount} 个，失败 ${errorCount} 个`, 'warning');
        }
        
        // 刷新时间线显示
        document.getElementById('timeline-turbine-filter').value = turbineId;
        loadTimeline();
    } catch (error) {
        console.error('批量更新失败:', error);
        showAlert('批量更新失败', 'danger');
    }
}

// 在时间线事件显示中添加编辑按钮
function addEditButtonToTimelineEvent(eventElement, eventId, turbineId) {
    const editButton = document.createElement('button');
    editButton.className = 'btn btn-sm btn-outline-primary me-1';
    editButton.innerHTML = '<i class="bi bi-pencil"></i>';
    editButton.title = '编辑事件';
    editButton.onclick = () => openTimelineEditModal(eventId, turbineId);
    
    // 找到事件的操作按钮容器并添加编辑按钮
    const actionsContainer = eventElement.querySelector('.timeline-event-actions');
    if (actionsContainer) {
        actionsContainer.prepend(editButton);
    }
}

// 显示提示信息
function showAlert(message, type = 'info') {
    // 创建提示框
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // 3秒后自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}