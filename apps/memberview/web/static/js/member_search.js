// Member Search JavaScript

let currentFilters = {
    state: '',
    metro: '',
    status: ''
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadStates();
    setupEventListeners();
});

function setupEventListeners() {
    const stateFilter = document.getElementById('state-filter');
    const metroFilter = document.getElementById('metro-filter');
    const statusFilter = document.getElementById('status-filter');
    const searchBtn = document.getElementById('search-btn');
    const clearBtn = document.getElementById('clear-btn');
    const backToList = document.getElementById('back-to-list');
    
    if (stateFilter) stateFilter.addEventListener('change', onStateChange);
    if (metroFilter) metroFilter.addEventListener('change', onFilterChange);
    if (statusFilter) statusFilter.addEventListener('change', onFilterChange);
    if (searchBtn) searchBtn.addEventListener('click', performSearch);
    if (clearBtn) clearBtn.addEventListener('click', clearFilters);
    if (backToList) backToList.addEventListener('click', showMemberList);
}

function loadStates() {
    fetch('/search/api/states')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(states => {
            const select = document.getElementById('state-filter');
            if (!select) {
                console.error('State filter select element not found');
                return;
            }
            
            // Check if states is an error object
            if (states.error) {
                console.error('Error from API:', states.error);
                return;
            }
            
            // Check if states is an array
            if (!Array.isArray(states)) {
                console.error('States is not an array:', states);
                return;
            }
            
            if (states.length === 0) {
                console.warn('No states returned from API');
                return;
            }
            
            states.forEach(state => {
                const option = document.createElement('option');
                option.value = state;
                option.textContent = state;
                select.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading states:', error);
        });
}

function onStateChange() {
    const state = document.getElementById('state-filter').value;
    currentFilters.state = state;
    
    const metroSelect = document.getElementById('metro-filter');
    metroSelect.innerHTML = '<option value="">All Metro Areas</option>';
    
    if (state) {
        metroSelect.disabled = false;
        loadMetros(state);
    } else {
        metroSelect.disabled = true;
    }
    
    // Reset metro filter
    currentFilters.metro = '';
}

function loadMetros(state) {
    fetch(`/search/api/metros/${encodeURIComponent(state)}`)
        .then(response => response.json())
        .then(metros => {
            const select = document.getElementById('metro-filter');
            metros.forEach(metro => {
                const option = document.createElement('option');
                option.value = metro.code;
                option.textContent = metro.name;
                select.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading metros:', error);
        });
}

function onFilterChange() {
    currentFilters.metro = document.getElementById('metro-filter').value;
    currentFilters.status = document.getElementById('status-filter').value;
}

function performSearch() {
    console.log('Search button clicked');
    console.log('Current filters:', currentFilters);
    searchMembers();
}

function clearFilters() {
    const stateFilter = document.getElementById('state-filter');
    const metroFilter = document.getElementById('metro-filter');
    const statusFilter = document.getElementById('status-filter');
    const resultsCount = document.getElementById('results-count');
    
    if (stateFilter) stateFilter.value = '';
    if (metroFilter) {
        metroFilter.value = '';
        metroFilter.disabled = true;
    }
    if (statusFilter) statusFilter.value = '';
    
    currentFilters = {
        state: '',
        metro: '',
        status: ''
    };
    
    const memberList = document.getElementById('member-list');
    if (memberList) memberList.innerHTML = '<p class="empty-state">Select filters and click Search to find members.</p>';
    if (resultsCount) resultsCount.textContent = '0 members found';
    showMemberList();
}

function showMemberList() {
    const listView = document.getElementById('member-list-view');
    const detailView = document.getElementById('member-detail-view');
    if (listView) listView.style.display = 'block';
    if (detailView) detailView.style.display = 'none';
}

function searchMembers() {
    // Show list view first to ensure elements are visible
    showMemberList();
    
    // Wait a tiny bit to ensure DOM is updated
    setTimeout(() => {
        const loading = document.getElementById('loading');
        const memberList = document.getElementById('member-list');
        
        if (!loading) {
            console.error('Loading element not found. Available IDs:', 
                Array.from(document.querySelectorAll('[id]')).map(el => el.id).join(', '));
            return;
        }
        
        if (!memberList) {
            console.error('Member list element not found. Available IDs:', 
                Array.from(document.querySelectorAll('[id]')).map(el => el.id).join(', '));
            return;
        }
        
        loading.style.display = 'block';
        memberList.innerHTML = '';
        
        // Continue with the rest of the function
        performSearchInternal();
    }, 10);
}

function performSearchInternal() {
    const loading = document.getElementById('loading');
    const memberList = document.getElementById('member-list');
    
    if (!loading || !memberList) {
        console.error('Missing elements in performSearchInternal');
        return; // Already logged error in searchMembers
    }
    
    // Build query string (no pagination - get all results)
    const params = new URLSearchParams();
    if (currentFilters.state) params.append('state', currentFilters.state);
    if (currentFilters.metro) params.append('metro', currentFilters.metro);
    if (currentFilters.status) params.append('status', currentFilters.status);
    
    const url = `/search/api/members?${params.toString()}`;
    console.log('Fetching members from:', url);
    
    fetch(url)
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Received data:', { total: data.total, membersCount: data.members?.length });
            loading.style.display = 'none';
            
            if (data.error) {
                console.error('API error:', data.error);
                memberList.innerHTML = `<p class="empty-state" style="color: #d32f2f;">Error: ${data.error}</p>`;
                return;
            }
            
            // Update results count
            const resultsCount = document.getElementById('results-count');
            if (resultsCount) {
                const total = data.total || data.members.length;
                resultsCount.textContent = `${total} member${total !== 1 ? 's' : ''} found`;
            }
            
            // Display all members (no pagination)
            console.log('Displaying', data.members.length, 'members');
            displayMembers(data.members);
        })
        .catch(error => {
            loading.style.display = 'none';
            console.error('Error searching members:', error);
            memberList.innerHTML = `<p class="empty-state" style="color: #d32f2f;">Error loading members. Please try again.</p>`;
        });
}

function displayMembers(members) {
    // Use member-list as that's what's in the template
    const container = document.getElementById('member-list');
    if (!container) {
        console.error('Member list container not found. Available IDs:', 
            Array.from(document.querySelectorAll('[id]')).map(el => el.id).join(', '));
        return;
    }
    container.innerHTML = '';
    
    if (members.length === 0) {
        container.innerHTML = '<p class="empty-state">No members found matching your criteria.</p>';
        return;
    }
    
    members.forEach(member => {
        const listItem = document.createElement('div');
        listItem.className = 'member-list-item';
        listItem.dataset.memberId = member.id;
        
        const statusClass = member.status.toLowerCase().replace(/\s+/g, '-');
        
        listItem.innerHTML = `
            <div class="member-list-header">
                <div class="member-list-name">${escapeHtml(member.name)}</div>
                <div class="member-list-info">
                    <span class="member-status ${statusClass}">${escapeHtml(member.status || 'N/A')}</span>
                    <span class="member-location">${formatLocation(member)}</span>
                </div>
            </div>
            <button class="expand-button" data-member-id="${member.id}">
                <i class="fas fa-chevron-down"></i> Expand
            </button>
            <div class="member-detail-expanded" style="display: none;" data-member-id="${member.id}">
                <div class="expanded-loading">Loading details...</div>
            </div>
        `;
        
        // Add expand button handler
        const expandBtn = listItem.querySelector('.expand-button');
        expandBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleMemberExpand(member.id, listItem);
        });
        
        container.appendChild(listItem);
    });
}

