/**
 * PathfinderBot WebSocket Client
 * 
 * Optimized WebSocket client for real-time communication with the robot.
 * Implements efficient event handling, connection recovery, and performance monitoring.
 */

class WebSocketClient {
    /**
     * Creates a new WebSocket client
     * 
     * @param {string} url - The WebSocket server URL
     * @param {Object} options - Configuration options
     * @param {number} options.reconnectInterval - Interval for reconnection attempts (ms)
     * @param {number} options.maxReconnectAttempts - Maximum number of reconnection attempts
     * @param {number} options.pingInterval - Interval for sending ping messages (ms)
     * @param {boolean} options.debug - Whether to enable debug logging
     */
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            reconnectInterval: options.reconnectInterval || 1000,
            maxReconnectAttempts: options.maxReconnectAttempts || 5,
            pingInterval: options.pingInterval || 30000,
            debug: options.debug || false
        };

        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.reconnectTimer = null;
        this.pingTimer = null;
        this.eventListeners = {};
        this.messageHandlers = {};
        this.lastMessageTime = 0;
        this.latencyMeasurements = [];

        // Performance metrics
        this.metrics = {
            messagesReceived: 0,
            messagesSent: 0,
            errors: 0,
            averageLatency: 0,
            connectionDrops: 0,
            lastConnected: null
        };
    }

    /**
     * Connects to the WebSocket server
     * 
     * @returns {Promise} A promise that resolves when connected
     */
    connect() {
        return new Promise((resolve, reject) => {
            if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || 
                           this.ws.readyState === WebSocket.OPEN)) {
                this.log('Already connected or connecting');
                resolve();
                return;
            }

            // Clear any existing reconnect timer
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }

            this.log(`Connecting to ${this.url}`);
            
            try {
                this.ws = new WebSocket(this.url);

                // Setup event handlers
                this.ws.onopen = () => {
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    this.metrics.lastConnected = new Date();
                    this.log('Connected to WebSocket server');
                    
                    // Start ping interval
                    this.startPingInterval();
                    
                    // Trigger connect event
                    this.trigger('connect');
                    
                    resolve();
                };

                this.ws.onclose = (event) => {
                    this.isConnected = false;
                    this.log(`WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}`);
                    
                    // Stop ping interval
                    this.stopPingInterval();
                    
                    // Increment connection drops counter
                    this.metrics.connectionDrops++;

                    // Trigger disconnect event
                    this.trigger('disconnect', event);
                    
                    // Attempt to reconnect
                    this.scheduleReconnect();
                };

                this.ws.onmessage = (event) => {
                    this.metrics.messagesReceived++;
                    this.lastMessageTime = Date.now();
                    
                    try {
                        const data = JSON.parse(event.data);
                        
                        // Handle pong messages for latency calculation
                        if (data.command === 'pong') {
                            this.handlePong(data);
                        }
                        
                        // Call type-specific handler
                        if (data.type && this.messageHandlers[data.type]) {
                            this.messageHandlers[data.type](data);
                        }
                        
                        // Trigger message event
                        this.trigger('message', data);
                    } catch (err) {
                        this.metrics.errors++;
                        this.log(`Error parsing message: ${err.message}`, true);
                        this.trigger('error', {
                            type: 'parseError',
                            error: err,
                            data: event.data
                        });
                    }
                };

                this.ws.onerror = (error) => {
                    this.metrics.errors++;
                    this.log(`WebSocket error: ${error}`, true);
                    this.trigger('error', error);
                    reject(error);
                };
                
            } catch (error) {
                this.metrics.errors++;
                this.log(`Error creating WebSocket: ${error.message}`, true);
                this.trigger('error', error);
                this.scheduleReconnect();
                reject(error);
            }
        });
    }

    /**
     * Schedules a reconnection attempt
     * 
     * @private
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            this.log('Maximum reconnection attempts reached', true);
            this.trigger('reconnectFailed');
            return;
        }

        this.reconnectAttempts++;
        
        // Use exponential backoff
        const delay = Math.min(30000, this.options.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1));
        
        this.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        this.reconnectTimer = setTimeout(() => {
            this.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.options.maxReconnectAttempts})`);
            this.trigger('reconnecting', { attempt: this.reconnectAttempts });
            this.connect().catch(() => {
                // Error handling happens in the connect method
            });
        }, delay);
    }

    /**
     * Disconnects from the WebSocket server
     */
    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        this.stopPingInterval();
        
        if (this.ws) {
            // Remove all event handlers to avoid memory leaks
            this.ws.onopen = null;
            this.ws.onclose = null;
            this.ws.onmessage = null;
            this.ws.onerror = null;
            
            if (this.ws.readyState === WebSocket.OPEN) {
                this.ws.close(1000, 'Client disconnecting');
            }
            
            this.ws = null;
        }
        
        this.isConnected = false;
        this.log('Disconnected from WebSocket server');
        this.trigger('disconnect', { code: 1000, reason: 'Client disconnecting' });
    }

    /**
     * Sends a message to the WebSocket server
     * 
     * @param {Object} data - The data to send
     * @returns {boolean} Whether the message was sent
     */
    send(data) {
        if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.log('Cannot send message: not connected', true);
            return false;
        }
        
        try {
            const message = typeof data === 'string' ? data : JSON.stringify(data);
            this.ws.send(message);
            this.metrics.messagesSent++;
            return true;
        } catch (err) {
            this.metrics.errors++;
            this.log(`Error sending message: ${err.message}`, true);
            this.trigger('error', {
                type: 'sendError',
                error: err,
                data: data
            });
            return false;
        }
    }

    /**
     * Sends a ping message to measure latency
     * 
     * @private
     */
    sendPing() {
        if (!this.isConnected) return;
        
        const pingData = {
            command: 'ping',
            timestamp: Date.now()
        };
        
        this.send(pingData);
    }

    /**
     * Handles a pong response
     * 
     * @private
     * @param {Object} data - The pong message data
     */
    handlePong(data) {
        const now = Date.now();
        const latency = now - data.timestamp;
        
        // Store latency measurement (keep last 10 values)
        this.latencyMeasurements.push(latency);
        if (this.latencyMeasurements.length > 10) {
            this.latencyMeasurements.shift();
        }
        
        // Calculate average latency
        this.metrics.averageLatency = this.latencyMeasurements.reduce((sum, val) => sum + val, 0) / this.latencyMeasurements.length;
        
        this.log(`Latency: ${latency}ms, Average: ${this.metrics.averageLatency.toFixed(2)}ms`);
        this.trigger('latency', { 
            latency, 
            average: this.metrics.averageLatency,
            timestamp: now
        });
    }

    /**
     * Starts the ping interval
     * 
     * @private
     */
    startPingInterval() {
        this.stopPingInterval();
        this.pingTimer = setInterval(() => {
            this.sendPing();
        }, this.options.pingInterval);
    }

    /**
     * Stops the ping interval
     * 
     * @private
     */
    stopPingInterval() {
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
    }

    /**
     * Registers a handler for a specific message type
     * 
     * @param {string} type - The message type
     * @param {Function} handler - The handler function
     */
    registerHandler(type, handler) {
        if (typeof handler !== 'function') {
            throw new Error('Handler must be a function');
        }
        this.messageHandlers[type] = handler;
    }

    /**
     * Unregisters a handler for a specific message type
     * 
     * @param {string} type - The message type
     */
    unregisterHandler(type) {
        delete this.messageHandlers[type];
    }

    /**
     * Adds an event listener
     * 
     * @param {string} event - The event name
     * @param {Function} callback - The callback function
     */
    on(event, callback) {
        if (!this.eventListeners[event]) {
            this.eventListeners[event] = [];
        }
        this.eventListeners[event].push(callback);
    }

    /**
     * Removes an event listener
     * 
     * @param {string} event - The event name
     * @param {Function} callback - The callback function
     */
    off(event, callback) {
        if (!this.eventListeners[event]) return;
        
        if (callback) {
            this.eventListeners[event] = this.eventListeners[event].filter(
                cb => cb !== callback
            );
        } else {
            delete this.eventListeners[event];
        }
    }

    /**
     * Triggers an event
     * 
     * @private
     * @param {string} event - The event name
     * @param {*} data - The event data
     */
    trigger(event, data) {
        if (!this.eventListeners[event]) return;
        
        for (const callback of this.eventListeners[event]) {
            try {
                callback(data);
            } catch (err) {
                this.log(`Error in event handler (${event}): ${err.message}`, true);
            }
        }
    }

    /**
     * Gets the current WebSocket state
     * 
     * @returns {Object} The current state
     */
    getState() {
        return {
            connected: this.isConnected,
            reconnectAttempts: this.reconnectAttempts,
            metrics: { ...this.metrics },
            latency: this.metrics.averageLatency,
            lastMessage: this.lastMessageTime
        };
    }

    /**
     * Logs a message
     * 
     * @private
     * @param {string} message - The message to log
     * @param {boolean} isError - Whether this is an error message
     */
    log(message, isError = false) {
        if (!this.options.debug && !isError) return;
        
        const timestamp = new Date().toISOString();
        const logMsg = `[WebSocketClient] ${timestamp} - ${message}`;
        
        if (isError) {
            console.error(logMsg);
        } else {
            console.log(logMsg);
        }
    }
}

// Exported as both ES module and global variable
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketClient;
} else if (typeof define === 'function' && define.amd) {
    define([], function() { return WebSocketClient; });
} else {
    window.WebSocketClient = WebSocketClient;
}
