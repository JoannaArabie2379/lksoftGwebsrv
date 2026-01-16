/**
 * ИГС Portal - Main JavaScript
 */

// ============================================
// Theme Management
// ============================================

function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'grey' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.textContent = newTheme === 'dark' ? '🌙' : '☀️';
    }
}

// Load saved theme on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.textContent = savedTheme === 'dark' ? '🌙' : '☀️';
    }
});

// ============================================
// Modal Management
// ============================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// Close modal on background click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
        document.body.style.overflow = '';
    }
});

// Close modal on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            modal.classList.remove('show');
        });
        document.body.style.overflow = '';
    }
});

// ============================================
// Notifications
// ============================================

function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelectorAll('.notification');
    existing.forEach(n => n.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// ============================================
// API Helpers
// ============================================

async function apiGet(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API GET error:', error);
        showNotification('Ошибка загрузки данных', 'error');
        throw error;
    }
}

async function apiPost(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API POST error:', error);
        showNotification(error.message || 'Ошибка отправки данных', 'error');
        throw error;
    }
}

async function apiPut(url, data) {
    try {
        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API PUT error:', error);
        showNotification(error.message || 'Ошибка обновления данных', 'error');
        throw error;
    }
}

async function apiDelete(url) {
    try {
        const response = await fetch(url, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API DELETE error:', error);
        showNotification(error.message || 'Ошибка удаления', 'error');
        throw error;
    }
}

// ============================================
// Form Helpers
// ============================================

function getFormData(formElement) {
    const formData = new FormData(formElement);
    const data = {};
    
    formData.forEach((value, key) => {
        if (value !== '' && value !== null) {
            // Try to convert to number if applicable
            if (!isNaN(value) && value !== '') {
                data[key] = Number(value);
            } else {
                data[key] = value;
            }
        }
    });
    
    return data;
}

function resetForm(formElement) {
    formElement.reset();
    
    // Clear any custom states
    const inputs = formElement.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.classList.remove('error', 'success');
    });
}

// ============================================
// CSV Import Preview
// ============================================

