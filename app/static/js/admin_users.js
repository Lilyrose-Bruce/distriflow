let users = [];
let currentUser = null;

// 1. Initialize
(async () => {
  try {
    currentUser = await apiJson('/auth/me');
    
    // Double check the user is an admin (though the backend will block them anyway)
    if (currentUser.role !== 'Administrator') {
      toast('Administrator access required.', 'error');
      window.location.href = '/dashboard';
      return;
    }
    
    document.getElementById('btn-add').style.display = 'block';
    document.getElementById('th-actions').style.display = 'table-cell';
    
    await loadUsers();
  } catch (ex) {
    toast(ex.message, 'error');
  }
})();

// 2. Fetch and Render Users
async function loadUsers() {
  try {
    users = await apiJson('/users');
    const tbody = document.querySelector('#users-table tbody');
    
    if (!users || !users.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="muted" style="text-align: center; padding: 24px;">No users found.</td></tr>';
      return;
    }

    tbody.innerHTML = users.map(u => {
      // Highlight your own account so you don't accidentally delete yourself
      const isMe = u.user_id === currentUser.user_id;
      
      return `
      <tr>
        <td style="font-weight: 500;">
          ${u.full_name} ${isMe ? '<span class="badge" style="margin-left: 8px; background: var(--navy); color: white;">You</span>' : ''}
        </td>
        <td class="muted">${u.username}</td>
        <td><span class="badge">${u.role}</span></td>
        <td class="r">
          <span class="badge" style="background: ${u.is_active ? 'var(--ok-soft)' : 'var(--surface-2)'}; color: ${u.is_active ? 'var(--ok)' : 'var(--muted)'};">
            ${u.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td class="r">
          <button class="btn link small" onclick="editUser(${u.user_id})">Edit</button>
          ${isMe ? '' : `<button class="btn link small danger" onclick="deactivateUser(${u.user_id})">Deactivate</button>`}
        </td>
      </tr>
    `}).join('');
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

// 3. Modal Logic
function openModal(user = null) {
  document.getElementById('modal-title').textContent = user ? 'Edit User' : 'Add User';
  document.getElementById('entity-id').value = user ? user.user_id : '';
  document.getElementById('f-name').value = user ? user.full_name : '';
  document.getElementById('f-user').value = user ? user.username : '';
  document.getElementById('f-pass').value = ''; // Always blank for security
  document.getElementById('f-role').value = user ? user.role : 'Dispatcher';
  document.getElementById('f-active').checked = user ? user.is_active : true;
  
  // Password is only required for NEW users. When editing, leaving it blank keeps the old one.
  document.getElementById('f-pass').required = !user;
  
  // If editing yourself, disable the role and active toggles so you don't lock yourself out
  const isMe = user && user.user_id === currentUser.user_id;
  document.getElementById('f-role').disabled = isMe;
  document.getElementById('f-active').disabled = isMe;
  
  document.getElementById('modal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal').style.display = 'none';
}

function editUser(id) {
  const u = users.find(x => x.user_id === id);
  if (u) openModal(u);
}

// 4. Deactivate User (The backend uses DELETE for this)
async function deactivateUser(id) {
  if (!confirm('Deactivate this user? They will no longer be able to log in.')) return;
  
  try {
    await apiFetch(`/users/${id}`, { method: 'DELETE' });
    toast('User deactivated', 'ok');
    loadUsers(); // Reload the table
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

// 5. Save User (Create or Update)
document.getElementById('entity-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const id = document.getElementById('entity-id').value;
  const password = document.getElementById('f-pass').value;
  
  // Build the payload exactly as the Pydantic schema expects
  const payload = {
    full_name: document.getElementById('f-name').value,
    username: document.getElementById('f-user').value,
    role: document.getElementById('f-role').value,
    is_active: document.getElementById('f-active').checked
  };
  
  // Only include the password if it was typed in
  if (password) {
    payload.password = password;
  }

  const method = id ? 'PUT' : 'POST';
  const url = id ? `/users/${id}` : '/users';

  // For a PUT request, Pydantic's exclude_unset=True means it's safe to send the whole payload.
  // If you only wanted to send changes, you would omit fields here, but sending everything is fine.

  try {
    const response = await apiFetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Failed to save user');
    }
    
    toast(id ? 'User updated' : 'User created', 'ok');
    closeModal();
    loadUsers();
  } catch (ex) {
    toast(ex.message, 'error');
  }
});