function toggleMemberExpand(memberId, listItem) {
    const expandedDiv = listItem.querySelector('.member-detail-expanded');
    const expandBtn = listItem.querySelector('.expand-button');
    const icon = expandBtn.querySelector('i');
    
    if (expandedDiv.style.display === 'none') {
        // Expand
        expandedDiv.style.display = 'block';
        expandBtn.innerHTML = '<i class="fas fa-chevron-up"></i> Collapse';
        listItem.classList.add('expanded');
        
        // Load details if not already loaded
        if (!expandedDiv.dataset.loaded) {
            loadMemberDetailsInline(memberId, expandedDiv);
        }
    } else {
        // Collapse
        expandedDiv.style.display = 'none';
        expandBtn.innerHTML = '<i class="fas fa-chevron-down"></i> Expand';
        listItem.classList.remove('expanded');
    }
}

function loadMemberDetailsInline(memberId, container) {
    container.innerHTML = '<div class="expanded-loading">Loading details...</div>';
    
    fetch(`/search/api/member/${encodeURIComponent(memberId)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                container.innerHTML = `<p class="expanded-error">Error: ${data.error}</p>`;
                return;
            }
            
            displayMemberDetailsInline(data, container);
            container.dataset.loaded = 'true';
        })
        .catch(error => {
            console.error('Error loading member detail:', error);
            container.innerHTML = `<p class="expanded-error">Error loading member details. Please try again.</p>`;
        });
}

function displayMemberDetailsInline(member, container) {
    const statusClass = member.status.toLowerCase().replace(/\s+/g, '-');
    
    let html = `
        <div class="expanded-section">
            <h4><i class="fas fa-building"></i> Company Information</h4>
            <div class="expanded-info-grid">
                <div class="expanded-info-item">
                    <strong>Membership Status:</strong>
                    <span class="member-status ${statusClass}">${escapeHtml(member.status || 'N/A')}</span>
                </div>
                ${member.address ? `
                <div class="expanded-info-item">
                    <strong>Address:</strong>
                    <span>${escapeHtml(member.address)}</span>
                </div>
                ` : ''}
                ${member.city ? `
                <div class="expanded-info-item">
                    <strong>City:</strong>
                    <span>${escapeHtml(member.city)}</span>
                </div>
                ` : ''}
                ${member.state ? `
                <div class="expanded-info-item">
                    <strong>State:</strong>
                    <span>${escapeHtml(member.state)}</span>
                </div>
                ` : ''}
                ${member.county ? `
                <div class="expanded-info-item">
                    <strong>County:</strong>
                    <span>${escapeHtml(member.county)}</span>
                </div>
                ` : ''}
                ${member.metro ? `
                <div class="expanded-info-item">
                    <strong>Metro Area:</strong>
                    <span>${escapeHtml(member.metro.name || 'N/A')}</span>
                </div>
                ` : ''}
            </div>
        </div>
    `;
    
    // Add deals section
    if (member.deals && member.deals.length > 0) {
        html += `
            <div class="expanded-section">
                <h4><i class="fas fa-handshake"></i> Recent Deals (Last 5)</h4>
                <div class="expanded-deals-list">
        `;
        
        member.deals.forEach(deal => {
            const amount = deal.amount ? formatCurrency(deal.amount) : 'N/A';
            const date = deal.close_date ? formatDate(deal.close_date) : 'N/A';
            html += `
                <div class="expanded-deal-item">
                    <div class="expanded-deal-name">${escapeHtml(deal.name || 'Unnamed Deal')}</div>
                    <div class="expanded-deal-info">
                        <span class="expanded-deal-amount">${amount}</span>
                        <span class="expanded-deal-date">${date}</span>
                        ${deal.stage ? `<span class="expanded-deal-stage">${escapeHtml(deal.stage)}</span>` : ''}
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="expanded-section">
                <h4><i class="fas fa-handshake"></i> Recent Deals</h4>
                <p class="expanded-empty">No deals found for this member.</p>
            </div>
        `;
    }
    
    // Add contacts section
    if (member.contacts && member.contacts.length > 0) {
        html += `
            <div class="expanded-section">
                <h4><i class="fas fa-users"></i> Contacts (Up to 5)</h4>
                <div class="expanded-contacts-list">
        `;
        
        member.contacts.forEach(contact => {
            const fullName = [contact.first_name, contact.last_name].filter(Boolean).join(' ') || 'N/A';
            html += `
                <div class="expanded-contact-item">
                    <div class="expanded-contact-name">${escapeHtml(fullName)}</div>
                    <div class="expanded-contact-info">
                        ${contact.email ? `<div class="expanded-contact-email"><i class="fas fa-envelope"></i> ${escapeHtml(contact.email)}</div>` : ''}
                        ${contact.phone ? `<div class="expanded-contact-phone"><i class="fas fa-phone"></i> ${escapeHtml(contact.phone)}</div>` : ''}
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="expanded-section">
                <h4><i class="fas fa-users"></i> Contacts</h4>
                <p class="expanded-empty">No contacts found for this member.</p>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

function showMemberDetail(memberId) {
    // Hide list view, show detail view
    document.getElementById('member-list-view').style.display = 'none';
    document.getElementById('member-detail-view').style.display = 'block';
    
    const detailContent = document.getElementById('member-detail-content');
    const detailLoading = document.getElementById('detail-loading');
    
    detailLoading.style.display = 'block';
    detailContent.innerHTML = '';
    
    fetch(`/search/api/member/${encodeURIComponent(memberId)}`)
        .then(response => response.json())
        .then(data => {
            detailLoading.style.display = 'none';
            
            if (data.error) {
                detailContent.innerHTML = `<p class="empty-state" style="color: #d32f2f;">Error: ${data.error}</p>`;
                return;
            }
            
            displayMemberDetail(data);
        })
        .catch(error => {
            detailLoading.style.display = 'none';
            console.error('Error loading member detail:', error);
            detailContent.innerHTML = `<p class="empty-state" style="color: #d32f2f;">Error loading member details. Please try again.</p>`;
        });
}

function displayMemberDetail(member) {
    const detailContent = document.getElementById('member-detail-content');
    const detailName = document.getElementById('detail-member-name');
    
    detailName.textContent = member.name || 'Member';
    
    const statusClass = member.status.toLowerCase().replace(/\s+/g, '-');
    
    let html = `
        <div class="detail-section">
            <h3><i class="fas fa-building"></i> Company Information</h3>
            <div class="detail-info-grid">
                <div class="detail-info-item">
                    <strong>Membership Status:</strong>
                    <span class="member-status ${statusClass}">${escapeHtml(member.status || 'N/A')}</span>
                </div>
                ${member.address ? `
                <div class="detail-info-item">
                    <strong>Address:</strong>
                    <span>${escapeHtml(member.address)}</span>
                </div>
                ` : ''}
                ${member.city ? `
                <div class="detail-info-item">
                    <strong>City:</strong>
                    <span>${escapeHtml(member.city)}</span>
                </div>
                ` : ''}
                ${member.state ? `
                <div class="detail-info-item">
                    <strong>State:</strong>
                    <span>${escapeHtml(member.state)}</span>
                </div>
                ` : ''}
                ${member.county ? `
                <div class="detail-info-item">
                    <strong>County:</strong>
                    <span>${escapeHtml(member.county)}</span>
                </div>
                ` : ''}
                ${member.metro ? `
                <div class="detail-info-item">
                    <strong>Metro Area:</strong>
                    <span>${escapeHtml(member.metro.name || 'N/A')}</span>
                </div>
                ` : ''}
            </div>
        </div>
    `;
    
    // Add deals section
    if (member.deals && member.deals.length > 0) {
        html += `
            <div class="detail-section">
                <h3><i class="fas fa-handshake"></i> Recent Deals (Last 5)</h3>
                <div class="deals-list">
        `;
        
        member.deals.forEach(deal => {
            const amount = deal.amount ? formatCurrency(deal.amount) : 'N/A';
            const date = deal.close_date ? formatDate(deal.close_date) : 'N/A';
            html += `
                <div class="deal-item">
                    <div class="deal-name">${escapeHtml(deal.name || 'Unnamed Deal')}</div>
                    <div class="deal-info">
                        <span class="deal-amount">${amount}</span>
                        <span class="deal-date">${date}</span>
                        ${deal.stage ? `<span class="deal-stage">${escapeHtml(deal.stage)}</span>` : ''}
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="detail-section">
                <h3><i class="fas fa-handshake"></i> Recent Deals</h3>
                <p class="empty-state">No deals found for this member.</p>
            </div>
        `;
    }
    
    // Add contacts section
    if (member.contacts && member.contacts.length > 0) {
        html += `
            <div class="detail-section">
                <h3><i class="fas fa-users"></i> Contacts (Up to 5)</h3>
                <div class="contacts-list">
        `;
        
        member.contacts.forEach(contact => {
            const fullName = [contact.first_name, contact.last_name].filter(Boolean).join(' ') || 'N/A';
            html += `
                <div class="contact-item">
                    <div class="contact-name">${escapeHtml(fullName)}</div>
                    <div class="contact-info">
                        ${contact.email ? `<div class="contact-email"><i class="fas fa-envelope"></i> ${escapeHtml(contact.email)}</div>` : ''}
                        ${contact.phone ? `<div class="contact-phone"><i class="fas fa-phone"></i> ${escapeHtml(contact.phone)}</div>` : ''}
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="detail-section">
                <h3><i class="fas fa-users"></i> Contacts</h3>
                <p class="empty-state">No contacts found for this member.</p>
            </div>
        `;
    }
    
    detailContent.innerHTML = html;
}

function formatCurrency(amount) {
    if (!amount || amount === 0) return '$0';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

function formatDate(dateString) {
    if (!dateString || dateString === 'N/A') return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) {
        return dateString;
    }
}

function formatLocation(member) {
    const parts = [];
    if (member.city) parts.push(member.city);
    if (member.state) parts.push(member.state);
    if (member.county) parts.push(`(${member.county})`);
    return parts.length > 0 ? escapeHtml(parts.join(', ')) : 'N/A';
}


function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

