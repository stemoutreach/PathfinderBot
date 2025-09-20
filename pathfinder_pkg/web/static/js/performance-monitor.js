/**
 * PathfinderBot Performance Monitor
 * 
 * A lightweight, efficient dashboard for monitoring robot performance metrics.
 * Features throttled updates, efficient DOM manipulation, and minimal layout shifts.
 */

class PerformanceMonitor {
    /**
     * Creates a new performance monitor
     * 
     * @param {Object} options - Configuration options
     * @param {string} options.containerId - The ID of the container element
     * @param {number} options.updateInterval - Update interval in milliseconds
     * @param {boolean} options.autoStart - Whether to start monitoring automatically
     * @param {WebSocketClient} options.wsClient - WebSocket client instance
     */
    constructor(options = {}) {
        this.options = {
            containerId: options.containerId || 'performance-monitor',
            updateInterval: options.updateInterval || 1000,
            autoStart: options.autoStart !== undefined ? options.autoStart : true,
            wsClient: options.wsClient || null,
        };
        
        this.metrics = {
            cpu: {
                current: 0,
                history: new Array(60).fill(0),
                min: 0,
                max: 0,
                avg: 0
            },
            memory: {
                current: 0,
                history: new Array(60).fill(0),
                min: 0, 
                max: 0,
                avg: 0
            },
            latency: {
                current: 0,
                history: new Array(60).fill(0),
                min: 0,
                max: 0,
                avg: 0
            },
            battery: {
                level: 100,
                charging: false,
                timeRemaining: null
            }
        };
        
        this.updateTimer = null;
        this.initialized = false;
        this.lastUpdateTime = 0;
        
        // Create DOM elements on initialization
        if (this.options.autoStart) {
            this.init();
        }
        
        // Connect WebSocket events if client provided
        if (this.options.wsClient) {
            this.connectWebSocketEvents();
        }
    }
    
    /**
     * Initializes the performance monitor
     */
    init() {
        if (this.initialized) return;
        
        // Get container element
        this.container = document.getElementById(this.options.containerId);
        if (!this.container) {
            console.error(`[PerformanceMonitor] Container element with ID '${this.options.containerId}' not found.`);
            return;
        }
        
        this.createDOMStructure();
        this.initialized = true;
        
        if (this.options.autoStart) {
            this.start();
        }
    }
    
    /**
     * Connects WebSocket events
     * 
     * @private
     */
    connectWebSocketEvents() {
        if (!this.options.wsClient) return;
        
        const wsClient = this.options.wsClient;
        
        // Listen for telemetry data
        wsClient.registerHandler('telemetry', (data) => {
            this.updateMetricsFromTelemetry(data);
        });
        
        // Listen for latency updates
        wsClient.on('latency', (data) => {
            this.updateMetric('latency', data.latency);
        });
    }
    
    /**
     * Creates the DOM structure for the performance monitor
     * 
     * @private
     */
    createDOMStructure() {
        // Clear container
        this.container.innerHTML = '';
        this.container.classList.add('performance-monitor');
        
        // Create header
        const header = document.createElement('div');
        header.className = 'monitor-header';
        header.innerHTML = '<h3>System Performance</h3>';
        this.container.appendChild(header);
        
        // Create metric sections
        this.createMetricSection('cpu', 'CPU Usage', '%');
        this.createMetricSection('memory', 'Memory Usage', '%');
        this.createMetricSection('latency', 'Network Latency', 'ms');
        
        // Create battery section
        const batterySection = document.createElement('div');
        batterySection.className = 'metric-section battery-section';
        batterySection.innerHTML = `
            <div class="metric-header">
                <span class="metric-title">Battery</span>
                <span class="metric-value" id="battery-value">100%</span>
            </div>
            <div class="battery-indicator">
                <div class="battery-level" id="battery-level" style="width: 100%"></div>
            </div>
            <div class="battery-status">
                <span id="battery-status">Charging</span>
                <span id="battery-time-remaining"></span>
            </div>
        `;
        this.container.appendChild(batterySection);
        
        // Create mini charts container
        const chartsContainer = document.createElement('div');
        chartsContainer.className = 'mini-charts-container';
        this.container.appendChild(chartsContainer);
        
        // Create connection status indicator
        const connectionStatus = document.createElement('div');
        connectionStatus.className = 'connection-status';
        connectionStatus.innerHTML = `
            <span class="status-dot connected" id="connection-indicator"></span>
            <span id="connection-status">Connected</span>
        `;
        this.container.appendChild(connectionStatus);
        
        // Set initial values
        this.updateAllDisplays();
    }
    
