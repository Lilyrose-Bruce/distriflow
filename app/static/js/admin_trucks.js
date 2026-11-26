let trucks = [];
let isAdmin = false;

(async () => {
  const me = await apiJson('/auth/me');
  isAdmin = me.role === 'Administrator';
  
  if (isAdmin) {
    document.getElementById('btn-add').style.display = 'block';
    document.getElementById('th-actions').style.display = 'table-cell';
  }
  
  await loadTrucks();
})();

async function loadTrucks() {
  try {
    trucks = await apiJson('/trucks');
    const tbody = document.querySelector('#trucks-table tbody');
    
    if (!trucks.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="muted" style="text-align: center; padding: 24px;">No trucks found.</td></tr>';
      return;
    }

    tbody.innerHTML = trucks.map(t => `
      <tr>
        <td style="font-weight: 500;">${t.license_plate}</td>
        <td class="r">${t.max_weight_capacity.toLocaleString()}</td>
        <td class="r"><span class="badge" style="background: ${t.is_active ? 'var(--ok-soft)' : 'var(--surface-2)'}; color: ${t.is_active ? 'var(--ok)' : 'var(--muted)'};">${t.is_active ? 'Active' : 'Inactive'}</span></td>
        ${isAdmin ? `<td class="r">
          <button class="btn link small" onclick="editTruck(${t.truck_id})">Edit</button>
          <button class="btn link small danger" onclick="deleteTruck(${t.truck_id})">Delete</button>
        </td>` : ''}
      </tr>
    `).join('');
  } catch (ex) { toast(ex.message, 'error'); }
}

function openModal(truck = null) {
  document.getElementById('modal-title').textContent = truck ? 'Edit Truck' : 'Add Truck';
  document.getElementById('entity-id').value = truck ? truck.truck_id : '';
  document.getElementById('f-plate').value = truck ? truck.license_plate : '';
  document.getElementById('f-capacity').value = truck ? truck.max_weight_capacity : '';
  document.getElementById('f-active').checked = truck ? truck.is_active : true;
  document.getElementById('modal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal').style.display = 'none';
}

function editTruck(id) {
  const t = trucks.find(x => x.truck_id === id);
  if (t) openModal(t);
}

async function deleteTruck(id) {
  if (!confirm('Delete this truck?')) return;
  try {
    await apiFetch(`/trucks/${id}`, { method: 'DELETE' });
    toast('Truck deactivated', 'ok');
    loadTrucks();
  } catch (ex) { toast(ex.message, 'error'); }
}

document.getElementById('entity-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const id = document.getElementById('entity-id').value;
  const payload = {
    license_plate: document.getElementById('f-plate').value,
    max_weight_capacity: parseFloat(document.getElementById('f-capacity').value),
    is_active: document.getElementById('f-active').checked
  };

  const method = id ? 'PUT' : 'POST';
  const url = id ? `/trucks/${id}` : '/trucks';

  try {
    await apiJson(url, { method, body: JSON.stringify(payload) });
    toast('Truck saved', 'ok');
    closeModal();
    loadTrucks();
  } catch (ex) { toast(ex.message, 'error'); }
});