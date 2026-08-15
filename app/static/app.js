// State management
let activeWorkItemId = null;
let workItems = [];
let activeActionId = null;

// DOM Elements
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const intakeForm = document.getElementById('intake-form');
const intakeText = document.getElementById('intake-text');
const intakeSubmitBtn = document.getElementById('intake-submit-btn');
const intakeSpinner = document.getElementById('intake-spinner');
const workItemsList = document.getElementById('work-items-list');

const noSelectionState = document.getElementById('no-selection-state');
const detailPanel = document.getElementById('detail-panel');
const taskTitle = document.getElementById('task-title');
const taskPriority = document.getElementById('task-priority');
const taskStatus = document.getElementById('task-status');
const taskSummary = document.getElementById('task-summary');
const taskDeadline = document.getElementById('task-deadline');
const taskTimestamp = document.getElementById('task-timestamp');

const warningsContainer = document.getElementById('warnings-container');
const missingInfoCard = document.getElementById('missing-info-card');
const missingInfoList = document.getElementById('missing-info-list');

const actionItemsList = document.getElementById('action-items-list');
const activityLog = document.getElementById('activity-log');

const editModal = document.getElementById('edit-modal');
const editDesc = document.getElementById('edit-desc');
const editOutput = document.getElementById('edit-output');
const modalCancelBtn = document.getElementById('modal-cancel-btn');
const modalApproveBtn = document.getElementById('modal-approve-btn');

// Initial Setup
document.addEventListener('DOMContentLoaded', () => {
    fetchWorkItems();
    
    // Event listeners
    intakeForm.addEventListener('submit', handleIntakeSubmit);
    searchBtn.addEventListener('click', () => fetchWorkItems(searchInput.value));
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            fetchWorkItems(searchInput.value);
        }
    });
    
    modalCancelBtn.addEventListener('click', hideEditModal);
    modalApproveBtn.addEventListener('click', submitActionEdit);
});

// Fetch all work items
async function fetchWorkItems(query = '') {
    try {
        let url = '/api/work-items';
        if (query) {
            url += `?q=${encodeURIComponent(query)}`;
        }
        const response = await fetch(url);
        workItems = await response.json();
        renderWorkItemsList();
    } catch (error) {
        console.error('Error fetching work items:', error);
    }
}

// Render left pane list of work items
function renderWorkItemsList() {
    if (workItems.length === 0) {
        workItemsList.innerHTML = '<div class="empty-state">No work items found.</div>';
        return;
    }
    
    workItemsList.innerHTML = '';
    workItems.forEach(item => {
        const card = document.createElement('div');
        card.className = `work-item-card ${activeWorkItemId === item.id ? 'active' : ''}`;
        card.onclick = () => selectWorkItem(item.id);
        
        // Priority class
        const pClass = `badge-${item.priority.toLowerCase()}`;
        
        // Status class
        const sClass = `status-${item.status.toLowerCase()}`;
        
        // Format date
        const dateStr = new Date(item.created_at).toLocaleString();
        
        card.innerHTML = `
            <div class="card-header">
                <h3>${item.title || 'Untitled Request'}</h3>
                <span class="badge ${pClass}">${item.priority}</span>
            </div>
            <div class="card-body">${item.summary || 'Parsing request...'}</div>
            <div class="card-footer">
                <span class="badge-status ${sClass}">${item.status.replace('_', ' ')}</span>
                <span class="card-time">${dateStr}</span>
            </div>
        `;
        
        workItemsList.appendChild(card);
    });
}

// Handle submitting new unstructured text
async function handleIntakeSubmit(e) {
    e.preventDefault();
    const text = intakeText.value.trim();
    if (!text) return;
    
    // Set loading state
    intakeSubmitBtn.disabled = true;
    intakeSpinner.style.display = 'block';
    
    try {
        const response = await fetch('/api/intake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to process request.');
        }
        
        const newItem = await response.json();
        intakeText.value = '';
        
        // Refresh items and select the new one
        await fetchWorkItems();
        selectWorkItem(newItem.id);
        
    } catch (error) {
        alert(`Error: ${error.message}`);
    } finally {
        intakeSubmitBtn.disabled = false;
        intakeSpinner.style.display = 'none';
    }
}