    /**
     * Creates a metric section in the DOM
     * 
     * @private
     * @param {string} id - The metric ID
     * @param {string} title - The metric title
     * @param {string} unit - The metric unit
     */
    createMetricSection(id, title, unit) {
        const section = document.createElement('div');
        section.className = 'metric-section';
        section.innerHTML = `
            <div class="metric-header">
                <span class="metric-title">${title}</span>
                <span class="metric-value" id="${id}-value">0${unit}</span>
            </div>
            <div class="metric-bar-container">
                <div class="metric-bar" id="${id}-bar" style="width: 0%"></div>
            </div>
            <div class="metric-details">
                <span>Min: <span id="${id}-min">0${unit}</span></span>
                <span>Avg: <span id="${id}-avg">0${unit}</span></span>
                <span>Max: <span id="${id}-max">0${unit}</span></span>
            </div>
        `;
        this.container.appendChild(section);
    }
    
    /**
     * Updates a specific metric
     * 
     * @param {string} metricName - The name of the metric to update
     * @param {number} value - The new value
     * @param {Object} additionalData - Additional data for the metric
     */
    updateMetric(metricName, value, additionalData = {}) {
        if (!this.metrics[metricName]) return;
        
        const metric = this.metrics[metricName];
        
        // Update current value
        metric.current = value;
        
        // Update history (shift left and add new value at the end)
        metric.history.shift();
        metric.history.push(value);
        
        // Update min/max/avg
        const nonZeroValues = metric.history.filter(v => v > 0);
        metric.min = nonZeroValues.length ? Math.min(...nonZeroValues) : 0;
        metric.max = Math.max(...metric.history);
        const sum = metric.history.reduce((a, b) => a + b, 0);
        metric.avg = nonZeroValues.length ? sum / nonZeroValues.length : 0;
        
        // Handle additional data
        if (additionalData) {
            Object.assign(metric, additionalData);
        }
        
        // Update display if initialized
        if (this.initialized) {
            this.updateMetricDisplay(metricName);
        }
    }
    
    /**
     * Updates battery information
     * 
     * @param {Object} batteryData - Battery data
     * @param {number} batteryData.level - Battery level (0-100)
     * @param {boolean} batteryData.charging - Whether the battery is charging
     * @param {number|null} batteryData.timeRemaining - Time remaining in minutes, or null
     */
    updateBattery(batteryData) {
        if (!batteryData) return;
        
        this.metrics.battery = {
            ...this.metrics.battery,
            ...batteryData
        };
        
        if (this.initialized) {
            this.updateBatteryDisplay();
        }
    }
    
    /**
     * Updates metrics from telemetry data
     * 
     * @param {Object} telemetryData - Telemetry data from the server
     */
    updateMetricsFromTelemetry(telemetryData) {
        if (!telemetryData || !telemetryData.data) return;
        
        const data = telemetryData.data;
        
        // Update CPU and memory if available in system metrics
        if (data.system) {
            if (data.system.cpu_usage !== undefined) {
                this.updateMetric('cpu', data.system.cpu_usage);
            }
            
            if (data.system.memory_usage !== undefined) {
                this.updateMetric('memory', data.system.memory_usage);
            }
        }
        
        // Update battery if available
        if (data.battery) {
            this.updateBattery({
                level: data.battery.level || this.metrics.battery.level,
                charging: data.battery.charging || false,
                timeRemaining: data.battery.timeRemaining || null
            });
        }
        
        // Update connection status
        this.updateConnectionStatus(true);
    }
    
    /**
     * Updates the connection status display
     * 
     * @param {boolean} connected - Whether there is an active connection
     */
    updateConnectionStatus(connected) {
        if (!this.initialized) return;
        
        const indicator = document.getElementById('connection-indicator');
        const statusText = document.getElementById('connection-status');
        
        if (indicator && statusText) {
            if (connected) {
                indicator.className = 'status-dot connected';
                statusText.textContent = 'Connected';
            } else {
                indicator.className = 'status-dot disconnected';
                statusText.textContent = 'Disconnected';
            }
        }
    }
    
