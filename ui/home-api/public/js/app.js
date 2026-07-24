'use strict';

var API = {
  token: localStorage.getItem('guardian_token'),
  site: new URLSearchParams(window.location.search).get('site') || 'home',

  fetch: function(endpoint) {
    var sep = endpoint.includes('?') ? '&' : '?';
    var url = '/api' + endpoint + sep + 'site=' + this.site;
    var self = this;

    return fetch(url, {
      headers: { 'Authorization': 'Bearer ' + this.token }
    }).then(function(res) {
      if (res.status === 401) {
        localStorage.removeItem('guardian_token');
        window.location.href = '/login';
        return null;
      }
      if (!res.ok) return null;
      return res.json();
    }).catch(function() { return null; });
  }
};

// Redirect to login if no token
if (!API.token && !window.location.pathname.includes('/login')) {
  window.location.href = '/login';
}

// --- KPI Updates ---

function updateHealth() {
  API.fetch('/health').then(function(data) {
    if (!data) return;

    // Health score
    var healthEl = document.getElementById('health-value');
    var healthSub = document.getElementById('health-subtitle');
    if (healthEl) {
      healthEl.textContent = data.healthScore.value !== null ? data.healthScore.value : '—';
    }
    if (healthSub && data.uptime) {
      var uptimeStr = data.uptime.pct30d !== null ? data.uptime.pct30d + '% uptime · 30d' : '';
      var incidentStr = data.uptime.timeSinceIncident ? ' · ' + data.uptime.timeSinceIncident + ' since last issue' : '';
      healthSub.innerHTML = statusBadgeText(data.healthScore.status, uptimeStr + incidentStr, 'Degraded', 'Unhealthy');
    }

    // Latency
    var latEl = document.getElementById('latency-value');
    var latSub = document.getElementById('latency-subtitle');
    if (latEl) latEl.textContent = data.wanLatency.value !== null ? data.wanLatency.value : '—';
    if (latSub) latSub.innerHTML = statusBadgeText(data.wanLatency.status, 'Within SLA', 'Elevated', 'SLA breach');

    // Speedtest (line capacity, not live utilization)
    var dlEl = document.getElementById('speed-down');
    var ulEl = document.getElementById('speed-up');
    var ispEl = document.getElementById('isp-name');
    var speedSub = document.getElementById('speed-subtitle');
    if (dlEl && data.speedtest) {
      dlEl.textContent = data.speedtest.download !== null ? data.speedtest.download : '—';
    }
    if (ulEl && data.speedtest) {
      ulEl.textContent = data.speedtest.upload !== null ? data.speedtest.upload : '—';
    }
    if (ispEl && data.speedtest) {
      ispEl.textContent = data.speedtest.ispName || '—';
    }

    // Loss
    var lossEl = document.getElementById('loss-value');
    var lossSub = document.getElementById('loss-subtitle');
    if (lossEl) lossEl.textContent = data.wanLoss.value !== null ? data.wanLoss.value : '—';
    if (lossSub) lossSub.innerHTML = statusBadgeText(data.wanLoss.status, 'Nominal', 'Elevated', 'Critical');

    // Update timestamp
    var updated = document.getElementById('last-updated');
    if (updated) updated.textContent = 'Updated just now';
  });
}

function statusBadgeText(status, goodText, warnText, badText) {
  if (status === 'healthy') return '<span class="text-[#22d3a7]">' + goodText + '</span>';
  if (status === 'degraded') return '<span class="text-[#f59e0b]">' + warnText + '</span>';
  if (status === 'unhealthy') return '<span class="text-[#ef4444]">' + badText + '</span>';
  return '<span class="text-slate-500">—</span>';
}

// --- Equipment Table ---

function updateEquipment() {
  API.fetch('/devices').then(function(data) {
    if (!data) return;
    var tbody = document.getElementById('equipment-table');
    if (!tbody) return;

    var rows = '';

    // Edge router (pfSense) - find it in probes
    var pfsense = (data.wanProbes || []).find(function(p) { return p.target === 'pfsense'; });
    if (pfsense) {
      rows += equipmentRow('pfsense', '192.168.3.1', 'Edge router', pfsense.status, 'Latency ' + (pfsense.latencyMs || '—') + ' ms');
    }

    // Switches
    (data.switches || []).forEach(function(sw) {
      var signal = sw.status === 'unmonitored' ? 'No SNMP' :
        sw.interfacesUp + '/' + sw.interfacesTotal + ' ports up' + (sw.errorRate > 0 ? ' · ' + sw.errorRate + ' err/s' : '');
      rows += equipmentRow(sw.name, sw.model, 'Switch', sw.status, signal);
    });

    // Access points
    (data.accessPoints || []).forEach(function(ap) {
      rows += equipmentRow(ap.name, ap.model, 'Access point', ap.status, ap.clients + ' clients');
    });

    // WAN probes as "critical path" entries (excluding pfsense which is already shown)
    var wanOnline = (data.wanProbes || []).filter(function(p) { return p.target !== 'pfsense'; });
    var wanHealthy = wanOnline.every(function(p) { return p.status === 'online'; });
    rows += equipmentRow('wan-probes', wanOnline.length + ' targets', 'Critical path', wanHealthy ? 'online' : 'degraded', wanHealthy ? 'All reachable' : 'Partial outage');

    tbody.innerHTML = rows;
  });
}

