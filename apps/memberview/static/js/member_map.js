/**
 * Member Map JavaScript
 * Handles map rendering, filtering, and popup display for NCRC members.
 */

// Initialize map
let memberMap;
let memberMarkers = [];
let allMembers = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    loadStates();
    setupFilters();
    loadMembers();
});

/**
 * Initialize Leaflet map
 */
function initializeMap() {
    // Center on USA
    memberMap = L.map('memberMap').setView([39.8283, -98.5795], 4);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(memberMap);
}

/**
 * Load list of states for filter dropdown
 */
async function loadStates() {
    try {
        const response = await fetch('/api/map/states');
        const states = await response.json();
        
        const stateSelect = document.getElementById('stateFilter');
        states.forEach(state => {
            const option = document.createElement('option');
            option.value = state;
            option.textContent = state;
            stateSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading states:', error);
    }
}

/**
 * Setup filter event listeners
 */
function setupFilters() {
    const stateFilter = document.getElementById('stateFilter');
    const statusFilter = document.getElementById('statusFilter');
    
    stateFilter.addEventListener('change', applyFilters);
    statusFilter.addEventListener('change', applyFilters);
}

/**
 * Apply filters and update map
 */
function applyFilters() {
    const state = document.getElementById('stateFilter').value;
    const status = document.getElementById('statusFilter').value;
    
    // Zoom to selected state
    if (state) {
        zoomToState(state);
    }
    
    loadMembers(state, status);
}

/**
 * Zoom map to selected state
 */
function zoomToState(stateName) {
    // State center coordinates (will be fetched from API or use defaults)
    const stateCenters = {
        'Alabama': {lat: 32.806671, lng: -86.791130, zoom: 7},
        'Alaska': {lat: 61.370716, lng: -152.404419, zoom: 4},
        'Arizona': {lat: 33.729759, lng: -111.431221, zoom: 6},
        'Arkansas': {lat: 34.969704, lng: -92.373123, zoom: 7},
        'California': {lat: 36.116203, lng: -119.681564, zoom: 6},
        'Colorado': {lat: 39.059811, lng: -105.311104, zoom: 6},
        'Connecticut': {lat: 41.597782, lng: -72.755371, zoom: 8},
        'Delaware': {lat: 39.318523, lng: -75.507141, zoom: 8},
        'District of Columbia': {lat: 38.9072, lng: -77.0369, zoom: 11},
        'Florida': {lat: 27.766279, lng: -81.686783, zoom: 6},
        'Georgia': {lat: 33.040619, lng: -83.643074, zoom: 7},
        'Hawaii': {lat: 21.094318, lng: -157.498337, zoom: 7},
        'Idaho': {lat: 44.240459, lng: -114.478828, zoom: 6},
        'Illinois': {lat: 40.349457, lng: -88.986137, zoom: 7},
        'Indiana': {lat: 39.849426, lng: -86.258278, zoom: 7},
        'Iowa': {lat: 42.011539, lng: -93.210526, zoom: 7},
        'Kansas': {lat: 38.526600, lng: -96.726486, zoom: 7},
        'Kentucky': {lat: 37.668140, lng: -84.670067, zoom: 7},
        'Louisiana': {lat: 31.169546, lng: -91.867805, zoom: 7},
        'Maine': {lat: 44.323535, lng: -69.765261, zoom: 7},
        'Maryland': {lat: 39.063946, lng: -76.802101, zoom: 8},
        'Massachusetts': {lat: 42.230171, lng: -71.530106, zoom: 8},
        'Michigan': {lat: 43.326618, lng: -84.536095, zoom: 6},
        'Minnesota': {lat: 45.694454, lng: -93.900192, zoom: 6},
        'Mississippi': {lat: 32.741646, lng: -89.678696, zoom: 7},
        'Missouri': {lat: 38.456085, lng: -92.288368, zoom: 7},
        'Montana': {lat: 46.921925, lng: -110.454353, zoom: 6},
        'Nebraska': {lat: 41.125370, lng: -98.268082, zoom: 7},
        'Nevada': {lat: 38.313515, lng: -117.055374, zoom: 6},
        'New Hampshire': {lat: 43.452492, lng: -71.563896, zoom: 8},
        'New Jersey': {lat: 40.298904, lng: -74.521011, zoom: 8},
        'New Mexico': {lat: 34.840515, lng: -106.248482, zoom: 6},
        'New York': {lat: 42.165726, lng: -74.948051, zoom: 7},
        'North Carolina': {lat: 35.630066, lng: -79.806419, zoom: 7},
        'North Dakota': {lat: 47.528912, lng: -99.784012, zoom: 7},
        'Ohio': {lat: 40.388783, lng: -82.764915, zoom: 7},
        'Oklahoma': {lat: 35.565342, lng: -96.928917, zoom: 7},
        'Oregon': {lat: 44.572021, lng: -122.070938, zoom: 6},
        'Pennsylvania': {lat: 40.590752, lng: -77.209755, zoom: 7},
        'Rhode Island': {lat: 41.680893, lng: -71.51178, zoom: 9},
        'South Carolina': {lat: 33.856892, lng: -80.945007, zoom: 7},
        'South Dakota': {lat: 44.299782, lng: -99.438828, zoom: 7},
        'Tennessee': {lat: 35.747845, lng: -86.692345, zoom: 7},
        'Texas': {lat: 31.054487, lng: -97.563461, zoom: 6},
        'Utah': {lat: 40.150032, lng: -111.862434, zoom: 6},
        'Vermont': {lat: 44.045876, lng: -72.710686, zoom: 8},
        'Virginia': {lat: 37.769337, lng: -78.169968, zoom: 7},
        'Washington': {lat: 47.400902, lng: -121.490494, zoom: 6},
        'West Virginia': {lat: 38.491226, lng: -80.954453, zoom: 7},
        'Wisconsin': {lat: 44.268543, lng: -89.616508, zoom: 7},
        'Wyoming': {lat: 42.755966, lng: -107.302490, zoom: 6},
    };
    
    const center = stateCenters[stateName];
    if (center) {
        memberMap.setView([center.lat, center.lng], center.zoom);
    }
}

/**
 * Load members from API
 */
async function loadMembers(state = '', status = '') {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const memberCount = document.getElementById('memberCount');
    const memberCountNumber = document.getElementById('memberCountNumber');
    
    loadingIndicator.style.display = 'block';
    memberCount.style.display = 'none';
    
    try {
        // Build query string
        const params = new URLSearchParams();
        if (state) params.append('state', state);
        if (status) params.append('status', status);
        
        const response = await fetch(`/api/map/members?${params.toString()}`);
        const members = await response.json();
        
        allMembers = members;
        
        // Clear existing markers
        clearMarkers();
        
        // Add markers for each member
        let membersWithCoords = 0;
        members.forEach(member => {
            if (member.location && (member.location.lat || member.location.lng)) {
                addMemberMarker(member);
                membersWithCoords++;
            } else {
                console.debug(`Skipping member ${member.name} - no coordinates`);
            }
        });
        
        // Update count
        memberCountNumber.textContent = `${membersWithCoords} of ${members.length} members`;
        loadingIndicator.style.display = 'none';
        memberCount.style.display = 'block';
        
        // Fit map to bounds if we have markers
        if (memberMarkers.length > 0) {
            const group = new L.featureGroup(memberMarkers);
            memberMap.fitBounds(group.getBounds().pad(0.1));
        } else {
            console.warn('No members with coordinates. Run geocoding script: python scripts/geocode_members.py');
        }
        
    } catch (error) {
        console.error('Error loading members:', error);
        loadingIndicator.textContent = 'Error loading members';
    }
}

/**
 * Add a marker for a member
 */
function addMemberMarker(member) {
    // Get coordinates (if available, otherwise geocode)
    let lat = member.location?.lat;
    let lng = member.location?.lng;
    
    // Convert to numbers if they're strings
    if (lat) lat = parseFloat(lat);
    if (lng) lng = parseFloat(lng);
    
    // If no coordinates, skip this member (geocoding should happen server-side)
    if (!lat || !lng || isNaN(lat) || isNaN(lng)) {
        console.debug(`Skipping member ${member.name} - no coordinates (${member.location?.city}, ${member.location?.state})`);
        return;
    }
    
    // Choose marker color based on status
    let markerColor = '#3388ff'; // Default blue
    if (member.status) {
        const statusUpper = member.status.toUpperCase();
        if (statusUpper.includes('CURRENT') || statusUpper.includes('ACTIVE')) {
            markerColor = '#28a745'; // Green
        } else if (statusUpper.includes('GRACE')) {
            markerColor = '#ffc107'; // Yellow
        } else if (statusUpper.includes('LAPSED')) {
            markerColor = '#dc3545'; // Red
        }
    }
    
    // Create custom icon
    const icon = L.divIcon({
        className: 'member-marker',
        html: `<div style="background-color: ${markerColor}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6]
    });
    
    // Create marker
    const marker = L.marker([lat, lng], { icon: icon });
    
    // Create popup content
    const popupContent = createPopupContent(member);
    marker.bindPopup(popupContent, { maxWidth: 400 });
    
    // Add to map
    marker.addTo(memberMap);
    memberMarkers.push(marker);
}

/**
 * Create popup content for a member
 */
function createPopupContent(member) {
    const statusClass = getStatusClass(member.status);
    const statusText = member.status || 'Unknown';
    
    let html = `
        <div class="member-popup">
            <h3>${escapeHtml(member.name || 'Unknown Company')}</h3>
            <span class="status-badge ${statusClass}">${escapeHtml(statusText)}</span>
            
            <div class="info-section">
                <h4>Location</h4>
                <div class="info-item">
                    ${escapeHtml(member.location?.city || 'N/A')}, ${escapeHtml(member.location?.state || 'N/A')}
                </div>
            </div>
    `;
    
    // Add last deal if available
    if (member.last_deal) {
        const amount = member.last_deal.amount ? formatCurrency(member.last_deal.amount) : 'N/A';
        const date = member.last_deal.close_date || 'N/A';
        
        html += `
            <div class="info-section">
                <h4>Last Deal</h4>
                <div class="deal-info">
                    <div class="info-item"><strong>${escapeHtml(member.last_deal.name || 'N/A')}</strong></div>
                    <div class="info-item deal-amount">${amount}</div>
                    <div class="info-item" style="font-size: 0.85rem; color: #666;">Closed: ${escapeHtml(date)}</div>
                </div>
            </div>
        `;
    }
    
    // Add summary stats
    html += `
            <div class="info-section">
                <h4>Summary</h4>
                <div class="info-item">Contacts: <strong>${member.contacts_count || 0}</strong></div>
                <div class="info-item">Deals: <strong>${member.deals_count || 0}</strong></div>
                ${member.total_deal_amount ? `<div class="info-item">Total Deal Amount: <strong>${formatCurrency(member.total_deal_amount)}</strong></div>` : ''}
            </div>
    `;
    
    // Form 990 data lookup disabled - too cumbersome with EIN matching
    // if (member.form_990 && member.form_990.found && member.form_990.financials) {
    //     const financials = member.form_990.financials;
    //     const org = member.form_990.organization || {};
    //     const taxYear = financials.tax_year || financials.tax_period || 'N/A';
    //     
    //     html += `
    //         <div class="info-section">
    //             <h4>IRS Form 990 (${escapeHtml(taxYear)})</h4>
    //             <div class="deal-info" style="background: #e8f4f8;">
    //                 ${org.ein ? `<div class="info-item" style="font-size: 0.85rem; color: #666; margin-bottom: 8px;"><strong>EIN:</strong> ${escapeHtml(org.ein)}</div>` : ''}
    //                 ${financials.total_revenue ? `<div class="info-item" style="margin: 5px 0;"><strong>Revenue:</strong> ${formatCurrency(financials.total_revenue)}</div>` : ''}
    //                 ${financials.total_expenses ? `<div class="info-item" style="margin: 5px 0;"><strong>Expenses:</strong> ${formatCurrency(financials.total_expenses)}</div>` : ''}
    //             </div>
    //     `;
    //     
    //     // Add officers if available
    //     if (financials.officers && financials.officers.length > 0) {
    //         html += `
    //             <div style="margin-top: 10px;">
    //                 <div style="font-size: 0.85rem; color: #666; margin-bottom: 5px;"><strong>Key Officers:</strong></div>
    //         `;
    //         
    //         financials.officers.slice(0, 5).forEach(officer => {
    //             const name = escapeHtml(officer.name || '');
    //             const title = escapeHtml(officer.title || '');
    //             if (name) {
    //                 html += `<div style="font-size: 0.85rem; margin: 3px 0;">${name}${title ? ` - ${title}` : ''}</div>`;
    //             }
    //         });
    //         
    //         html += `</div>`;
    //     }
    //     
    //     html += `</div>`;
    // }
    
    // Add link to view full details
    html += `
            <div class="info-section" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee;">
                <a href="/member/${member.id}" style="color: #003366; text-decoration: none; font-weight: 600;">
                    View Full Details →
                </a>
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Get CSS class for member status
 */
function getStatusClass(status) {
    if (!status) return '';
    
    const statusUpper = status.toUpperCase();
    if (statusUpper.includes('CURRENT') || statusUpper.includes('ACTIVE')) {
        return 'current';
    } else if (statusUpper.includes('GRACE')) {
        return 'grace';
    } else if (statusUpper.includes('LAPSED')) {
        return 'lapsed';
    }
    return '';
}

/**
 * Clear all markers from map
 */
function clearMarkers() {
    memberMarkers.forEach(marker => {
        memberMap.removeLayer(marker);
    });
    memberMarkers = [];
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    if (typeof amount !== 'number') return 'N/A';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

