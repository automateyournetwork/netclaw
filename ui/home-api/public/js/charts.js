'use strict';

var Charts = {
  instances: {},

  colors: {
    blue: '#3b82f6',
    accent: '#22d3a7',
    amber: '#f59e0b',
    grid: '#1a2d4a',
    axis: '#64748b'
  },

  createWanChart: function(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return null;
    el.innerHTML = '';

    var rect = el.getBoundingClientRect();
    var w = Math.floor(rect.width) || 600;
    var h = 200;

    var opts = {
      width: w,
      height: h,
      cursor: { show: true },
      legend: { show: false },
      scales: {
        x: { time: true },
        y: { auto: true },
        loss: { auto: true, range: [0, 100] }
      },
      axes: [
        { stroke: this.colors.axis, grid: { stroke: this.colors.grid, width: 1 }, ticks: { show: false } },
        { stroke: this.colors.blue, size: 50, gap: 4, values: function(u, v) { return v.map(function(n) { return n.toFixed(0) + ' ms'; }); }, grid: { stroke: this.colors.grid, width: 1 } },
        { stroke: this.colors.accent, side: 1, scale: 'loss', size: 40, gap: 4, values: function(u, v) { return v.map(function(n) { return n.toFixed(0) + '%'; }); }, grid: { show: false } }
      ],
      series: [
        {},
        { label: 'Latency (ms)', stroke: this.colors.blue, width: 2, fill: 'rgba(59,130,246,0.08)', scale: 'y' },
        { label: 'Loss x100', stroke: this.colors.accent, width: 2, fill: 'rgba(34,211,167,0.05)', scale: 'loss' }
      ]
    };

    var chart = new uPlot(opts, [[], [], []], el);
    this.instances.wan = chart;
    this._autoResize(el, chart, h);
    return chart;
  },

  createThroughputChart: function(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return null;
    el.innerHTML = '';

    var rect = el.getBoundingClientRect();
    var w = Math.floor(rect.width) || 600;
    var h = 200;

    var opts = {
      width: w,
      height: h,
      cursor: { show: true },
      legend: { show: false },
      scales: {
        x: { time: true },
        y: { auto: true }
      },
      axes: [
        { stroke: this.colors.axis, grid: { stroke: this.colors.grid, width: 1 }, ticks: { show: false } },
        { stroke: this.colors.blue, size: 55, gap: 4, values: function(u, v) { return v.map(function(n) { return n.toFixed(0) + ' M'; }); }, grid: { stroke: this.colors.grid, width: 1 } }
      ],
      series: [
        {},
        { label: 'Download (Mbps)', stroke: this.colors.blue, width: 2, fill: 'rgba(59,130,246,0.1)' },
        { label: 'Upload (Mbps)', stroke: this.colors.amber, width: 2, fill: 'rgba(245,158,11,0.05)' }
      ]
    };

    var chart = new uPlot(opts, [[], [], []], el);
    this.instances.throughput = chart;
    this._autoResize(el, chart, h);
    return chart;
  },

  updateWanChart: function(apiData) {
    var chart = this.instances.wan;
    if (!chart || !apiData) return;
    if (!apiData.latency || !apiData.latency.timestamps || apiData.latency.timestamps.length < 2) return;

    var scaledLoss = apiData.loss.values.map(function(v) { return v * 100; });
    chart.setData([apiData.latency.timestamps, apiData.latency.values, scaledLoss]);
  },

  updateThroughputChart: function(apiData) {
    var chart = this.instances.throughput;
    if (!chart || !apiData) return;
    if (!apiData.download || !apiData.download.timestamps || apiData.download.timestamps.length < 2) return;

    var dlMbps = apiData.download.values.map(function(v) { return v / 1e6; });
    var ulMbps = apiData.upload.values.map(function(v) { return v / 1e6; });
    chart.setData([apiData.download.timestamps, dlMbps, ulMbps]);
  },

  _autoResize: function(el, chart, fixedHeight) {
    var timeout;
    window.addEventListener('resize', function() {
      clearTimeout(timeout);
      timeout = setTimeout(function() {
        var rect = el.getBoundingClientRect();
        if (rect.width > 0) {
          chart.setSize({ width: Math.floor(rect.width), height: fixedHeight });
        }
      }, 150);
    });
  }
};