function equipmentRow(name, subtitle, role, status, signal) {
  var statusColor = status === 'online' ? 'text-[#22d3a7]' : status === 'degraded' ? 'text-[#f59e0b]' : status === 'unmonitored' ? 'text-slate-500' : 'text-[#ef4444]';
  var statusLabel = status === 'online' ? 'Online' : status === 'degraded' ? 'Degraded' : status === 'unmonitored' ? 'No SNMP' : 'Offline';
  var statusDot = status === 'online' ? 'bg-[#22d3a7]' : status === 'degraded' ? 'bg-[#f59e0b]' : status === 'unmonitored' ? 'bg-slate-500' : 'bg-[#ef4444]';

  return '<tr class="text-sm">' +
    '<td class="py-3 pr-4"><a href="/device/' + name + '?site=' + API.site + '" class="block hover:opacity-80"><div class="font-medium text-white">' + name + '</div><div class="text-xs text-slate-500">' + subtitle + '</div></a></td>' +
    '<td class="py-3 pr-4 text-slate-400">' + role + '</td>' +
    '<td class="py-3 pr-4"><span class="inline-flex items-center gap-1.5 ' + statusColor + '"><span class="w-2 h-2 rounded-full ' + statusDot + '"></span>' + statusLabel + '</span></td>' +
    '<td class="py-3 text-slate-400">' + signal + '</td>' +
    '</tr>';
}

// --- Recent Events (curated diary) ---

