/**
 * Real-time telemetry system for PathfinderBot
 * 
 * This module provides functionality for collecting, processing, visualizing,
 * and analyzing telemetry data from the PathfinderBot system.
 */

// Core TelemetrySystem object
const TelemetrySystem = {
  // Configuration options
  config: {
    collectionInterval: 1000,
    batchSize: 10,
    storageMode: 'memory',
    enableAnomaly: true,
    reconnectDelay: 5000
  },
  
  // Connection and data management
  connection: null,
  metrics: {},
  customMetrics: {},
  lastUpdate: 0,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  subscriptions: [],
  
  // Configuration method (called by HTML page)
  configure: function(options) {
    // Merge provided options with defaults
    this.config = {...this.config, ...options};
    console.log('TelemetrySystem configured:', this.config);
    return this;
  },
  
  // Start telemetry collection
  start: function() {
    console.log('TelemetrySystem starting...');
    this.initConnection();
    this.startCollection();
    return this;
  },
  
  // Initialize WebSocket connection
  initConnection: function() {
    // Close existing connection if any
    if (this.connection) {
      this.connection.close();
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/telemetry`;
    
    console.log(`Connecting to telemetry service at ${wsUrl}`);
    this.connection = new WebSocket(wsUrl);
    
    this.connection.onopen = () => {
      console.log('Telemetry connection established');
      this.reconnectAttempts = 0;
      
      // Subscribe to basic metrics
      this.connection.send(JSON.stringify({
        command: 'subscribe',
        metrics: ['system.cpu', 'system.memory', 'system.disk', 'robot.position']
      }));
      
      // Subscribe to custom metrics
      if (this.subscriptions.length > 0) {
        this.connection.send(JSON.stringify({
          command: 'subscribe',
          metrics: this.subscriptions
        }));
      }
    };
    
    this.connection.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.processData(data);
      } catch (err) {
        console.error('Error processing telemetry data:', err);
      }
    };
    
    this.connection.onerror = (error) => {
      console.error('Telemetry connection error:', error);
    };
    
    this.connection.onclose = (event) => {
      console.log('Telemetry connection closed:', event.code, event.reason);
      
      // Try to reconnect after delay
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`Reconnecting (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${this.config.reconnectDelay}ms`);
        setTimeout(() => this.initConnection(), this.config.reconnectDelay);
      } else {
        console.error('Max reconnection attempts reached. Telemetry system offline.');
      }
    };
  },
  
  // Begin collecting data at specified interval
  startCollection: function() {
    // Set up polling interval for custom metrics
    setInterval(() => {
      this.collectCustomMetrics();
    }, this.config.collectionInterval);
  },
  
  // Collect data from custom metric providers
  collectCustomMetrics: function() {
    const customData = {};
    let hasData = false;
    
    // Collect from registered custom metrics
    for (const [name, collector] of Object.entries(this.customMetrics)) {
      try {
        const value = collector();
        customData[name] = value;
        hasData = true;
      } catch (err) {
        console.error(`Error collecting custom metric ${name}:`, err);
      }
    }
    
    // If we have data and connection is open, send it
    if (hasData && this.connection && this.connection.readyState === WebSocket.OPEN) {
      this.connection.send(JSON.stringify({
        command: 'custom_metrics',
        data: customData
      }));
    }
  },
  
  // Process incoming telemetry data
  processData: function(data) {
    if (!data || !data.metrics) {
      console.warn('Received invalid telemetry data format:', data);
      return;
    }
    
    // Update metrics store
    for (const [key, value] of Object.entries(data.metrics)) {
      if (!this.metrics[key]) {
        this.metrics[key] = {
          current: value,
          history: [],
          min: value,
          max: value,
          sum: value,
          count: 1,
          avg: value
        };
      } else {
        const metric = this.metrics[key];
        
        // Update current value
        metric.current = value;
        
        // Update history (limited to 100 points by default)
        metric.history.push({
          value: value,
          timestamp: data.timestamp || Date.now()
        });
        if (metric.history.length > 100) {
          metric.history.shift();
        }
        
        // Update statistics
        metric.min = Math.min(metric.min, value);
        metric.max = Math.max(metric.max, value);
        metric.sum += value;
        metric.count++;
        metric.avg = metric.sum / metric.count;
      }
    }
    
    // Check for anomalies if enabled
    if (this.config.enableAnomaly) {
      for (const [key, value] of Object.entries(data.metrics)) {
        this.anomaly.checkThresholds(key, value);
      }
    }
    
    this.lastUpdate = Date.now();
    
    // Trigger update event
    const event = new CustomEvent('telemetry-update', {
      detail: { metrics: data.metrics }
    });
    document.dispatchEvent(event);
  },
  
  // Subscribe to specific metrics
  subscribe: function(metrics, callback) {
    if (!Array.isArray(metrics)) {
      metrics = [metrics];
    }
    
    // Add to subscriptions list
    metrics.forEach(metric => {
      if (!this.subscriptions.includes(metric)) {
        this.subscriptions.push(metric);
      }
    });
    
    // Send subscription if connected
    if (this.connection && this.connection.readyState === WebSocket.OPEN) {
      this.connection.send(JSON.stringify({
        command: 'subscribe',
        metrics: metrics
      }));
    }
    
    // Add event listener for updates
    if (callback && typeof callback === 'function') {
      document.addEventListener('telemetry-update', callback);
    }
    
    return this;
  },
  
  // Register custom metric collection
  registerMetric: function(name, collector) {
    if (typeof collector !== 'function') {
      console.error('Metric collector must be a function');
      return this;
    }
    
    this.customMetrics[name] = collector;
    console.log(`Registered custom metric: ${name}`);
    return this;
  },
  
  // Get current value for a metric
  getValue: function(metricName) {
    const metric = this.metrics[metricName];
    return metric ? metric.current : null;
  },
  
  // Get history for a metric
  getHistory: function(metricName) {
    const metric = this.metrics[metricName];
    return metric ? metric.history : [];
  },
  
  // Get statistics for a metric
  getStats: function(metricName) {
    const metric = this.metrics[metricName];
    if (!metric) return null;
    
    return {
      current: metric.current,
      min: metric.min,
      max: metric.max,
      avg: metric.avg,
      count: metric.count
    };
  },
  
  // Visualization helpers
  visualize: {
    gauge: function(elementId, metricName, options = {}) {
      const element = document.getElementById(elementId);
      if (!element) {
        console.error(`Element not found: ${elementId}`);
        return;
      }
      
      // Default options
      const defaults = {
        min: 0,
        max: 100,
        units: '%',
        colors: {
          normal: '#2ecc71',
          warning: '#f39c12',
          danger: '#e74c3c'
        },
        thresholds: {
          warning: 70,
          danger: 90
        }
      };
      
      const config = {...defaults, ...options};
      
      // Update gauge when telemetry is updated
      const updateGauge = (event) => {
        const metrics = event.detail.metrics;
        if (!metrics || !metrics[metricName]) return;
        
        const value = metrics[metricName];
        
        // Determine color based on thresholds
        let color = config.colors.normal;
        if (value >= config.thresholds.danger) {
          color = config.colors.danger;
        } else if (value >= config.thresholds.warning) {
          color = config.colors.warning;
        }
        
        // Update gauge HTML
        element.innerHTML = `
          <div class="gauge-value" style="color: ${color}">
            ${value.toFixed(1)}${config.units}
          </div>
          <div class="gauge-progress-container">
            <div class="gauge-progress" style="width: ${Math.min(100, Math.max(0, value / config.max * 100))}%; background-color: ${color}"></div>
          </div>
        `;
      };
      
      // Listen for telemetry updates
      document.addEventListener('telemetry-update', updateGauge);
      
      return {
        destroy: () => {
          document.removeEventListener('telemetry-update', updateGauge);
        }
      };
    },
    
    chart: function(elementId, metricName, options = {}) {
      const element = document.getElementById(elementId);
      if (!element) {
        console.error(`Element not found: ${elementId}`);
        return;
      }
      
      console.log(`Creating chart for ${metricName} in ${elementId}`);
      
      // This is a placeholder - in a real implementation, this would use
      // a charting library like Chart.js to create an actual chart
      element.innerHTML = `<div class="chart-placeholder">Chart for ${metricName} (placeholder)</div>`;
      
      return {
        destroy: () => {
          // Clean up any resources
        }
      };
    },
  },
  
  // Anomaly detection
  anomaly: {
    thresholds: {
      'system.cpu': {warning: 70, danger: 90},
      'system.memory': {warning: 80, danger: 95}
    },
    
    // Register custom thresholds for a metric
    registerThresholds: function(metricName, thresholds) {
      this.thresholds[metricName] = thresholds;
      return TelemetrySystem;
    },
    
    // Check if a metric value exceeds thresholds
    checkThresholds: function(metricName, value) {
      const thresholds = this.thresholds[metricName];
      if (!thresholds) return false;
      
      if (value >= thresholds.danger) {
        this.triggerAlert(metricName, 'danger', value);
        return true;
      } else if (value >= thresholds.warning) {
        this.triggerAlert(metricName, 'warning', value);
        return true;
      }
      
      return false;
    },
    
    // Trigger an alert for an anomaly
    triggerAlert: function(metricName, level, value) {
      console.log(`[${level.toUpperCase()}] Anomaly detected for ${metricName}: ${value}`);
      
      // Create and dispatch an event
      const event = new CustomEvent('telemetry-anomaly', {
        detail: {
          metric: metricName,
          level: level,
          value: value,
          timestamp: Date.now()
        }
      });
      document.dispatchEvent(event);
    },
    
    // Detect patterns in historical data (placeholder)
    detectPatterns: function(metricName) {
      // This would be implemented in a more advanced version
      console.log(`Pattern detection for ${metricName} not implemented yet`);
    }
  },
  
  // Data export functions
  export: {
    csv: function(metricNames, timeRange) {
      if (!metricNames || !Array.isArray(metricNames)) {
        console.error('Must provide an array of metric names to export');
        return null;
      }
      
      let csv = 'timestamp,' + metricNames.join(',') + '\n';
      
      // This is a simplified implementation - a real one would handle time ranges properly
      const data = metricNames.map(name => TelemetrySystem.getHistory(name));
      
      // Only proceed if we have data
      if (data.length === 0 || data.some(d => d.length === 0)) {
        return 'No data available for export';
      }
      
      // Combine data from all metrics
      const timestamps = {};
      data.forEach((metricData, index) => {
        metricData.forEach(point => {
          if (!timestamps[point.timestamp]) {
            timestamps[point.timestamp] = new Array(metricNames.length).fill('');
          }
          timestamps[point.timestamp][index] = point.value;
        });
      });
      
      // Create CSV rows
      Object.entries(timestamps)
        .sort(([a], [b]) => parseInt(a) - parseInt(b))
        .forEach(([timestamp, values]) => {
          const date = new Date(parseInt(timestamp));
          csv += `${date.toISOString()},${values.join(',')}\n`;
        });
      
      return csv;
    },
    
    json: function(metricNames, timeRange) {
      if (!metricNames || !Array.isArray(metricNames)) {
        console.error('Must provide an array of metric names to export');
        return null;
      }
      
      const result = {
        metrics: {},
        timeRange: timeRange || { start: null, end: null }
      };
      
      metricNames.forEach(name => {
        const metric = TelemetrySystem.metrics[name];
        if (metric) {
          result.metrics[name] = {
            current: metric.current,
            history: metric.history,
            stats: {
              min: metric.min,
              max: metric.max,
              avg: metric.avg
            }
          };
        }
      });
      
      return JSON.stringify(result);
    }
  }
};

// Add some CSS for visualizations
(function() {
  const style = document.createElement('style');
  style.textContent = `
    .gauge-value {
      font-size: 1.5rem;
      font-weight: bold;
      text-align: center;
    }
    .gauge-progress-container {
      height: 6px;
      width: 100%;
      background-color: #eee;
      border-radius: 3px;
      margin-top: 5px;
      overflow: hidden;
    }
    .gauge-progress {
      height: 100%;
      transition: width 0.3s ease, background-color 0.3s ease;
    }
    .chart-placeholder {
      background-color: #f5f5f5;
      border: 1px dashed #ccc;
      padding: 20px;
      text-align: center;
      color: #999;
      font-style: italic;
    }
  `;
  document.head.appendChild(style);
})();

// Export TelemetrySystem to the global scope
window.TelemetrySystem = TelemetrySystem;
