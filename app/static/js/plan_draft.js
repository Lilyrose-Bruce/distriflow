let draftData = null;
let originalStopOrder = [];
let originalMetrics = {};
let isDragging = false;

// 1. Initialize
const today = new Date().toISOString().split('T')[0];
document.getElementById('delivery-date-input').value = today;

(async () => {
  await loadDraft();
})();

async function loadDraft() {
  try {
    draftData = await apiJson('/plans/draft');
    
    // If no draft exists, kick back to staging
    if (!draftData || !draftData.stops) {
        toast('No draft plan found. Please generate one from staging.', 'error');
        window.location.href = '/staging';
        return;
    }

    // Store original state for the "Reset" button
    if (originalStopOrder.length === 0) {
      originalStopOrder = draftData.stops.map(s => s.customer_id);
      originalMetrics = { ...draftData.metrics };
    }

    document.getElementById('truck-plate').textContent = draftData.truck_license_plate || 'Selected Truck';
    document.getElementById('stop-count').textContent = draftData.stops.length;

    renderStops();
    renderLoadingPlan();
    renderMetrics();
    renderRouteSketch();

  } catch (ex) {
    toast(ex.message, 'error');
  }
}

// 2. Render Delivery Sequence (Draggable)
function renderStops() {
  const list = document.getElementById('stops-list');
  
  // We use customer_id as the unique identifier because it's always present
  list.innerHTML = draftData.stops.map((s, i) => `
    <li class="stop-item" draggable="true" data-id="${s.customer_id}" data-index="${i}"
        style="display: flex; align-items: center; gap: 16px; padding: 16px; border: 1px solid var(--line); border-radius: 8px; margin-bottom: 12px; background: var(--surface); cursor: grab;">
      
      <div style="color: var(--muted); font-size: 1.2rem; cursor: grab;">⋮⋮</div>
      
      <div style="width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--navy); display: flex; align-items: center; justify-content: center; font-weight: 600; flex-shrink: 0;">
        ${i + 1}
      </div>
      
      <div style="flex: 1;">
        <div style="font-weight: 600;">${s.customer_name}</div>
        <div class="muted" style="font-size: 0.85rem;">${s.town || 'Unknown'} · open 08:00–17:00</div>
        <div class="muted" style="font-size: 0.85rem;">Arrive ${s.arrival_time || '--:--'}</div>
      </div>
      
      <div style="display: flex; flex-direction: column; gap: 4px;">
        <button class="btn small" onclick="moveStop(${i}, -1)" ${i === 0 ? 'disabled' : ''}>▲</button>
        <button class="btn small" onclick="moveStop(${i}, 1)" ${i === draftData.stops.length - 1 ? 'disabled' : ''}>▼</button>
      </div>
    </li>
  `).join('');

  attachDragEvents();
}

// 3. Render Loading Plan (Reverse Order)
function renderLoadingPlan() {
  const container = document.getElementById('loading-list');
  
  // Reverse the stops to match LIFO loading
  const reversedStops = [...draftData.stops].reverse();
  
  container.innerHTML = reversedStops.map((s, i) => `
    <div style="border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin-bottom: 12px;">
      <div class="muted" style="font-size: 0.75rem; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px;">Load ${i + 1}</div>
      <div style="font-weight: 600; margin-bottom: 4px;">Stop ${s.stop_sequence}: ${s.customer_name}</div>
      <div class="muted" style="font-size: 0.9rem; margin-bottom: 8px;">${s.stop_weight} kg</div>
      <ul style="margin: 0; padding-left: 20px; font-size: 0.85rem; color: var(--muted);">
        ${s.items.map(item => `<li>${item.quantity} × ${item.product}</li>`).join('')}
      </ul>
    </div>
  `).join('');
}

