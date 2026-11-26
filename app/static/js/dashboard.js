// Global chart instances
let activityChartInstance = null;
let fleetDonutInstance = null;
let currentRange = 7;

// 1. Initialize Dashboard
(async () => {
  await fetchDashboardData(currentRange);

  // Listen for dropdown changes
  document.getElementById('chart-range').addEventListener('change', async (e) => {
    currentRange = parseInt(e.target.value);
    await fetchDashboardData(currentRange);
  });
})();

// 2. Fetch Data from Backend
async function fetchDashboardData(days) {
  try {
    const data = await apiJson(`/dashboard/stats?days=${days}`);
    
    // Update KPIs
    document.getElementById('kpi-active-today').textContent = data.active_today || 0;
    document.getElementById('kpi-total-plans').textContent = data.total_plans || 0;
    document.getElementById('kpi-trucks').textContent = data.active_trucks || 0;
    document.getElementById('kpi-customers').textContent = data.total_customers || 0;

    // Render Components
    renderRecentPlans(data.recent_plans);
    updateActivityChart(data.activity_labels, data.activity_data);
    updateFleetDonut(data.status_breakdown); 

  } catch (ex) {
    console.error(ex);
    toast(ex.message, 'error');
  }
}

// 3. Render Recent Plans Table
function renderRecentPlans(plans) {
  const tbody = document.getElementById('recent-plans-body');
  if (!plans || plans.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="muted" style="text-align: center; padding: 24px;">No plans created yet.</td></tr>';
    return;
  }

  tbody.innerHTML = plans.map(p => {
    let badgeColor = 'var(--navy)';
    if (p.status === 'in_progress') badgeColor = 'var(--amber)';
    if (p.status === 'delivered') badgeColor = 'var(--ok)';

    return `
      <tr>
        <td style="font-weight: 600;">#${p.plan_id}</td>
        <td class="muted">${p.date}</td>
        <td><span class="tag" style="background: var(--surface-2); border: 1px solid var(--line);">${p.truck}</span></td>
        <td class="r">${p.stops}</td>
        <td class="r">
          <select onchange="updateStatus(${p.plan_id}, this.value)" 
                  style="padding: 6px 10px; border-radius: 20px; border: 1px solid ${badgeColor}; 
                         font-size: 0.75rem; background: ${badgeColor}15; color: ${badgeColor}; 
                         font-weight: 700; cursor: pointer; outline: none; text-align: center;">
            <option value="approved" ${p.status === 'approved' ? 'selected' : ''}>APPROVED</option>
            <option value="in_progress" ${p.status === 'in_progress' ? 'selected' : ''}>IN TRANSIT</option>
            <option value="delivered" ${p.status === 'delivered' ? 'selected' : ''}>DELIVERED</option>
          </select>
        </td>
      </tr>
    `;
  }).join('');
}

// 4. Render/Update Line Chart
function updateActivityChart(labels, dataPoints) {
  const ctx = document.getElementById('activityChart').getContext('2d');
  
  // If chart exists, just update the data and re-render (fast)
  if (activityChartInstance) {
    activityChartInstance.data.labels = labels;
    activityChartInstance.data.datasets[0].data = dataPoints;
    activityChartInstance.update();
    return;
  }

  // Otherwise, create a new chart
  activityChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Plans Generated',
        data: dataPoints,
        borderColor: '#1E2761',
        backgroundColor: 'rgba(30, 39, 97, 0.05)',
        borderWidth: 3,
        pointBackgroundColor: '#E8A93B',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 5,
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { 
            beginAtZero: true, 
            grid: { color: 'var(--line)' },
            ticks: { stepSize: 1 } // Force integers (no 2.5 plans!)
        },
        x: { grid: { display: false } }
      }
    }
  });
}

// 5. Render/Update Donut Chart
function updateFleetDonut(statusData) {
  const ctx = document.getElementById('fleetDonut').getContext('2d');
  
  const dataCounts = statusData || { approved: 0, in_progress: 0, delivered: 0 };
  const dataValues = [dataCounts.approved, dataCounts.in_progress, dataCounts.delivered];

  if (fleetDonutInstance) {
    fleetDonutInstance.data.datasets[0].data = dataValues;
    fleetDonutInstance.update();
    return;
  }

  fleetDonutInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Approved', 'In Transit', 'Delivered'],
      datasets: [{
        data: dataValues,
        backgroundColor: ['#1E2761', '#E8A93B', '#1B7F5A'],
        borderWidth: 0,
        cutout: '75%'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      }
    }
  });
}

// 6. Update Status
async function updateStatus(planId, newStatus) {
  try {
    await apiJson(`/plans/${planId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus })
    });
    toast('Status updated', 'ok');
    // Re-fetch dashboard data to update charts immediately
    setTimeout(() => fetchDashboardData(currentRange), 500);
  } catch (ex) {
    toast(ex.message, 'error');
  }
}