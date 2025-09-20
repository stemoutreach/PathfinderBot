/**
 * PathfinderBot Main Application Script
 * 
 * This script initializes the web interface and connects to the WebSocket server.
 * It implements performance optimizations and responsive UI updates.
 */

// Performance optimization: Use requestAnimationFrame for smooth animations
window.requestAnimationFrame = window.requestAnimationFrame || 
                              window.webkitRequestAnimationFrame || 
                              window.mozRequestAnimationFrame;

// Configuration
const config = {
    // WebSocket server URL, automatically determine based on current location
    wsUrl: `ws://${window.location.hostname}:8765`,
    
    // Update intervals
    controlUpdateInterval: 100,    // 10 Hz for controls
    telemetryUpdateInterval: 500,  // 2 Hz for telemetry updates
    
    // Connection parameters
    reconnectInterval: 2000,       // 2 seconds between reconnect attempts
    maxReconnectAttempts: 10,      // Maximum reconnect attempts
    
    // UI configuration
    uiThrottleTime: 16,            // ~60fps for UI updates
    
    // Debug options
    debug: false,                  // Enable debug logging
};

// Cached DOM elements for performance
let domCache = {};

// Store for application state
const appState = {
    connected: false,
    controlsEnabled: false,
    telemetryEnabled: true,
    lastTelemetry: null,
    performance: {
        cpu: 0,
        memory: 0,
        latency: 0
    },
};

/**
 * Initializes the application
 */
function initializeApp() {
    console.log('Initializing PathfinderBot Web Interface...');
    
    // Cache DOM elements
    cacheElements();
    
    // Initialize WebSocket connection
    initWebSocket();
    
    // Initialize performance monitor
    initPerformanceMonitor();
    
    // Initialize event listeners
    initEventListeners();
    
    // Setup visibility change handling for better resource management
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    console.log('Initialization complete.');
}

/**
 * Cache frequently accessed DOM elements for performance
 */
function cacheElements() {
    const elements = [
        'status-indicator',
        'connection-status',
        'control-panel',
        'telemetry-panel',
        'performance-monitor',
        'map-container',
        'camera-feed'
    ];
    
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            domCache[id] = element;
        }
    });
}

/**
 * Initialize WebSocket connection
 */
function initWebSocket() {
    // Create WebSocket client
    window.wsClient = new WebSocketClient(config.wsUrl, {
        reconnectInterval: config.reconnectInterval,
        maxReconnectAttempts: config.maxReconnectAttempts,
        pingInterval: 30000,
        debug: config.debug
    });
    
    // Add event listeners
    wsClient.on('connect', () => {
        console.log('Connected to WebSocket server');
        appState.connected = true;
        updateConnectionStatus(true);
        
        // Start telemetry after connection
        if (appState.telemetryEnabled) {
            wsClient.send({
                command: 'start_telemetry',
                interval: config.telemetryUpdateInterval / 1000
            });
        }
    });
    
    wsClient.on('disconnect', () => {
        console.log('Disconnected from WebSocket server');
        appState.connected = false;
        updateConnectionStatus(false);
    });
    
    wsClient.on('reconnecting', (data) => {
        console.log(`Reconnecting... Attempt ${data.attempt}`);
        updateConnectionStatus(false, `Reconnecting (${data.attempt})`);
    });
    
    wsClient.on('error', (error) => {
        console.error('WebSocket error:', error);
    });
    
    // Register message handlers
    wsClient.registerHandler('telemetry', handleTelemetry);
    
    // Connect to the server
    wsClient.connect().catch(error => {
        console.error('Failed to connect:', error);
    });
}

/**
 * Initialize performance monitor
 */
function initPerformanceMonitor() {
    if (domCache['performance-monitor']) {
        window.perfMonitor = new PerformanceMonitor({
            containerId: 'performance-monitor',
            updateInterval: 1000,
            autoStart: true,
            wsClient: wsClient
        });
    }
}

/**
 * Initialize event listeners for UI controls
 */
