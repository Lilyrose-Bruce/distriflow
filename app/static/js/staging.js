let currentTruckCapacity = 0;
let stagingRows = [];
let allCustomers = [];

// 1. Initialize
(async () => {
  try {
    allCustomers = await apiJson('/customers');
    
    // Populate Add Row dropdown
    const sel = document.getElementById('add-customer');
    allCustomers.forEach(c => {
      const o = document.createElement('option');
      o.value = c.customer_id;
      o.textContent = c.customer_name;
      o.dataset.name = c.customer_name; 
      sel.appendChild(o);
    });

    // Populate Edit Modal dropdown
    const editSel = document.getElementById('edit-customer');
    allCustomers.forEach(c => {
      const o = document.createElement('option');
      o.value = c.customer_id;
      o.textContent = c.customer_name;
      o.dataset.name = c.customer_name; 
      editSel.appendChild(o);
    });

  } catch (ex) { toast('Failed to load customers', 'error'); }

  await fetchStagingState();
})();

// 2. Fetch and Render Staging State
async function fetchStagingState() {
  try {
    const data = await apiJson('/staging/read'); 
    
    stagingRows = data.rows || [];
    currentTruckCapacity = data.truck ? data.truck.max_weight_capacity : 0;
    
    document.getElementById('truck-title').textContent = 
      `Truck: ${data.truck ? data.truck.license_plate : 'None'}`;
    document.getElementById('truck-capacity').textContent = 
      `Maximum capacity: ${currentTruckCapacity.toLocaleString()} kg`;
    
    renderTable(data);
    updateCapacityAndErrors(data);
    
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

// 3. Render Table Rows
function renderTable(data) {
  const tbody = document.querySelector('#staging-table tbody');
  
  if (!stagingRows.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="muted" style="text-align: center; padding: 24px;">No orders staged yet.</td></tr>';
    return;
  }

  tbody.innerHTML = stagingRows.map((r, i) => {
    const hasErrors = r.status === "error" || (r.errors && r.errors.length > 0);
    const errorString = hasErrors ? r.errors.join('<br>') : '';
    
    // Format Status Cell based on screenshot
    let statusCell = '<span class="status-ok">OK</span>';
    let totalWt = (r.total_weight || 0).toLocaleString();
    
    if (hasErrors) {
      statusCell = `
        <span class="status-bad" style="font-size: 0.85rem; line-height: 1.2; display: block;">
          ⚠ ${errorString}
        </span>`;
      totalWt = '–'; // Show dash instead of 0 if invalid
    }

    const actualRowId = r.row_id || (i + 1);

    return `
      <tr class="${hasErrors ? 'err' : ''}">
        <td class="muted">${i + 1}</td>
        <td style="font-weight: 500;">${r.customer_name || 'Unknown'}</td>
        <td class="muted">${r.product || ''}</td>
        <td class="r num">${r.quantity || 0}</td>
        <td class="r num">${r.unit_weight || 0}</td>
        <td class="r num">${totalWt}</td>
        <td>${statusCell}</td>
        <td class="r">
          <button class="btn link small" onclick="openEditModal(${r.row_id})">
            ${hasErrors ? 'Fix' : 'Edit'}
          </button>
          <button class="btn link small danger" onclick="deleteRow(${r.row_id})">Delete</button>
        </td>
      </tr>
    `;
  }).join('');
}

// 4. Capacity Bar & Global Errors Logic
function updateCapacityAndErrors(data) {
  const stagedWeight = data.total_weight || 0;
  const spaceLeft = data.space_left || 0;
  const pct = data.percent_used || 0;
  
  document.getElementById('staged-weight-label').textContent = 
    `Staged weight: ${stagedWeight.toLocaleString()} kg of ${currentTruckCapacity.toLocaleString()} kg (${Math.round(pct)}%)`;
  document.getElementById('space-left').textContent = 
    `Space left: ${Math.max(0, spaceLeft).toLocaleString()} kg`;
    
  const fill = document.getElementById('capacity-fill');
  fill.style.width = `${Math.min(100, pct)}%`;
  
  if (!data.within_capacity) {
    fill.style.background = 'var(--bad)';
  } else {
    fill.style.background = 'var(--amber)';
  }

  // --- Global Error Banner ---
  const errBanner = document.getElementById('global-errors');
  const errCount = document.getElementById('error-count');
  const errList = document.getElementById('error-list');
  
  if (data.messages && data.messages.length > 0) {
    errBanner.style.display = 'block';
    errCount.textContent = `${data.messages.length} row${data.messages.length > 1 ? 's' : ''} need fixing`;
    errList.innerHTML = data.messages.map(msg => `<li>${msg}</li>`).join('');
  } else {
    errBanner.style.display = 'none';
  }

  // --- Generate Button State ---
  const btnGen = document.getElementById('btn-generate');
  btnGen.disabled = !data.can_generate;
}

// 5. Add Row Form
const qtyInput = document.getElementById('add-qty');
const unitWtInput = document.getElementById('add-unit-wt');
const totalInput = document.getElementById('add-total');

function calcTotal() {
  const q = parseFloat(qtyInput.value) || 0;
  const w = parseFloat(unitWtInput.value) || 0;
  totalInput.value = (q * w).toFixed(2);
}
qtyInput.addEventListener('input', calcTotal);
unitWtInput.addEventListener('input', calcTotal);

document.getElementById('add-row-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const custSelect = document.getElementById('add-customer');
  if (!custSelect.value) return toast('Select a customer', 'error');
  
  // We pass the customer NAME to match the backend upload validation
  const payload = {
    customer_name: custSelect.options[custSelect.selectedIndex].dataset.name,
    product: document.getElementById('add-product').value,
    quantity: parseInt(qtyInput.value),
    unit_weight: parseFloat(unitWtInput.value)
  };

  try {
    await apiFetch('/staging/rows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    }).then(res => res.json());
    toast('Row added', 'ok');
    document.getElementById('add-row-form').reset();
    totalInput.value = '';
    await fetchStagingState();
  } catch (ex) {
    toast(ex.message, 'error');
  }
});

// 6. Edit Modal Logic
function openEditModal(rowId) {
  const row = stagingRows.find(r => r.row_id === rowId);
  if (!row) return;

  document.getElementById('edit-row-id').value = rowId;
  document.getElementById('edit-product').value = row.product || '';
  document.getElementById('edit-qty').value = row.quantity || '';
  document.getElementById('edit-unit-wt').value = row.unit_weight || '';

  // Try to select the current customer in the dropdown
  const editCustSelect = document.getElementById('edit-customer');
  if (row.customer_name) {
    const matchedOption = Array.from(editCustSelect.options).find(
      o => o.dataset.name === row.customer_name
    );
    if (matchedOption) editCustSelect.value = matchedOption.value;
  }

  document.getElementById('edit-modal').style.display = 'flex';
}

function closeEditModal() {
  document.getElementById('edit-modal').style.display = 'none';
}

document.getElementById('edit-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const rowId = document.getElementById('edit-row-id').value;
  const custSelect = document.getElementById('edit-customer');
  
  const payload = {
    customer_name: custSelect.options[custSelect.selectedIndex].dataset.name,
    product: document.getElementById('edit-product').value,
    quantity: parseInt(document.getElementById('edit-qty').value),
    unit_weight: parseFloat(document.getElementById('edit-unit-wt').value)
  };

  try {
    await apiFetch(`/staging/rows/${rowId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    }).then(res => res.json());
    toast('Row updated', 'ok');
    closeEditModal();
    await fetchStagingState();
  } catch (ex) {
    toast(ex.message, 'error');
  }
});

// 7. Delete Row
async function deleteRow(rowId) {
  if (!confirm('Delete this row?')) return;
  try {
    await apiFetch(`/staging/rows/${rowId}`, { method: 'DELETE' });
    await fetchStagingState();
  } catch (ex) { toast(ex.message, 'error'); }
}

// 8. Generate Plan
document.getElementById('btn-generate').addEventListener('click', async () => {
  const btn = document.getElementById('btn-generate');
  btn.disabled = true;
  btn.textContent = 'Optimizing...';
  
  try {
    const response = await apiFetch('/plans/generate', { method: 'POST' });
    
    // Check if the server actually succeeded
    if (!response.ok) {
      const errData = await response.json();
      throw new Error(errData.detail || `Server error: ${response.status}`);
    }
    
    // Only redirect if it was successful
    window.location.href = '/plans/draft/view';
  } catch (ex) {
    toast(ex.message, 'error');
    btn.textContent = 'Generate Sequence';
    btn.disabled = false;
  }
});