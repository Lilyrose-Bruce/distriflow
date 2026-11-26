let customers = [];
let isAdmin = false;

(async () => {
  const me = await apiJson('/auth/me');
  isAdmin = me.role === 'Administrator';
  
  if (isAdmin) {
    document.getElementById('btn-add').style.display = 'block';
    document.getElementById('th-actions').style.display = 'table-cell';
  }
  
  await loadCustomers();
})();

async function loadCustomers() {
  try {
    customers = await apiJson('/customers');
    const tbody = document.querySelector('#customers-table tbody');
    
    if (!customers.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="muted" style="text-align: center; padding: 24px;">No customers found.</td></tr>';
      return;
    }

    tbody.innerHTML = customers.map(c => `
      <tr>
        <td style="font-weight: 500;">${c.customer_name}</td>
        <td class="muted">${c.town}</td>
        <td class="muted">${c.phone || '-'}</td>
        <td class="r">${c.open_time} - ${c.close_time}</td>
        ${isAdmin ? `<td class="r">
          <button class="btn link small" onclick="editCustomer(${c.customer_id})">Edit</button>
          <button class="btn link small danger" onclick="deleteCustomer(${c.customer_id})">Delete</button>
        </td>` : ''}
      </tr>
    `).join('');
  } catch (ex) { toast(ex.message, 'error'); }
}

function openModal(customer = null) {
  document.getElementById('modal-title').textContent = customer ? 'Edit Customer' : 'Add Customer';
  document.getElementById('entity-id').value = customer ? customer.customer_id : '';
  document.getElementById('f-name').value = customer ? customer.customer_name : '';
  document.getElementById('f-town').value = customer ? customer.town : '';
  document.getElementById('f-phone').value = customer ? customer.phone : '';
  document.getElementById('f-open').value = customer ? customer.open_time : '08:00';
  document.getElementById('f-close').value = customer ? customer.close_time : '17:00';
  document.getElementById('f-lat').value = customer ? customer.latitude : '';
  document.getElementById('f-lng').value = customer ? customer.longitude : '';
  document.getElementById('modal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal').style.display = 'none';
}

function editCustomer(id) {
  const c = customers.find(x => x.customer_id === id);
  if (c) openModal(c);
}

async function deleteCustomer(id) {
  if (!confirm('Delete this customer?')) return;
  try {
    await apiFetch(`/customers/${id}`, { method: 'DELETE' });
    toast('Customer deleted', 'ok');
    loadCustomers();
  } catch (ex) { toast(ex.message, 'error'); }
}

document.getElementById('entity-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const id = document.getElementById('entity-id').value;
  const payload = {
    customer_name: document.getElementById('f-name').value,
    town: document.getElementById('f-town').value,
    phone: document.getElementById('f-phone').value,
    open_time: document.getElementById('f-open').value,
    close_time: document.getElementById('f-close').value,
    latitude: parseFloat(document.getElementById('f-lat').value),
    longitude: parseFloat(document.getElementById('f-lng').value)
  };

  const method = id ? 'PUT' : 'POST';
  const url = id ? `/customers/${id}` : '/customers';

  try {
    await apiJson(url, { method, body: JSON.stringify(payload) });
    toast('Customer saved', 'ok');
    closeModal();
    loadCustomers();
  } catch (ex) { toast(ex.message, 'error'); }
});