function initEventListeners() {
    // Example: Control buttons
    const controlButtons = document.querySelectorAll('.control-button');
    controlButtons.forEach(button => {
        button.addEventListener('click', handleControlButton);
    });
    
    // Example: Range inputs
    const rangeInputs = document.querySelectorAll('input[type="range"]');
    rangeInputs.forEach(input => {
        input.addEventListener('input', throttle(handleRangeInput, config.uiThrottleTime));
    });
    
    // Enable/disable telemetry toggle
    const telemetryToggle = document.getElementById('telemetry-toggle');
    if (telemetryToggle) {
        telemetryToggle.addEventListener('change', handleTelemetryToggle);
    }
}

/**
 * Handle telemetry toggle
 */
function handleTelemetryToggle(event) {
    const enabled = event.target.checked;
    appState.telemetryEnabled = enabled;
    
    if (wsClient && wsClient.isConnected) {
        if (enabled) {
            wsClient.send({
                command: 'start_telemetry',
                interval: config.telemetryUpdateInterval / 1000
            });
        } else {
            wsClient.send({
                command: 'stop_telemetry'
            });
        }
    }
}

/**
 * Handle control button clicks
 */
function handleControlButton(event) {
    const button = event.currentTarget;
    const action = button.dataset.action;
    
    if (!action) return;
    
    // Handle different actions
    switch (action) {
        case 'move-forward':
            sendMoveCommand(1, 0, 0);
            break;
        case 'move-backward':
            sendMoveCommand(-1, 0, 0);
            break;
        case 'turn-left':
            sendMoveCommand(0, 0, -1);
            break;
        case 'turn-right':
            sendMoveCommand(0, 0, 1);
            break;
        case 'stop':
            sendStopCommand();
            break;
        case 'set-goal':
            const goalX = parseFloat(document.getElementById('goal-x').value || 0);
            const goalY = parseFloat(document.getElementById('goal-y').value || 0);
            sendGoalCommand(goalX, goalY);
            break;
        case 'cancel-navigation':
            sendCancelNavigationCommand();
            break;
        case 'clear-queue':
            sendClearQueueCommand();
            break;
    }
}

/**
 * Handle range input changes (throttled)
 */
function handleRangeInput(event) {
    const input = event.target;
    const value = parseFloat(input.value);
    const controlType = input.dataset.control;
    
    if (!controlType) return;
    
    // Update visual feedback immediately
    const valueDisplay = document.getElementById(`${input.id}-value`);
    if (valueDisplay) {
        valueDisplay.textContent = value.toFixed(1);
    }
    
    // Send command based on control type
    switch (controlType) {
        case 'speed':
            appState.speed = value;
            updateMovement();
            break;
        case 'rotation':
            appState.rotation = value;
            updateMovement();
            break;
    }
}

/**
 * Update movement based on current control state
 */
function updateMovement() {
    if (appState.speed !== undefined && appState.rotation !== undefined) {
        sendMoveCommand(appState.speed, 0, appState.rotation);
    }
}

/**
 * Send movement command to the server
 */
function sendMoveCommand(x, y, rotation) {
    if (wsClient && wsClient.isConnected) {
        wsClient.send({
            command: 'move',
            x: x,
            y: y,
            rotation: rotation
        });
    }
}

/**
 * Send stop command to the server
 */
function sendStopCommand() {
    if (wsClient && wsClient.isConnected) {
        wsClient.send({
            command: 'stop'
        });
    }
}

/**
 * Send goal command to the server
 */
function sendGoalCommand(x, y) {
    if (wsClient && wsClient.isConnected) {
        wsClient.send({
            command: 'set_goal',
            x: x,
            y: y
        });
    }
}

/**
 * Send cancel navigation command
 */
function sendCancelNavigationCommand() {
    if (wsClient && wsClient.isConnected) {
        wsClient.send({
            command: 'cancel_navigation'
        });
    }
}

/**
 * Send clear queue command
 */
function sendClearQueueCommand() {
    if (wsClient && wsClient.isConnected) {
        wsClient.send({
            command: 'clear_queue'
        });
    }
}

/**
 * Handle telemetry data from server
 */
function handleTelemetry(data) {
    appState.lastTelemetry = data;
    
    // Update UI elements based on telemetry data
    updateTelemetryDisplay(data);
}

/**
 * Update connection status in UI
 */