    /**
     * Updates the display for a specific metric
     * 
     * @private
     * @param {string} metricName - The name of the metric to update
     */
    updateMetricDisplay(metricName) {
        if (!this.initialized) return;
        
        const metric = this.metrics[metricName];
        let unit = '';
        
        switch (metricName) {
            case 'cpu':
            case 'memory':
                unit = '%';
                break;
            case 'latency':
                unit = 'ms';
                break;
        }
        
        // Update value display
        const valueElement = document.getElementById(`${metricName}-value`);
        if (valueElement) {
            valueElement.textContent = `${Math.round(metric.current)}${unit}`;
        }
        
        // Update bar width
        const barElement = document.getElementById(`${metricName}-bar`);
        if (barElement) {
            // Calculate width based on metric type
            let width = 0;
            switch (metricName) {
                case 'cpu':
                case 'memory':
                    width = Math.min(100, Math.max(0, metric.current));
                    break;
                case 'latency':
                    // Scale latency: 0-1000ms maps to 0-100%
                    width = Math.min(100, Math.max(0, metric.current / 10));
                    break;
            }
            
            barElement.style.width = `${width}%`;
            
            // Update bar color based on value
            if (width < 60) {
                barElement.className = 'metric-bar good';
            } else if (width < 80) {
                barElement.className = 'metric-bar warning';
            } else {
                barElement.className = 'metric-bar critical';
            }
        }
        
        // Update min/avg/max
        const minElement = document.getElementById(`${metricName}-min`);
        const avgElement = document.getElementById(`${metricName}-avg`);
        const maxElement = document.getElementById(`${metricName}-max`);
        
        if (minElement && metric.min !== undefined) {
            minElement.textContent = `${Math.round(metric.min)}${unit}`;
        }
        
        if (avgElement && metric.avg !== undefined) {
            avgElement.textContent = `${Math.round(metric.avg)}${unit}`;
        }
        
        if (maxElement && metric.max !== undefined) {
            maxElement.textContent = `${Math.round(metric.max)}${unit}`;
        }
    }
    
    /**
     * Updates the battery display
     * 
     * @private
     */
    updateBatteryDisplay() {
        if (!this.initialized) return;
        
        const battery = this.metrics.battery;
        
        // Update level display and indicator
        const valueElement = document.getElementById('battery-value');
        const levelElement = document.getElementById('battery-level');
        const statusElement = document.getElementById('battery-status');
        const timeElement = document.getElementById('battery-time-remaining');
        
        if (valueElement) {
            valueElement.textContent = `${Math.round(battery.level)}%`;
        }
        
        if (levelElement) {
            levelElement.style.width = `${battery.level}%`;
            
            // Update color based on level
            if (battery.level > 50) {
                levelElement.className = 'battery-level good';
            } else if (battery.level > 20) {
                levelElement.className = 'battery-level warning';
            } else {
                levelElement.className = 'battery-level critical';
            }
        }
        
        if (statusElement) {
            statusElement.textContent = battery.charging ? 'Charging' : 'Discharging';
        }
        
        if (timeElement) {
            if (battery.timeRemaining !== null) {
                const hours = Math.floor(battery.timeRemaining / 60);
                const minutes = Math.round(battery.timeRemaining % 60);
                timeElement.textContent = `${hours}h ${minutes}m remaining`;
            } else {
                timeElement.textContent = '';
            }
        }
    }
    
    /**
     * Updates all metric displays
     * 
     * @private
     */
    updateAllDisplays() {
        if (!this.initialized) return;
        
        // Update all metric displays
        for (const metricName in this.metrics) {
            if (metricName === 'battery') {
                this.updateBatteryDisplay();
            } else {
                this.updateMetricDisplay(metricName);
            }
        }
        
        // Check WebSocket connection status
        if (this.options.wsClient) {
            this.updateConnectionStatus(this.options.wsClient.isConnected);
        }
        
        this.lastUpdateTime = Date.now();
    }
    
    /**
     * Starts the performance monitor update loop
     */
    start() {
        if (!this.initialized) {
            this.init();
        }
        
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        this.updateTimer = setInterval(() => {
            this.updateAllDisplays();
        }, this.options.updateInterval);
    }
    
    /**
     * Stops the performance monitor update loop
     */
    stop() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }
}

// Exported as both ES module and global variable
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PerformanceMonitor;
} else if (typeof define === 'function' && define.amd) {
    define([], function() { return PerformanceMonitor; });
} else {
    window.PerformanceMonitor = PerformanceMonitor;
}
