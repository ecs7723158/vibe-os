package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// AgentStatusHook payload structure received from Python agent
type AgentStatusPayload struct {
	AgentName  string `json:"agent_name"`
	Status     string `json:"status"`
	LogMessage string `json:"log_message"`
	Timestamp  string `json:"timestamp,omitempty"`
}

// Hub manages active WebSocket client connections
type Hub struct {
	clients    map[*websocket.Conn]bool
	broadcast  chan AgentStatusPayload
	register   chan *websocket.Conn
	unregister chan *websocket.Conn
	mutex      sync.RWMutex
}

func newHub() *Hub {
	return &Hub{
		clients:    make(map[*websocket.Conn]bool),
		broadcast:  make(chan AgentStatusPayload, 100),
		register:   make(chan *websocket.Conn),
		unregister: make(chan *websocket.Conn),
	}
}

func (h *Hub) run() {
	for {
		select {
		case conn := <-h.register:
			h.mutex.Lock()
			h.clients[conn] = true
			h.mutex.Unlock()
			log.Printf("[Hub] Client connected. Total active clients: %d", len(h.clients))

			// Send welcome message to newly connected client
			welcome := AgentStatusPayload{
				AgentName:  "SystemGateway",
				Status:     "CONNECTED",
				LogMessage: "Connected to Go WebSocket Gateway on ws://localhost:8080/ws/client",
				Timestamp:  time.Now().Format(time.RFC3339),
			}
			data, _ := json.Marshal(welcome)
			conn.WriteMessage(websocket.TextMessage, data)

		case conn := <-h.unregister:
			h.mutex.Lock()
			if _, ok := h.clients[conn]; ok {
				delete(h.clients, conn)
				conn.Close()
				log.Printf("[Hub] Client disconnected. Remaining clients: %d", len(h.clients))
			}
			h.mutex.Unlock()

		case payload := <-h.broadcast:
			if payload.Timestamp == "" {
				payload.Timestamp = time.Now().Format(time.RFC3339)
			}
			data, err := json.Marshal(payload)
			if err != nil {
				log.Printf("[Hub] Error marshaling payload: %v", err)
				continue
			}

			h.mutex.RLock()
			for conn := range h.clients {
				err := conn.WriteMessage(websocket.TextMessage, data)
				if err != nil {
					log.Printf("[Hub] Error writing to client: %v. Closing connection.", err)
					conn.Close()
					delete(h.clients, conn)
				}
			}
			h.mutex.RUnlock()
		}
	}
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all cross-origin requests for local dev
	},
}

func enableCORS(w *http.ResponseWriter) {
	(*w).Header().Set("Access-Control-Allow-Origin", "*")
	(*w).Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
	(*w).Header().Set("Access-Control-Allow-Headers", "Content-Type")
}

func main() {
	hub := newHub()
	go hub.run()

	// WebSocket handler for web clients
	http.HandleFunc("/ws/client", func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("[WebSocket] Upgrade error: %v", err)
			return
		}

		hub.register <- conn

		// Read pump to detect disconnection
		go func() {
			defer func() {
				hub.unregister <- conn
			}()
			for {
				_, _, err := conn.ReadMessage()
				if err != nil {
					break
				}
			}
		}()
	})

	// REST API endpoint for Python Agent to push status logs
	http.HandleFunc("/api/agent-hook", func(w http.ResponseWriter, r *http.Request) {
		enableCORS(&w)

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}

		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "Failed to read request body", http.StatusBadRequest)
			return
		}
		defer r.Body.Close()

		var payload AgentStatusPayload
		if err := json.Unmarshal(body, &payload); err != nil {
			http.Error(w, fmt.Sprintf("Invalid JSON payload: %v", err), http.StatusBadRequest)
			return
		}

		if payload.Timestamp == "" {
			payload.Timestamp = time.Now().Format(time.RFC3339)
		}

		log.Printf("[AgentHook] Broadcast payload from %s [%s]: %s", payload.AgentName, payload.Status, payload.LogMessage)

		// Broadcast to all WebSocket clients
		hub.broadcast <- payload

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "Hook received and broadcasted",
		})
	})

	// Health check endpoint
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		enableCORS(&w)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"status": "ok",
			"service": "backend-go-websocket-gateway",
		})
	})

	port := ":8080"
	log.Printf("==================================================")
	log.Printf("   Go WebSocket Gateway starting on port %s", port)
	log.Printf("   WebSocket Endpoint: ws://localhost%s/ws/client", port)
	log.Printf("   Agent Hook Endpoint: http://localhost%s/api/agent-hook", port)
	log.Printf("==================================================")

	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
