// app/static/js/new_plan.js

let selectedFile = null;

// 1. Load Trucks on Page Load
(async () => {
  try {
    const trucks = await apiJson('/trucks');
    const sel = document.getElementById('truck-select');
    sel.innerHTML = '<option value="">— choose a truck —</option>';
    
    trucks.filter(t => t.is_active).forEach(t => {
      const o = document.createElement('option');
      o.value = t.truck_id;
      o.dataset.capacity = t.max_weight_capacity;
      o.textContent = `${t.license_plate} · ${t.max_weight_capacity.toLocaleString()} kg`;
      sel.appendChild(o);
    });
  } catch (ex) {
    toast(ex.message, 'error');
  }
})();

// 2. Handle Truck Selection
document.getElementById('truck-select').addEventListener('change', async (e) => {
  const truckId = e.target.value;
  if (!truckId) return;
  try {
    await apiJson('/staging/truck', {
      method: 'PUT',
      body: JSON.stringify({ truck_id: parseInt(truckId) })
    });
  } catch (ex) {
    toast(ex.message, 'error');
  }
});

// 3. File Drag & Drop / Browse
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileNameDisplay = document.getElementById('file-name');
const fileHelper = document.getElementById('file-helper');
const btnUpload = document.getElementById('btn-upload');

function handleFileSelect(file) {
  if (!file) return;
  selectedFile = file;
  fileNameDisplay.textContent = file.name;
  fileHelper.textContent = `${(file.size / 1024).toFixed(1)} KB ready to check`;
  btnUpload.disabled = false;
}

fileInput.addEventListener('change', (e) => {
  if (e.target.files.length) handleFileSelect(e.target.files[0]);
});

// Drag and drop events
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files[0]);
});

// 4. "Use example orders" button
document.getElementById('btn-example').addEventListener('click', () => {
  const csvContent = "Customer,Product,Quantity,Unit weight (kg),Total weight (kg)\n" +
                     "Mwangi Hardware,MDF board 18mm,40,25,1000\n" +
                     "Njeri Building Supplies,Laminated door,30,18,540\n" +
                     "Otieno Timber Mart,Door frame,60,12,720";
                     
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const file = new File([blob], "example-orders.csv", { type: 'text/csv' });
  
  handleFileSelect(file);
  toast('Example orders loaded', 'ok');
});

// 5. "Copy example file" button
document.getElementById('btn-copy')?.addEventListener('click', () => {
  const text = `Customer,Product,Quantity,Unit weight (kg),Total weight (kg)
Mwangi Hardware,MDF board 18mm,40,25,1000
Njeri Building Supplies,Laminated door,30,18,540
Otieno Timber Mart,Door frame,60,12,720`;
  
  navigator.clipboard.writeText(text).then(() => {
    toast('Copied to clipboard', 'ok');
  });
});

// 6. Upload Action
btnUpload.addEventListener('click', async () => {
  const truckId = document.getElementById('truck-select').value;
  
  if (!truckId) {
    toast('Please select a truck first.', 'error');
    return;
  }
  if (!selectedFile) {
    toast('Please select a file.', 'error');
    return;
  }

  const fd = new FormData();
  fd.append('file', selectedFile);

  const originalText = btnUpload.textContent;
  btnUpload.textContent = 'Uploading...';
  btnUpload.disabled = true;

  try {
    await apiJson('/staging/upload', { method: 'POST', body: fd });
    toast('File uploaded successfully', 'ok');
    // Redirect to the staging table view
    window.location.href = '/staging';
  } catch (ex) {
    toast(ex.message, 'error');
    btnUpload.textContent = originalText;
    btnUpload.disabled = false;
  }
});

// 7. Cancel Action
document.getElementById('btn-cancel').addEventListener('click', async () => {
  if (!confirm('Clear staging and start over?')) return;
  try {
    await apiFetch('/staging', { method: 'DELETE' });
    window.location.href = '/dashboard';
  } catch (ex) {
    toast(ex.message, 'error');
  }
});