function updateConnectionStatus(connected, statusText = null) {
    const statusIndicator = domCache['status-indicator'];
    const connectionStatus = domCache['connection-status'];
    
    if (statusIndicator) {
        statusIndicator.className = connected ? 'status connected' : 'status disconnected';
    }
    
    if (connectionStatus) {
        connectionStatus.textContent = statusText || (connected ? 'Connected' : 'Disconnected');
    }
    
    // Update control panel state
    const controlPanel = domCache['control-panel'];
    if (controlPanel) {
        controlPanel.classList.toggle('disabled', !connected);
    }
}

/**
 * Update telemetry display
 */
function updateTelemetryDisplay(data) {
    if (!data || !data.data) return;
    
    const telemetryPanel = domCache['telemetry-panel'];
    if (!telemetryPanel) return;
    
    const telemetryData = data.data;
    
    // Update system information
    if (telemetryData.system) {
        updateSystemInfo(telemetryData.system);
    }
    
    // Update pose information
    if (telemetryData.pose) {
        updatePoseInfo(telemetryData.pose);
    }
    
    // Update navigation information
    if (telemetryData.navigation) {
        updateNavigationInfo(telemetryData.navigation);
    }
    
    // Update sensor information
    if (telemetryData.sensors) {
        updateSensorInfo(telemetryData.sensors);
    }
}

/**
 * Update system information display
 */
function updateSystemInfo(systemData) {
    const cpuUsage = document.getElementById('cpu-usage');
    const memoryUsage = document.getElementById('memory-usage');
    
    if (cpuUsage && systemData.cpu_usage !== undefined) {
        cpuUsage.textContent = `${systemData.cpu_usage.toFixed(1)}%`;
        appState.performance.cpu = systemData.cpu_usage;
    }
    
    if (memoryUsage && systemData.memory_usage !== undefined) {
        memoryUsage.textContent = `${systemData.memory_usage.toFixed(1)}%`;
        appState.performance.memory = systemData.memory_usage;
    }
}

/**
 * Update pose information display
 */
function updatePoseInfo(poseData) {
    const poseX = document.getElementById('pose-x');
    const poseY = document.getElementById('pose-y');
    const poseTheta = document.getElementById('pose-theta');
    
    if (poseX) poseX.textContent = poseData.x.toFixed(2);
    if (poseY) poseY.textContent = poseData.y.toFixed(2);
    if (poseTheta) poseTheta.textContent = poseData.theta.toFixed(2);
}

/**
 * Update navigation information display
 */
function updateNavigationInfo(navData) {
    const navStatus = document.getElementById('nav-status');
    const goalX = document.getElementById('current-goal-x');
    const goalY = document.getElementById('current-goal-y');
    const distToGoal = document.getElementById('distance-to-goal');
    
    if (navStatus) navStatus.textContent = navData.status || 'IDLE';
    
    if (navData.goal) {
        if (goalX) goalX.textContent = navData.goal.x.toFixed(2);
        if (goalY) goalY.textContent = navData.goal.y.toFixed(2);
    }
    
    if (distToGoal && navData.distance_to_goal !== undefined) {
        distToGoal.textContent = navData.distance_to_goal.toFixed(2);
    }
}

/**
 * Update sensor information display
 */
function updateSensorInfo(sensorData) {
    // Implement based on available sensor data
}

/**
 * Handle document visibility change for better resource management
 */
function handleVisibilityChange() {
    if (document.hidden) {
        // Document is hidden, reduce update rate to save resources
        if (wsClient && wsClient.isConnected && appState.telemetryEnabled) {
            wsClient.send({
                command: 'set_telemetry_interval',
                interval: 2.0  // Reduce to 0.5 Hz when page is not visible
            });
        }
    } else {
        // Document is visible again, restore normal update rate
        if (wsClient && wsClient.isConnected && appState.telemetryEnabled) {
            wsClient.send({
                command: 'set_telemetry_interval',
                interval: config.telemetryUpdateInterval / 1000
            });
        }
    }
}

/**
 * Creates a throttled function that only invokes the provided function
 * at most once per specified interval
 */
function throttle(func, wait) {
    let lastCall = 0;
    return function(...args) {
        const now = Date.now();
        if (now - lastCall >= wait) {
            lastCall = now;
            return func.apply(this, args);
        }
    };
}

// Initialize the application when the document is fully loaded
document.addEventListener('DOMContentLoaded', initializeApp);
