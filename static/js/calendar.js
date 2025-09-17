const monthName = (d)=> d.toLocaleString('default', { month: 'long' });

function renderCalendar(containerId){
  const c = document.getElementById(containerId);
  const state = { view: new Date(), booked: new Set() };

  fetch('/api/booked-dates').then(r=>r.json()).then(d=>{
    (d.booked_dates||[]).forEach(x=> state.booked.add(x));
    draw();
  }).catch(draw);

  function draw(){
    const y = state.view.getFullYear();
    const m = state.view.getMonth();
    const first = new Date(y, m, 1);
    const startDay = first.getDay();
    const daysInMonth = new Date(y, m+1, 0).getDate();

    c.innerHTML = `
      <div class="flex items-center justify-between mb-4">
        <button id="prevM" class="px-3 py-1 rounded-xl border border-white/15 text-white/80">←</button>
        <h2 class="text-xl font-semibold">${monthName(state.view)} ${y}</h2>
        <button id="nextM" class="px-3 py-1 rounded-xl border border-white/15 text-white/80">→</button>
      </div>
      <div class="grid grid-cols-7 text-center text-sm font-medium mb-1 text-white/70">
        <div>Sun</div><div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div>
      </div>
      <div id="grid" class="grid grid-cols-7 gap-2"></div>
      <div id="msg" class="mt-3 text-sm text-white/80"></div>`;

    document.getElementById('prevM').onclick = ()=>{ state.view = new Date(y, m-1, 1); draw(); };
    document.getElementById('nextM').onclick = ()=>{ state.view = new Date(y, m+1, 1); draw(); };

    const grid = document.getElementById('grid');
    for(let i=0;i<startDay;i++) grid.appendChild(document.createElement('div'));

    for(let d=1; d<=daysInMonth; d++){
      const dt = new Date(y,m,d);
      const iso = dt.toISOString().slice(0,10);
      const isPast = dt < new Date(new Date().toDateString());
      const isToday = dt.toDateString() === new Date().toDateString();
      const booked = state.booked.has(iso);

      const btn = document.createElement('button');
      btn.className = "p-2 rounded-xl border text-sm transition border-white/15";
      btn.textContent = d;

      if (booked){
        btn.className += " bg-red-900/30 cursor-not-allowed opacity-60";
        btn.title = "Booked";
        btn.disabled = true;
      } else if (isPast || isToday){
        btn.className += " bg-white/5 cursor-not-allowed opacity-50";
        btn.title = isToday ? "Today (not bookable)" : "Past date";
        btn.disabled = true;
      } else {
        btn.className += " bg-green-900/20 hover:scale-[1.03]";
        btn.title = "Available – click to checkout";
        btn.onclick = ()=> bookDate(iso);
      }
      grid.appendChild(btn);
    }
  }

  function bookDate(iso){
    const msg = document.getElementById('msg');
    if (msg) msg.textContent = "Redirecting to secure checkout...";
    fetch('/create-checkout-session', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ date: iso })
    })
    .then(r=>r.json())
    .then(data=>{
      if(data && data.checkout_url){
        window.location = data.checkout_url;
      } else if (msg) {
        msg.textContent = (data && data.error) || "Could not create checkout session.";
      }
    })
    .catch(()=> { if (msg) msg.textContent = "Network error. Try again."; });
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  const el = document.getElementById('calendar');
  if(el) renderCalendar('calendar');
});