// 4. Render Metrics Table
function renderMetrics() {
  const m = draftData.metrics;
  const orig = originalMetrics;
  
  // Calculate differences based on your EXACT backend field names
  const distDiff = m.total_distance_km - orig.total_distance_km;
  const timeDiff = m.total_travel_minutes - orig.total_travel_minutes;
  
  const tbody = document.getElementById('metrics-body');
  tbody.innerHTML = `
    <tr>
      <td style="padding: 12px 10px; border-bottom: 1px solid var(--line);">Distance (km)</td>
      <td style="padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: right;">${orig.total_distance_km.toFixed(1)}</td>
      <td style="padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: right; font-weight: 600;">${m.total_distance_km.toFixed(1)}</td>
    </tr>
    <tr>
      <td style="padding: 12px 10px; border-bottom: 1px solid var(--line);">Travel time (h)</td>
      <td style="padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: right;">${(orig.total_travel_minutes / 60).toFixed(1)}</td>
      <td style="padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: right; font-weight: 600;">${(m.total_travel_minutes / 60).toFixed(1)}</td>
    </tr>
    <tr>
      <td style="padding: 12px 10px; border-bottom: 1px solid var(--line);">Stops</td>
      <td style="padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: right;">${orig.stops_count}</td>
      <td style="padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: right; font-weight: 600;">${m.stops_count}</td>
    </tr>
  `;

  // Alert Box & Reset Button
  const alertBox = document.getElementById('metric-alert');
  const btnReset = document.getElementById('btn-reset');
  
  if (Math.abs(distDiff) < 0.1 && Math.abs(timeDiff) < 1) { // Basically unchanged
    alertBox.innerHTML = 'Matches the original plan. Drag a stop to try a different order.';
    btnReset.disabled = true;
  } else {
    const distKm = Math.abs(distDiff).toFixed(1);
    const timeH = Math.abs(timeDiff / 60).toFixed(1);
    const direction = distDiff > 0 ? 'longer' : 'shorter';
    
    alertBox.innerHTML = `<strong>Changed plan is ${distKm} km and ${timeH} h ${direction} than the original.</strong><br>Metrics update after every move.`;
    btnReset.disabled = false;
  }
}

// 5. Drag & Drop Events
function attachDragEvents() {
  const items = document.querySelectorAll('.stop-item');
  
  items.forEach(item => {
    item.addEventListener('dragstart', () => {
      isDragging = true;
      item.style.opacity = '0.5';
      item.classList.add('dragging');
    });
    
    item.addEventListener('dragend', () => {
      isDragging = false;
      item.style.opacity = '1';
      item.classList.remove('dragging');
    });
    
    item.addEventListener('dragover', (e) => {
      e.preventDefault(); 
    });
    
    item.addEventListener('drop', async (e) => {
      e.preventDefault();
      const draggingItem = document.querySelector('.dragging');
      if (!draggingItem || draggingItem === item) return;
      
      const itemsArray = [...document.querySelectorAll('.stop-item')];
      const fromIndex = itemsArray.indexOf(draggingItem);
      const toIndex = itemsArray.indexOf(item);
      
      if (fromIndex < toIndex) {
        item.parentNode.insertBefore(draggingItem, item.nextSibling);
      } else {
        item.parentNode.insertBefore(draggingItem, item);
      }
      
      // Ensure we extract and parse the stop_id as a Number
      const newOrder = [...document.querySelectorAll('.stop-item')].map(li => Number(li.dataset.id));
      
      await saveNewOrder(newOrder);
    });
  });
}

// 6. Move via Arrows
async function moveStop(index, direction) {
  const items = [...document.querySelectorAll('.stop-item')];
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= items.length) return;
  
  // Swap in array
  const temp = draftData.stops[index];
  draftData.stops[index] = draftData.stops[targetIndex];
  draftData.stops[targetIndex] = temp;
  
  const newOrder = draftData.stops.map(s => s.customer_id);
  await saveNewOrder(newOrder);
}

// 7. Save & Recalculate
async function saveNewOrder(newStopIds) {
  try {
    document.getElementById('stops-list').style.opacity = '0.5';
    
    // We send customer_ids now
    const response = await fetch('/plans/draft/reorder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ stop_ids: newStopIds }) // Pydantic schema still calls it stop_ids, but we pass customer_ids
    });
    
    if (!response.ok) {
        const err = await response.json();
        console.error("Reorder Error:", err);
        throw new Error(err.detail ? JSON.stringify(err.detail) : 'Failed to reorder');
    }

    const updatedDraft = await response.json();
    draftData = updatedDraft; 
    await loadDraft(); 
    
    document.getElementById('stops-list').style.opacity = '1';
  } catch (ex) {
    toast(ex.message, 'error');
    document.getElementById('stops-list').style.opacity = '1';
    await loadDraft(); 
  }
}