function updateEvents() {
  API.fetch('/events?limit=20').then(function(data) {
    if (!data) return;
    var feed = document.getElementById('events-feed');
    if (!feed) return;

    if (!data.events || data.events.length === 0) {
      feed.innerHTML = '<div class="text-sm text-slate-500">No recent events</div>';
      return;
    }

    feed.innerHTML = data.events.map(function(ev) {
      var time = new Date(ev.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' });
      var severity = classifyEvent(ev);
      var hasDetail = ev.investigation_notes || ev.root_cause;
      var clickAttr = hasDetail ? 'onclick="showEventDetail(\'' + ev.id + '\')" style="cursor:pointer;"' : '';
      var expandIcon = hasDetail ? '<span class="text-slate-600 ml-1">+</span>' : '';

      return '<div class="flex gap-3 items-start text-sm hover:bg-guardian-border/20 rounded px-1 py-1" ' + clickAttr + '>' +
        '<span class="text-slate-500 shrink-0 tabular-nums">' + time + '</span>' +
        '<span class="font-medium shrink-0 ' + severity.colorClass + '">' + severity.label + '</span>' +
        '<span class="text-slate-300">' + ev.message + expandIcon + '</span>' +
        '</div>';
    }).join('');

    // Store events for detail view
    window._guardianEvents = data.events;
  });
}

function showEventDetail(eventId) {
  var ev = (window._guardianEvents || []).find(function(e) { return e.id === eventId; });
  if (!ev) return;

  var time = new Date(ev.timestamp).toLocaleString();
  var html = '<div class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onclick="if(event.target===this)this.remove()">' +
    '<div class="bg-guardian-card border border-guardian-border rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">' +
      '<div class="flex justify-between items-start mb-4">' +
        '<div>' +
          '<h3 class="text-lg font-semibold text-white">' + (ev.alert_name || 'Event') + '</h3>' +
          '<div class="text-xs text-slate-400 mt-1">' + time + ' | ' + (ev.category || 'general') + ' | ' + (ev.status || 'logged') + '</div>' +
        '</div>' +
        '<button onclick="this.closest(\'.fixed\').remove()" class="text-slate-400 hover:text-white text-xl">x</button>' +
      '</div>' +
      '<div class="space-y-4">' +
        '<div><div class="text-xs text-slate-400 uppercase mb-1">Message</div><div class="text-sm text-slate-200">' + ev.message + '</div></div>' +
        (ev.investigation_notes ? '<div class="bg-guardian-bg rounded p-3"><div class="text-xs text-slate-400 uppercase mb-1">Investigation Notes</div><div class="text-sm text-slate-300 whitespace-pre-wrap">' + ev.investigation_notes + '</div></div>' : '') +
        (ev.root_cause ? '<div><div class="text-xs text-slate-400 uppercase mb-1">Root Cause</div><div class="text-sm text-white font-medium">' + ev.root_cause + '</div></div>' : '') +
        (!ev.investigation_notes && !ev.root_cause ? '<div class="text-sm text-slate-500">No investigation details recorded for this event.</div>' : '') +
      '</div>' +
    '</div>' +
  '</div>';

  document.body.insertAdjacentHTML('beforeend', html);
}

function classifyEvent(ev) {
  var sev = ev.severity || '';
  if (sev === 'ok') return { label: 'OK', colorClass: 'event-ok' };
  if (sev === 'alert') return { label: 'ALERT', colorClass: 'event-alert' };
  if (sev === 'watch') return { label: 'WATCH', colorClass: 'event-watch' };
  if (sev === 'info') return { label: 'INFO', colorClass: 'event-info' };

  // Fallback: classify from message text
  var lower = (ev.message || '').toLowerCase();
  if (lower.includes('resolved') || lower.includes('completed') || lower.includes('recovered')) {
    return { label: 'OK', colorClass: 'event-ok' };
  }
  if (lower.includes('alert') || lower.includes('critical') || lower.includes('down') || lower.includes('fail')) {
    return { label: 'ALERT', colorClass: 'event-alert' };
  }
  if (lower.includes('warning') || lower.includes('spike') || lower.includes('watch')) {
    return { label: 'WATCH', colorClass: 'event-watch' };
  }
  return { label: 'INFO', colorClass: 'event-info' };
}

// --- Chart Updates ---

var currentRange = '1h';

function updateWanChart() {
  API.fetch('/metrics/wan?range=' + currentRange + '&step=' + getStep(currentRange)).then(function(data) {
    if (data) Charts.updateWanChart(data);
  });
}

function updateThroughputChart() {
  API.fetch('/metrics/throughput?range=24h&step=5m').then(function(data) {
    if (data) Charts.updateThroughputChart(data);
  });
}

function getStep(range) {
  switch (range) {
    case '1h': return '30s';
    case '6h': return '2m';
    case '24h': return '5m';
    case '7d': return '30m';
    default: return '30s';
  }
}

// --- Security Summary ---

function updateSecurity() {
  API.fetch('/security').then(function(data) {
    if (!data) return;
    var el24h = document.getElementById('blocked-24h');
    var el1h = document.getElementById('blocked-1h');
    var statusEl = document.getElementById('security-status');
    var sourcesEl = document.getElementById('top-sources');

    if (el24h) el24h.textContent = data.blockedConnections.last24h !== null ? data.blockedConnections.last24h.toLocaleString() : '—';
    if (el1h) el1h.textContent = data.blockedConnections.lastHour !== null ? data.blockedConnections.lastHour.toLocaleString() : '—';
    if (statusEl) statusEl.textContent = data.status === 'active' ? 'Firewall active' : 'Security data unavailable';

    if (sourcesEl && data.topSources && data.topSources.length > 0) {
      sourcesEl.innerHTML = data.topSources.map(function(s) {
        var badge = '';
        if (s.classification === 'benign') badge = '<span class="text-guardian-accent text-[10px]">scanner</span>';
        else if (s.classification === 'malicious') badge = '<span class="text-red-400 text-[10px]">malicious</span>';
        else if (s.noise) badge = '<span class="text-slate-500 text-[10px]">noise</span>';
        var name = s.name ? '<span class="text-slate-500 text-[10px] ml-1">' + s.name + '</span>' : '';
        return '<div class="flex justify-between items-center text-slate-300"><span><a href="https://ipinfo.io/' + s.ip + '" target="_blank" rel="noopener" class="font-mono text-xs text-blue-400 hover:text-blue-300 underline">' + s.ip + '</a>' + name + '</span><span class="flex items-center gap-2">' + badge + '<span class="text-slate-500 text-xs">' + s.count + '</span></span></div>';
      }).join('');
    } else if (sourcesEl) {
      sourcesEl.innerHTML = '<div class="text-slate-500">No external blocks this hour</div>';
    }
  });
}

// --- Polling ---

function startPolling() {
  requestAnimationFrame(function() {
    Charts.createWanChart('wan-chart');
    Charts.createThroughputChart('throughput-chart');
    updateWanChart();
    updateThroughputChart();
  });

  updateHealth();
  updateEquipment();
  updateEvents();
  updateSecurity();

  setInterval(updateHealth, 30000);
  setInterval(updateEquipment, 30000);
  setInterval(updateEvents, 30000);
  setInterval(updateSecurity, 60000);
  setInterval(updateWanChart, 30000);
  setInterval(updateThroughputChart, 60000);
}

// --- Init ---

document.addEventListener('DOMContentLoaded', function() {
  if (document.getElementById('wan-chart')) {
    startPolling();
  }

  var logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function() {
      localStorage.removeItem('guardian_token');
      window.location.href = '/login';
    });
  }
});
