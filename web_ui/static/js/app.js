/**
 * 松瓷机电AI助手WEB UI 主要JavaScript文件
 * 提供全局功能和Socket.IO连接管理
 */

// 全局变量
let socket = null;
let connectionStatus = 'disconnected';
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

// 初始化Socket.IO连接
function initializeSocket() {
    console.log('初始化Socket.IO连接...');
    
    socket = io({
        transports: ['websocket', 'polling'],
        timeout: 20000,
        reconnection: true,
        reconnectionAttempts: maxReconnectAttempts,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000
    });
    
    // 连接事件
    socket.on('connect', function() {
        console.log('Socket.IO连接成功');
        connectionStatus = 'connected';
        reconnectAttempts = 0;
        updateConnectionStatus('connected');
        showToast('连接成功', 'success');
    });
    
    socket.on('disconnect', function(reason) {
        console.log('Socket.IO连接断开:', reason);
        connectionStatus = 'disconnected';
        updateConnectionStatus('disconnected');
        showToast('连接断开: ' + reason, 'warning');
    });
    
    socket.on('connect_error', function(error) {
        console.error('Socket.IO连接错误:', error);
        connectionStatus = 'error';
        updateConnectionStatus('error');
        
        reconnectAttempts++;
        if (reconnectAttempts >= maxReconnectAttempts) {
            showToast('连接失败，请刷新页面重试', 'danger');
        }
    });
    
    socket.on('reconnect', function(attemptNumber) {
        console.log('Socket.IO重连成功，尝试次数:', attemptNumber);
        connectionStatus = 'connected';
        updateConnectionStatus('connected');
        showToast('重连成功', 'success');
    });
    
    socket.on('reconnect_attempt', function(attemptNumber) {
        console.log('Socket.IO重连尝试:', attemptNumber);
        connectionStatus = 'connecting';
        updateConnectionStatus('connecting');
    });
    
    socket.on('reconnect_failed', function() {
        console.error('Socket.IO重连失败');
        connectionStatus = 'failed';
        updateConnectionStatus('failed');
        showToast('重连失败，请刷新页面', 'danger');
    });
    
    // 系统消息
    socket.on('connected', function(data) {
        console.log('服务器确认连接:', data);
    });
    
    socket.on('error', function(data) {
        console.error('服务器错误:', data);
        showToast('服务器错误: ' + data.message, 'danger');
    });
    
    socket.on('system_status', function(data) {
        console.log('系统状态更新:', data);
        updateSystemStatus(data);
    });
    
    socket.on('system_update', function(data) {
        console.log('系统更新:', data);
        handleSystemUpdate(data);
    });
    
    // 心跳检测
    setInterval(function() {
        if (socket && socket.connected) {
            socket.emit('ping');
        }
    }, 30000); // 每30秒发送一次心跳
    
    socket.on('pong', function(data) {
        console.log('心跳响应:', data);
    });
}

// 更新连接状态显示
function updateConnectionStatus(status) {
    const statusIcon = document.getElementById('connection-status');
    const statusText = document.getElementById('status-text');
    
    if (!statusIcon || !statusText) return;
    
    // 移除所有状态类
    statusIcon.className = 'fas fa-circle me-1';
    
    switch (status) {
        case 'connected':
            statusIcon.classList.add('text-success');
            statusText.textContent = '已连接';
            statusIcon.title = '连接正常';
            break;
        case 'connecting':
            statusIcon.classList.add('text-warning');
            statusText.textContent = '连接中';
            statusIcon.title = '正在连接...';
            break;
        case 'disconnected':
            statusIcon.classList.add('text-secondary');
            statusText.textContent = '已断开';
            statusIcon.title = '连接已断开';
            break;
        case 'error':
        case 'failed':
            statusIcon.classList.add('text-danger');
            statusText.textContent = '连接失败';
            statusIcon.title = '连接失败';
            break;
    }
}

// 显示Toast消息
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: duration
    });
    
    toast.show();
    
    // 自动清理DOM
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// 显示加载遮罩
function showLoading(message = '加载中...') {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.querySelector('.loading-spinner div:last-child').textContent = message;
        overlay.classList.remove('d-none');
    }
}

// 隐藏加载遮罩
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('d-none');
    }
}

// 更新系统状态
function updateSystemStatus(status) {
    // 这里可以更新页面上的系统状态显示
    console.log('更新系统状态:', status);
}

// 处理系统更新
function handleSystemUpdate(update) {
    console.log('处理系统更新:', update);
    
    switch (update.type) {
        case 'model_loaded':
            showToast('模型加载完成', 'success');
            break;
        case 'model_error':
            showToast('模型加载失败: ' + update.data.error, 'danger');
            break;
        case 'config_updated':
            showToast('配置已更新', 'info');
            break;
        default:
            console.log('未知系统更新类型:', update.type);
    }
}

// API请求封装
class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
    }
    
    async request(endpoint, options = {}) {
        const url = this.baseURL + endpoint;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, finalOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }
    
    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }
    
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }
    
    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }
    
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}

// 创建全局API客户端实例
const api = new APIClient();

// 工具函数
const utils = {
    // 格式化时间
    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },
    
    // 格式化日期
    formatDate(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    },
    
    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // 节流函数
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // 复制到剪贴板
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            showToast('已复制到剪贴板', 'success');
        } catch (err) {
            console.error('复制失败:', err);
            showToast('复制失败', 'danger');
        }
    },
    
    // 下载文件
    downloadFile(content, filename, contentType = 'text/plain') {
        const blob = new Blob([content], { type: contentType });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }
};

// 全局错误处理
window.addEventListener('error', function(event) {
    console.error('全局错误:', event.error);
    showToast('发生未知错误，请刷新页面重试', 'danger');
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('未处理的Promise拒绝:', event.reason);
    showToast('网络请求失败，请检查网络连接', 'warning');
});

// 页面可见性变化处理
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('页面隐藏');
    } else {
        console.log('页面显示');
        // 页面重新显示时检查连接状态
        if (socket && !socket.connected) {
            socket.connect();
        }
    }
});

// 导出全局对象
window.AIAssistant = {
    socket,
    api,
    utils,
    showToast,
    showLoading,
    hideLoading,
    updateConnectionStatus
};
