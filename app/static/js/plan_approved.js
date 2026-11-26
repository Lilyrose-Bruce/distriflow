let approvedPlan = null;
let deliveryCSV = "";
let loadingCSV = "";

(async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const planId = urlParams.get('id');

  if (!planId) {
    toast('No plan ID provided.', 'error');
    window.location.href = '/plans/saved';
    return;
  }

  try {
    approvedPlan = await apiJson(`/plans/${planId}`);
    renderPlanDetails();
  } catch (ex) {
    toast(ex.message, 'error');
    setTimeout(() => window.location.href = '/plans/saved', 2000);
  }
})();

function renderPlanDetails() {
  const year = new Date().getFullYear();
  const paddedId = String(approvedPlan.plan_id).padStart(4, '0');
  const code = `DF-${year}-${paddedId}`;
  
  document.getElementById('plan-code').textContent = `${code} saved`;
  
  const truck = approvedPlan.truck_license_plate || 'Truck';
  const stopsCount = approvedPlan.stops.length;
  const weight = approvedPlan.total_weight.toLocaleString();
  const dist = approvedPlan.total_distance.toFixed(1);
  const hours = (approvedPlan.total_time / 60).toFixed(1);
  
  document.getElementById('plan-summary').textContent = 
    `${truck}, ${stopsCount} stops, ${weight} kg, ${dist} km, ${hours} hours. It now appears under Approved Plans and on the Overview.`;

  buildCSVs();
}

function buildCSVs() {
  // Delivery Sequence
  let dCsv = "Stop,Customer,Town,Arrive,Weight (kg)\n";
  approvedPlan.stops.forEach(s => {
    const time = s.arrival_time || '--:--'; 
    const customer = `"${s.customer.customer_name.replace(/"/g, '""')}"`;
    const town = `"${s.customer.town.replace(/"/g, '""')}"`;
    const stopitems = s.items;
    dCsv += `${s.stop_sequence},${customer},${town},${time},${stopitems}\n`;
  });
  deliveryCSV = dCsv;
  document.getElementById('delivery-csv-preview').textContent = dCsv;

  // Loading Plan (Reverse Order)
  let lCsv = "Load order,For stop,Customer,Product,Quantity,Weight (kg)\n";
  const reversedStops = [...approvedPlan.stops].reverse();
  let loadNum = 1;
  
  reversedStops.forEach(s => {
    const customer = `"${s.customer.customer_name.replace(/"/g, '""')}"`;
    s.items.forEach(item => {
      const product = `"${item.product.replace(/"/g, '""')}"`;
      lCsv += `${loadNum},${s.stop_sequence},${customer},${product},${item.quantity},${item.total_weight}\n`;
      loadNum++;
    });
  });
  loadingCSV = lCsv;
  document.getElementById('loading-csv-preview').textContent = lCsv;
}

function downloadCSV(type) {
  const csvData = type === 'delivery' ? deliveryCSV : loadingCSV;
  const filename = type === 'delivery' ? 'delivery_sequence.csv' : 'loading_plan.csv';
  
  const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  toast(`${filename} downloaded`, 'ok');
}

async function copyToClipboard(type) {
  const text = type === 'delivery' ? deliveryCSV : loadingCSV;
  
  try {
    await navigator.clipboard.writeText(text);
    toast('Copied to clipboard!', 'ok');
  } catch (err) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand("copy");
    document.body.removeChild(textArea);
    toast('Copied to clipboard!', 'ok');
  }
}