// Select and load work item details
async function selectWorkItem(id) {
    activeWorkItemId = id;
    
    // Highlight in list
    const cards = document.querySelectorAll('.work-item-card');
    cards.forEach(card => card.classList.remove('active'));
    // Render list again to update active class
    renderWorkItemsList();
    
    try {
        const response = await fetch(`/api/work-items/${id}`);
        if (!response.ok) throw new Error('Failed to fetch item details.');
        const detail = await response.json();
        renderWorkItemDetails(detail);
    } catch (error) {
        console.error('Error fetching details:', error);
    }
}

// Render main pane details
function renderWorkItemDetails(item) {
    noSelectionState.classList.add('hidden');
    detailPanel.classList.remove('hidden');
    
    taskTitle.innerText = item.title || 'Ingested Work Request';
    
    // Priority badge
    taskPriority.className = `badge-priority badge-${item.priority.toLowerCase()}`;
    taskPriority.innerText = `Priority: ${item.priority}`;
    
    // Status badge
    taskStatus.className = `badge-status status-${item.status.toLowerCase()}`;
    taskStatus.innerText = item.status.replace('_', ' ');
    
    taskSummary.innerText = item.summary || '';
    taskDeadline.innerText = item.deadline || 'None Specified';
    
    const dateStr = new Date(item.created_at).toLocaleString();
    taskTimestamp.innerText = dateStr;
    
    // Warnings: Missing information
    warningsContainer.classList.add('hidden');
    missingInfoCard.classList.add('hidden');
    
    if (item.missing_information && item.missing_information.length > 0) {
        warningsContainer.classList.remove('hidden');
        missingInfoCard.classList.remove('hidden');
        missingInfoList.innerHTML = '';
        item.missing_information.forEach(info => {
            const li = document.createElement('li');
            li.innerText = info;
            missingInfoList.appendChild(li);
        });
    }
    
    // Render action items list
    renderActionItems(item.actions, item.id);
    
    // Render activity log
    renderActivityLogs(item.activities);
}

// Render action item cards
function renderActionItems(actions, itemId) {
    actionItemsList.innerHTML = '';
    
    if (actions.length === 0) {
        actionItemsList.innerHTML = '<div class="empty-state">No action items planned.</div>';
        return;
    }
    
    actions.forEach(action => {
        const card = document.createElement('div');
        
        // Determine route class
        let routeClass = '';
        if (action.action_type === 'EXECUTE_AUTOMATICALLY') routeClass = 'route-execute';
        else if (action.action_type === 'PREPARE_FOR_HUMAN_REVIEW') routeClass = 'route-review';
        else if (action.action_type === 'REQUIRES_CLARIFICATION') routeClass = 'route-clarify';
        else routeClass = 'route-cannot';
        
        card.className = `action-card ${routeClass}`;
        
        // Status dot class
        let dotClass = 'pending';
        if (action.status === 'AWAITING_CONFIRMATION') dotClass = 'awaiting';
        else if (action.status === 'COMPLETED') dotClass = 'completed';
        else if (action.status === 'FAILED') dotClass = 'failed';
        else if (action.status === 'BLOCKED') dotClass = 'blocked';
        
        let outputHtml = '';
        // If there is execution output, format and render it
        if (action.output) {
            let outputText = action.output;
            let displayBriefLink = false;
            let briefFilename = '';
            
            // Check if brief generator output
            if (action.tool_name === 'generate_markdown_brief') {
                try {
                    const parsed = JSON.parse(action.output);
                    if (parsed.status === 'SUCCESS' && parsed.filename) {
                        displayBriefLink = true;
                        briefFilename = parsed.filename;
                        outputText = parsed.content;
                    }
                } catch (e) {
                    // Not JSON, display text
                }
            } else if (action.tool_name === 'web_check' || action.tool_name === 'simulate_reminder' || action.tool_name === 'search_stored_work') {
                try {
                    // Try formatting JSON output for readability
                    const parsed = JSON.parse(action.output);
                    outputText = JSON.stringify(parsed, null, 2);
                } catch(e) {}
            }
            
            outputHtml = `
                <div class="action-output-box">${outputText}</div>
                ${displayBriefLink ? `
                    <div style="margin-top: 0.5rem;">
                        <a href="/briefs/${briefFilename}" target="_blank" class="brief-link">
                            📄 View Generated Brief File (${briefFilename})
                        </a>
                    </div>
                ` : ''}
            `;
        }
        
        // Action control buttons
        let controlsHtml = '';
        if (action.status === 'AWAITING_CONFIRMATION') {
            controlsHtml = `
                <div class="action-controls">
                    <button class="action-btn btn-edit" onclick="showEditModal(${action.id}, '${escapeQuote(action.description)}', \`${escapeQuote(action.output || '')}\`)">Edit & Approve</button>
                    <button class="action-btn btn-reject" onclick="handleActionStatus(${itemId}, ${action.id}, 'reject')">Reject</button>
                    <button class="action-btn btn-approve" onclick="handleActionStatus(${itemId}, ${action.id}, 'approve')">Approve</button>
                </div>
            `;
        } else if (action.status === 'PENDING' && action.action_type === 'EXECUTE_AUTOMATICALLY') {
            controlsHtml = `
                <div class="action-controls">
                    <button class="action-btn btn-execute" onclick="handleActionExecute(${itemId}, ${action.id})">Run Check</button>
                </div>
            `;
        }
        
        card.innerHTML = `
            <div class="action-card-header">
                <span class="action-description">${action.description}</span>
                <span class="action-route-badge">${action.action_type.replace(/_/g, ' ')}</span>
            </div>
            <div class="action-reason">Reason: ${action.reason || 'None provided'}</div>
            ${outputHtml}
            <div class="action-card-footer">
                <div class="action-status-indicator">
                    <span class="status-dot ${dotClass}"></span>
                    <span>Status: ${action.status.replace(/_/g, ' ')}</span>
                </div>
                ${controlsHtml}
            </div>
        `;
        
        actionItemsList.appendChild(card);
    });
}

