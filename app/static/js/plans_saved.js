let allPlans = [];

// 1. Initialize
(async () => {
  await loadPlans();
  
  // Add event listeners for live filtering
  document.getElementById('filter-search').addEventListener('input', applyFilters);
  document.getElementById('filter-date').addEventListener('change', applyFilters);
  document.getElementById('filter-status').addEventListener('change', applyFilters);
})();

// 2. Fetch all plans
async function loadPlans() {
  try {
    // We use the existing GET /plans endpoint from your backend
    allPlans = await apiJson('/plans/list');
    applyFilters();
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

// 3. Filter and Render Table
function applyFilters() {
  const searchVal = document.getElementById('filter-search').value.trim();
  const dateVal = document.getElementById('filter-date').value;
  const statusVal = document.getElementById('filter-status').value;

  const filtered = allPlans.filter(p => {
    // Plan ID filter
    if (searchVal && !p.plan_id.toString().includes(searchVal)) return false;
    
    // Date filter
    if (dateVal && p.delivery_date !== dateVal) return false;
    
    // Status filter
    if (statusVal && p.status !== statusVal) return false;
    
    return true;
  });

  renderTable(filtered);
}

function clearFilters() {
  document.getElementById('filter-search').value = '';
  document.getElementById('filter-date').value = '';
  document.getElementById('filter-status').value = '';
  applyFilters();
}

// 4. Render Table Rows
function renderTable(plans) {
  const tbody = document.getElementById('plans-body');
  
  if (plans.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="muted" style="text-align: center; padding: 24px;">No plans match your filters.</td></tr>';
    return;
  }

  tbody.innerHTML = plans.map(p => {
    // Status styles
    let badgeClass = 'badge';
    let badgeStyle = '';
    if (p.status === 'approved') badgeStyle = 'background: var(--surface-2); color: var(--navy);';
    if (p.status === 'in_progress') badgeStyle = 'background: var(--amber-soft); color: var(--amber);';
    if (p.status === 'delivered') badgeStyle = 'background: var(--ok-soft); color: var(--ok);';

    const truckPlate = p.truck ? p.truck.license_plate : `ID ${p.truck_id}`;
    
    return `
      <tr id="plan-row-${p.plan_id}">
        <td>
          <button class="btn small" onclick="toggleDetails(${p.plan_id})" style="padding: 0 8px;">▼</button>
        </td>
        <td style="font-weight: 600;">#${p.plan_id}</td>
        <td>${p.delivery_date}</td>
        <td><span class="tag">${truckPlate}</span></td>
        <td class="r">${p.stops ? p.stops.length : 0}</td>
        <td class="r">${(p.total_distance / 1000).toFixed(1)} km</td>
        <td>
          <select onchange="updateStatus(${p.plan_id}, this.value)" 
                  class="badge" 
                  style="${badgeStyle} border: none; font-weight: 600; cursor: pointer; padding: 4px 8px;">
            <option value="approved" ${p.status === 'approved' ? 'selected' : ''}>Approved</option>
            <option value="in_progress" ${p.status === 'in_progress' ? 'selected' : ''}>In Transit</option>
            <option value="delivered" ${p.status === 'delivered' ? 'selected' : ''}>Delivered</option>
          </select>
        </td>
        <td class="r">
          <a href="/plans/${p.plan_id}/export" class="btn small" style="text-decoration: none;">Download CSV</a>
        </td>
      </tr>
      
      <!-- Hidden Details Row -->
      <tr id="details-row-${p.plan_id}" style="display: none; background: var(--surface-2);">
        <td colspan="8" style="padding: 20px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            
            <!-- Delivery Sequence -->
            <div>
              <h4 style="margin-bottom: 12px;">Delivery Sequence</h4>
              <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.9rem;">
                ${(p.stops || []).map(s => `
                  <li style="margin-bottom: 8px; border-bottom: 1px solid var(--line); padding-bottom: 8px;">
                    <strong>Stop ${s.stop_sequence}:</strong> ${s.customer_id} 
                    <span class="muted">(${s.items.length} items)</span>
                  </li>
                `).join('')}
              </ul>
            </div>

            <!-- Loading Plan -->
            <div>
              <h4 style="margin-bottom: 12px;">Loading Plan (LIFO)</h4>
              <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.9rem;">
                ${(p.stops || []).slice().reverse().map((s, i) => `
                  <li style="margin-bottom: 8px; border-bottom: 1px solid var(--line); padding-bottom: 8px;">
                    <strong>Load ${i + 1}:</strong> Stop ${s.stop_sequence} goods
                  </li>
                `).join('')}
              </ul>
            </div>

          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// 5. Toggle Details Expansion
function toggleDetails(planId) {
  const row = document.getElementById(`details-row-${planId}`);
  if (row.style.display === 'none') {
    row.style.display = 'table-row';
  } else {
    row.style.display = 'none';
  }
}

// 6. Update Status Inline
async function updateStatus(planId, newStatus) {
  try {
    await apiJson(`/plans/${planId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus })
    });
    toast('Status updated', 'ok');
    
    // Update local data without reloading the whole page
    const plan = allPlans.find(p => p.plan_id === planId);
    if (plan) plan.status = newStatus;
    
    // Re-render to update the badge color
    applyFilters();
  } catch (ex) {
    toast(ex.message, 'error');
    // Revert selection if it failed
    applyFilters();
  }
}