// 8. Reset Button
async function resetToOriginal() {
  await saveNewOrder(originalStopOrder);
}

// 9. Route Sketch (Real Maps using Leaflet)
let mapOriginal = null;
let mapChanged = null;
let layerOriginal = null;
let layerChanged = null;

function renderRouteSketch() {
  const stops = draftData.stops;
  if (stops.length === 0) return;

  // Depot coordinates
  const depotLat = draftData.depot_latitude || -1.286389;
  const depotLng = draftData.depot_longitude || 36.817223;
  const depotPoint = [depotLat, depotLng];

  // Build coordinate arrays for both maps
  // Original: Depot -> originalStopOrder -> Depot
  const originalCoords = [depotPoint];
  originalStopOrder.forEach(id => {
    const stop = stops.find(s => s.customer_id === id);
    if (stop) originalCoords.push([parseFloat(stop.latitude), parseFloat(stop.longitude)]);
  });
  originalCoords.push(depotPoint);

  // Changed: Depot -> current stops order -> Depot
  const changedCoords = [depotPoint];
  stops.forEach(s => {
    changedCoords.push([parseFloat(s.latitude), parseFloat(s.longitude)]);
  });
  changedCoords.push(depotPoint);

  // Initialize maps if they don't exist yet
  if (!mapOriginal) {
    mapOriginal = L.map('map-original').setView(depotPoint, 8);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(mapOriginal);
  }

  if (!mapChanged) {
    mapChanged = L.map('map-changed').setView(depotPoint, 8);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(mapChanged);
  }

  // Clear existing lines and markers
  if (layerOriginal) mapOriginal.removeLayer(layerOriginal);
  if (layerChanged) mapChanged.removeLayer(layerChanged);

  // Draw Original Route (Gray line)
  layerOriginal = L.layerGroup().addTo(mapOriginal);
  L.polyline(originalCoords, { color: '#5B6478', weight: 3, dashArray: '5, 10' }).addTo(layerOriginal);
  
  // Draw Changed Route (Navy line)
  layerChanged = L.layerGroup().addTo(mapChanged);
  L.polyline(changedCoords, { color: '#1E2761', weight: 4 }).addTo(layerChanged);

  // Add Markers to Original Map
  L.marker(depotPoint).addTo(layerOriginal).bindPopup('Depot');
  originalStopOrder.forEach((id, i) => {
    const stop = stops.find(s => s.customer_id === id);
    if (stop) {
      L.marker([stop.latitude, stop.longitude])
        .addTo(layerOriginal)
        .bindPopup(`${i + 1}. ${stop.customer_name}`);
    }
  });

  // Add Markers to Changed Map
  L.marker(depotPoint).addTo(layerChanged).bindPopup('Depot');
  stops.forEach((s, i) => {
    L.marker([s.latitude, s.longitude])
      .addTo(layerChanged)
      .bindPopup(`${i + 1}. ${s.customer_name}`);
  });

  // Auto-zoom both maps to fit their routes
  mapOriginal.fitBounds(L.latLngBounds(originalCoords), { padding: [30, 30] });
  mapChanged.fitBounds(L.latLngBounds(changedCoords), { padding: [30, 30] });

  // Fix for Leaflet rendering issues inside CSS grids
  setTimeout(() => {
    mapOriginal.invalidateSize();
    mapChanged.invalidateSize();
  }, 100);
}

// 10. Approve Plan
async function approvePlan() {
  const btn = document.querySelector('button[onclick="approvePlan()"]');
  const dateInput = document.getElementById('delivery-date-input').value;
  
  if (!dateInput) {
    return toast('Please select a delivery date.', 'error');
  }

  const originalText = btn.textContent;
  btn.textContent = 'Approving...';
  btn.disabled = true;

  try {
    const plan = await apiJson('/plans/approve', { 
        method: 'POST',
        body: JSON.stringify({ delivery_date: dateInput }) // Send the selected date
    });
    
    toast('Plan approved successfully!', 'ok');
    window.location.href = `/plans/approved?id=${plan.plan_id}`; 
  } catch (ex) {
    toast(ex.message, 'error');
    btn.textContent = originalText;
    btn.disabled = false;
  }
}