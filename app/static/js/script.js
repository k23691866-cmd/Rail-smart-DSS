// ───── Sidebar toggle ─────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ───── Live clock ─────
function updateClock() {
  const el = document.getElementById('live-clock');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleString('en-IN', {
    weekday: 'short', day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit', hour12: true
  });
}
setInterval(updateClock, 1000);
updateClock();

// ───── Booking form: live train info ─────
document.addEventListener('DOMContentLoaded', () => {
  const select = document.getElementById('train-select');
  const seatsInput = document.getElementById('seats');
  const info = document.getElementById('train-info');

  if (!select) return;

  async function loadTrainInfo() {
    const id = select.value;
    if (!id) { info.style.display = 'none'; return; }
    try {
      const res = await fetch(`/api/train/${id}`);
      const data = await res.json();
      const seats = parseInt(seatsInput.value) || 1;
      const total = (data.fare * seats).toFixed(2);
      info.style.display = 'flex';
      info.innerHTML = `
        <span><strong>Train:</strong> ${data.name} (${data.number})</span>
        <span><strong>Route:</strong> ${data.source} → ${data.destination}</span>
        <span><strong>Departure:</strong> ${data.departure}</span>
        <span><strong>Available:</strong> ${data.available_seats} seats</span>
        <span><strong>Fare/seat:</strong> ₹${data.fare}</span>
        <span><strong>Total:</strong> ₹${total}</span>
      `;
    } catch (e) {
      info.style.display = 'none';
    }
  }

  select.addEventListener('change', loadTrainInfo);
  if (seatsInput) seatsInput.addEventListener('input', loadTrainInfo);
});

// ───── Auto dismiss alerts ─────
document.querySelectorAll('.alert').forEach(alert => {
  setTimeout(() => {
    alert.style.transition = 'opacity .4s, transform .4s';
    alert.style.opacity = '0';
    alert.style.transform = 'translateX(20px)';
    setTimeout(() => alert.remove(), 400);
  }, 6000);
});