// Render activity logs terminal window
function renderActivityLogs(logs) {
    activityLog.innerHTML = '';
    if (logs.length === 0) {
        activityLog.innerHTML = '<div style="color: var(--color-neutral);">No activity trace logs recorded.</div>';
        return;
    }
    
    logs.forEach(log => {
        const time = new Date(log.created_at).toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        let statusColor = '#94a3b8'; // Slate
        if (log.status === 'SUCCESS' || log.status === 'COMPLETED') statusColor = '#34d399'; // Emerald
        else if (log.status === 'FAILED' || log.status === 'BLOCKED') statusColor = '#f87171'; // Red
        
        entry.innerHTML = `
            <span class="log-time">[${time}]</span>
            <span class="log-event" style="color: ${statusColor}">${log.event}</span>
            <span class="log-details">${log.details}</span>
        `;
        activityLog.appendChild(entry);
    });
    
    // Auto scroll bottom
    activityLog.scrollTop = activityLog.scrollHeight;
}

// Action button trigger: Approve / Reject
async function handleActionStatus(itemId, actionId, decision) {
    try {
        const response = await fetch(`/api/work-items/${itemId}/actions/${actionId}/${decision}`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error(`Failed to perform ${decision} action.`);
        const updated = await response.json();
        renderWorkItemDetails(updated);
        fetchWorkItems(); // Refresh left pane statuses
    } catch (error) {
        alert(error.message);
    }
}

// Action button trigger: Execute automatable action manual
async function handleActionExecute(itemId, actionId) {
    try {
        const response = await fetch(`/api/work-items/${itemId}/actions/${actionId}/execute`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Failed to execute action.');
        const updated = await response.json();
        renderWorkItemDetails(updated);
        fetchWorkItems(); // Refresh list statuses
    } catch (error) {
        alert(error.message);
    }
}

// Edit Modal helpers
function showEditModal(actionId, description, output) {
    activeActionId = actionId;
    editDesc.value = description;
    editOutput.value = output;
    editModal.classList.add('active');
}

function hideEditModal() {
    editModal.classList.remove('active');
    activeActionId = null;
}

// Edit modal save submit
async function submitActionEdit() {
    if (!activeActionId || !activeWorkItemId) return;
    
    const desc = editDesc.value.trim();
    const outputText = editOutput.value.trim();
    
    if (!desc) {
        alert('Action description cannot be empty.');
        return;
    }
    
    try {
        const response = await fetch(`/api/work-items/${activeWorkItemId}/actions/${activeActionId}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: desc,
                output: outputText
            })
        });
        
        if (!response.ok) throw new Error('Failed to update action.');
        
        const updated = await response.json();
        renderWorkItemDetails(updated);
        fetchWorkItems(); // Refresh left list
        hideEditModal();
    } catch (error) {
        alert(error.message);
    }
}

// Helper to escape backticks and quotes in inline HTML templates
function escapeQuote(str) {
    if (!str) return '';
    return str
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '&quot;')
        .replace(/`/g, '\\`');
}
