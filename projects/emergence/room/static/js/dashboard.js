// Room Dashboard - Nautilus Widget
// Real-time WebSocket updates for memory palace monitoring

const socket = io();
let chamberChart = null;

// Format bytes to human readable
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

// Format timestamp
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + ' min ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + ' hr ago';
    if (diff < 604800000) return Math.floor(diff / 86400000) + ' days ago';
    
    return date.toLocaleDateString();
}

// Format path to be more readable
function formatPath(path) {
    // Shorten long paths
    const parts = path.split('/');
    if (parts.length > 3) {
        return '.../' + parts.slice(-2).join('/');
    }
    return path;
}

// Initialize chamber chart
function initializeChamberChart() {
    const ctx = document.getElementById('chamberChart').getContext('2d');
    
    chamberChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Atrium (48h)', 'Corridor (48h-7d)', 'Vault (7d+)'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [
                    '#3498db',  // atrium
                    '#9b59b6',  // corridor
                    '#f39c12'   // vault
                ],
                borderWidth: 2,
                borderColor: '#1a1f3a'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Update chamber chart with new data
function updateChamberChart(atrium, corridor, vault) {
    if (chamberChart) {
        chamberChart.data.datasets[0].data = [atrium, corridor, vault];
        chamberChart.update();
    }
    
    // Update counts in legend
    document.getElementById('atrium-count').textContent = atrium;
    document.getElementById('corridor-count').textContent = corridor;
    document.getElementById('vault-count').textContent = vault;
}

// Update dashboard with Nautilus status
function updateDashboard(data) {
    console.log('Updating dashboard with data:', data);
    
    if (data.error) {
        console.error('Error in data:', data.error);
        return;
    }
    
    // Update last update time
    const lastUpdate = document.getElementById('last-update');
    lastUpdate.textContent = `Updated ${formatTimestamp(data.timestamp)}`;
    
    // Update overview stats
    document.getElementById('total-chunks').textContent = 
        data.gravity?.total_chunks?.toLocaleString() || '-';
    document.getElementById('total-accesses').textContent = 
        `${data.gravity?.total_accesses?.toLocaleString() || 0} accesses`;
    
    document.getElementById('door-coverage').textContent = 
        `${data.doors?.coverage_pct || 0}%`;
    document.getElementById('door-stats').textContent = 
        `${data.doors?.tagged_files || 0} / ${data.doors?.total_files || 0} tagged`;
    
    document.getElementById('db-size').textContent = 
        formatBytes(data.gravity?.db_size_bytes || 0);
    
    document.getElementById('mirror-events').textContent = 
        data.mirrors?.total_events?.toLocaleString() || '-';
    document.getElementById('mirror-coverage').textContent = 
        `${data.mirrors?.fully_mirrored || 0} fully mirrored`;
    
    // Update chamber distribution chart
    const atrium = data.chambers?.atrium || 0;
    const corridor = data.chambers?.corridor || 0;
    const vault = data.chambers?.vault || 0;
    updateChamberChart(atrium, corridor, vault);
    
    // Update recent promotions
    updatePromotions(data.chambers?.recent_promotions || []);
    
    // Update top memories
    updateTopMemories(data.gravity?.top_memories || []);
    
    // Update top contexts
    updateTopContexts(data.doors?.top_contexts || []);
}

// Update promotions list
function updatePromotions(promotions) {
    const container = document.getElementById('promotions-list');
    
    if (promotions.length === 0) {
        container.innerHTML = '<div class="loading">No recent promotions</div>';
        return;
    }
    
    container.innerHTML = promotions.map(p => `
        <div class="promotion-item ${p.chamber}">
            <div class="memory-path" title="${p.path}">${formatPath(p.path)}</div>
            <div style="display: flex; gap: 0.5rem; align-items: center; margin-top: 0.5rem;">
                <span class="chamber-badge ${p.chamber}">${p.chamber}</span>
                <span style="color: var(--text-secondary); font-size: 0.85rem;">
                    ${formatTimestamp(p.promoted_at)}
                </span>
            </div>
        </div>
    `).join('');
}

// Update top memories list
function updateTopMemories(memories) {
    const container = document.getElementById('top-memories-list');
    
    if (memories.length === 0) {
        container.innerHTML = '<div class="loading">No memories tracked yet</div>';
        return;
    }
    
    container.innerHTML = memories.map(m => `
        <div class="memory-item">
            <div>
                <div class="memory-path" title="${m.path}">${formatPath(m.path)}</div>
                <div style="margin-top: 0.5rem;">
                    <span class="chamber-badge ${m.chamber}">${m.chamber}</span>
                </div>
            </div>
            <div class="memory-stats">
                <div>
                    <span class="memory-score">${m.score}</span>
                    <div style="font-size: 0.75rem;">gravity</div>
                </div>
                <div>
                    <span>${m.accesses}</span>
                    <div style="font-size: 0.75rem;">reads</div>
                </div>
                <div>
                    <span>${m.references || 0}</span>
                    <div style="font-size: 0.75rem;">refs</div>
                </div>
            </div>
        </div>
    `).join('');
}

// Update top contexts list
function updateTopContexts(contexts) {
    const container = document.getElementById('contexts-list');
    
    if (contexts.length === 0) {
        container.innerHTML = '<div class="loading">No tags yet</div>';
        return;
    }
    
    container.innerHTML = contexts.map(c => `
        <div class="context-tag">
            <span>${c.tag}</span>
            <span class="count">${c.count}</span>
        </div>
    `).join('');
}

// WebSocket event handlers
socket.on('connect', () => {
    console.log('Connected to Room dashboard');
    document.getElementById('connection-status').classList.add('connected');
    document.getElementById('connection-text').textContent = 'Connected';
});

socket.on('disconnect', () => {
    console.log('Disconnected from Room dashboard');
    document.getElementById('connection-status').classList.remove('connected');
    document.getElementById('connection-status').classList.add('disconnected');
    document.getElementById('connection-text').textContent = 'Disconnected';
});

socket.on('connected', (data) => {
    console.log('Server says:', data.message);
});

socket.on('nautilus_update', (data) => {
    console.log('Received Nautilus update');
    updateDashboard(data);
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard loaded');
    initializeChamberChart();
    
    // Request initial update
    socket.emit('request_update');
});

// Manual refresh button (could be added to UI)
function refreshData() {
    socket.emit('request_update');
}