function previewCSV(input) {
    const file = input.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const text = e.target.result;
        const lines = text.split('\n');
        const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
        
        // Show preview
        const preview = document.getElementById('csv-preview');
        const mapping = document.getElementById('csv-mapping');
        
        if (preview && mapping) {
            preview.classList.remove('hidden');
            
            // DB field options
            const dbFields = [
                { value: '', label: '-- Пропустить --' },
                { value: 'number', label: 'Номер' },
                { value: 'lat', label: 'Широта (lat)' },
                { value: 'lon', label: 'Долгота (lon)' },
                { value: 'description', label: 'Описание' },
                { value: 'owner_id', label: 'ID собственника' },
                { value: 'state_id', label: 'ID состояния' }
            ];
            
            // Generate mapping fields
            mapping.innerHTML = headers.map((header, idx) => `
                <div class="form-row" style="margin-bottom: 8px;">
                    <div class="form-group" style="flex: 1;">
                        <label style="font-weight: bold;">${header}</label>
                    </div>
                    <div class="form-group" style="flex: 1;">
                        <select name="mapping_${header}" class="csv-mapping-select" data-csv-col="${header}">
                            ${dbFields.map(f => `<option value="${f.value}">${f.label}</option>`).join('')}
                        </select>
                    </div>
                </div>
            `).join('');
            
            // Show sample data
            if (lines.length > 1) {
                const sampleLine = lines[1].split(',').map(v => v.trim().replace(/"/g, ''));
                mapping.innerHTML += `
                    <div class="mt-2" style="padding: 12px; background: var(--bg-tertiary); border-radius: 6px;">
                        <strong>Пример данных:</strong><br>
                        ${headers.map((h, i) => `${h}: ${sampleLine[i] || '-'}`).join('<br>')}
                    </div>
                `;
            }
        }
    };
    reader.readAsText(file);
}

async function submitCSVImport(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    // Build mapping object
    const mapping = {};
    document.querySelectorAll('.csv-mapping-select').forEach(select => {
        if (select.value) {
            mapping[select.dataset.csvCol] = select.value;
        }
    });
    
    formData.append('mapping', JSON.stringify(mapping));
    
    try {
        const response = await fetch('/api/import/csv', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification(`Импортировано: ${result.imported} из ${result.total}`, 'success');
            closeModal('import-modal');
            
            // Reload data
            if (typeof loadObjects === 'function') {
                loadObjects();
            }
            if (typeof loadStats === 'function') {
                loadStats();
            }
        } else {
            showNotification(result.error || 'Ошибка импорта', 'error');
        }
    } catch (e) {
        showNotification('Ошибка сети', 'error');
    }
}

async function submitTABImport(event) {
    event.preventDefault();
    
    showNotification('Импорт TAB/MAP/DAT файлов будет доступен в следующей версии', 'info');
}

// ============================================
// Admin Functions
// ============================================

function showAddUserModal() {
    const html = `
        <div class="modal show" id="add-user-modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Добавить пользователя</h3>
                    <button class="modal-close" onclick="closeModal('add-user-modal')">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="add-user-form" onsubmit="submitNewUser(event)">
                        <div class="form-group">
                            <label>Логин *</label>
                            <input type="text" name="username" required>
                        </div>
                        <div class="form-group">
                            <label>Пароль *</label>
                            <input type="password" name="password" required>
                        </div>
                        <div class="form-group">
                            <label>ФИО</label>
                            <input type="text" name="full_name">
                        </div>
                        <div class="form-group">
                            <label>Email</label>
                            <input type="email" name="email">
                        </div>
                        <div class="form-group">
                            <label>Роль</label>
                            <select name="role_id">
                                <option value="1">Пользователь</option>
                                <option value="2">Администратор</option>
                                <option value="3">Визор</option>
                            </select>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" onclick="closeModal('add-user-modal')">Отмена</button>
                            <button type="submit" class="btn btn-primary">Создать</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
}

async function submitNewUser(event) {
    event.preventDefault();
    
    const form = event.target;
    const data = getFormData(form);
    
    try {
        await apiPost('/api/users', data);
        showNotification('Пользователь создан', 'success');
        closeModal('add-user-modal');
        document.getElementById('add-user-modal').remove();
        
        if (typeof loadAdminData === 'function') {
            loadAdminData();
        }
    } catch (e) {
        // Error already shown by apiPost
    }
}

function showAddOwnerModal() {
    const html = `
        <div class="modal show" id="add-owner-modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Добавить собственника</h3>
                    <button class="modal-close" onclick="closeModal('add-owner-modal')">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="add-owner-form" onsubmit="submitNewOwner(event)">
                        <div class="form-group">
                            <label>Наименование организации *</label>
                            <input type="text" name="organization_name" required>
                        </div>
                        <div class="form-group">
                            <label>Контактное лицо</label>
                            <input type="text" name="contact_person">
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Телефон</label>
                                <input type="text" name="phone">
                            </div>
                            <div class="form-group">
                                <label>Email</label>
                                <input type="email" name="email">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Адрес</label>
                            <textarea name="address" rows="2"></textarea>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" onclick="closeModal('add-owner-modal')">Отмена</button>
                            <button type="submit" class="btn btn-primary">Создать</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
}

async function submitNewOwner(event) {
    event.preventDefault();
    
    const form = event.target;
    const data = getFormData(form);
    
    try {
        await apiPost('/api/owners', data);
        showNotification('Собственник добавлен', 'success');
        closeModal('add-owner-modal');
        document.getElementById('add-owner-modal').remove();
        
        if (typeof loadAdminData === 'function') {
            loadAdminData();
        }
        if (typeof loadReferences === 'function') {
            loadReferences();
        }
    } catch (e) {
        // Error already shown
    }
}

function showAddContractModal() {
    // First load owners for dropdown
    fetch('/api/owners')
        .then(r => r.json())
        .then(owners => {
            const ownerOptions = owners.map(o => 
                `<option value="${o.id}">${o.organization_name}</option>`
            ).join('');
            
            const html = `
                <div class="modal show" id="add-contract-modal">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3>Добавить контракт</h3>
                            <button class="modal-close" onclick="closeModal('add-contract-modal')">&times;</button>
                        </div>
                        <div class="modal-body">
                            <form id="add-contract-form" onsubmit="submitNewContract(event)">
                                <div class="form-row">
                                    <div class="form-group">
                                        <label>Номер контракта *</label>
                                        <input type="text" name="contract_number" required>
                                    </div>
                                    <div class="form-group">
                                        <label>Дата контракта *</label>
                                        <input type="date" name="contract_date" required>
                                    </div>
                                </div>
                                <div class="form-group">
                                    <label>Собственник</label>
                                    <select name="owner_id">
                                        <option value="">-- Не выбран --</option>
                                        ${ownerOptions}
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>Описание</label>
                                    <textarea name="description" rows="2"></textarea>
                                </div>
                                <div class="form-actions">
                                    <button type="button" class="btn btn-secondary" onclick="closeModal('add-contract-modal')">Отмена</button>
                                    <button type="submit" class="btn btn-primary">Создать</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', html);
        });
}

async function submitNewContract(event) {
    event.preventDefault();
    
    const form = event.target;
    const data = getFormData(form);
    
    try {
        await apiPost('/api/contracts', data);
        showNotification('Контракт добавлен', 'success');
        closeModal('add-contract-modal');
        document.getElementById('add-contract-modal').remove();
        
        if (typeof loadAdminData === 'function') {
            loadAdminData();
        }
    } catch (e) {
        // Error already shown
    }
}

function editUser(userId) {
    showNotification('Редактирование пользователя будет доступно в следующей версии', 'info');
}

// ============================================
// Utility Functions
// ============================================

function formatDate(dateString) {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('ru-RU');
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('ru-RU');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================
// Confirm Dialog
// ============================================

function confirmAction(message, onConfirm) {
    const html = `
        <div class="modal show" id="confirm-modal">
            <div class="modal-content" style="max-width: 400px;">
                <div class="modal-header">
                    <h3>Подтверждение</h3>
                    <button class="modal-close" onclick="closeModal('confirm-modal'); document.getElementById('confirm-modal').remove();">&times;</button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" onclick="closeModal('confirm-modal'); document.getElementById('confirm-modal').remove();">Отмена</button>
                        <button type="button" class="btn btn-danger" id="confirm-btn">Подтвердить</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
    
    document.getElementById('confirm-btn').onclick = function() {
        closeModal('confirm-modal');
        document.getElementById('confirm-modal').remove();
        onConfirm();
    };
}
