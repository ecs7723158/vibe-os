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

const (
	writeWait      = 10 * time.Second
	pongWait       = 60 * time.Second
	pingPeriod     = (pongWait * 9) / 10
	maxMessageSize = 512 * 1024
)

// AgentStatusPayload structure received from Python agent
type AgentStatusPayload struct {
	AgentName  string `json:"agent_name"`
	Status     string `json:"status"`
	LogMessage string `json:"log_message"`
	Timestamp  string `json:"timestamp,omitempty"`
}

// Hub manages active WebSocket client connections safely
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
	ticker := time.NewTicker(pingPeriod)
	defer ticker.Stop()

	for {
		select {
		case conn := <-h.register:
			h.mutex.Lock()
			h.clients[conn] = true
			h.mutex.Unlock()
			log.Printf("[Hub] Client connected. Total active clients: %d", len(h.clients))

			welcome := AgentStatusPayload{
				AgentName:  "SystemGateway",
				Status:     "CONNECTED",
				LogMessage: "Connected to Go WebSocket Gateway on ws://localhost:8080/ws/client",
				Timestamp:  time.Now().Format(time.RFC3339),
			}
			data, _ := json.Marshal(welcome)
			conn.SetWriteDeadline(time.Now().Add(writeWait))
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
				conn.SetWriteDeadline(time.Now().Add(writeWait))
				err := conn.WriteMessage(websocket.TextMessage, data)
				if err != nil {
					log.Printf("[Hub] Write error to client: %v. Closing connection.", err)
					conn.Close()
					delete(h.clients, conn)
				}
			}
			h.mutex.RUnlock()

		case <-ticker.C:
			// Heartbeat ticker to keep connections alive & prune dead sockets
			h.mutex.Lock()
			for conn := range h.clients {
				conn.SetWriteDeadline(time.Now().Add(writeWait))
				if err := conn.WriteMessage(websocket.PingMessage, nil); err != nil {
					log.Printf("[Hub Heartbeat] Ping failed for client: %v. Cleaning up.", err)
					conn.Close()
					delete(h.clients, conn)
				}
			}
			h.mutex.Unlock()
		}
	}
}

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true
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

	http.HandleFunc("/ws/client", func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("[WebSocket Upgrade Error]: %v", err)
			return
		}

		conn.SetReadLimit(maxMessageSize)
		conn.SetReadDeadline(time.Now().Add(pongWait))
		conn.SetPongHandler(func(string) error {
			conn.SetReadDeadline(time.Now().Add(pongWait))
			return nil
		})

		hub.register <- conn

		go func() {
			defer func() {
				hub.unregister <- conn
			}()
			for {
				_, _, err := conn.ReadMessage()
				if err != nil {
					if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
						log.Printf("[WebSocket Close Error]: %v", err)
					}
					break
				}
			}
		}()
	})

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

		log.Printf("[AgentHook] Payload [%s - %s]: %s", payload.AgentName, payload.Status, payload.LogMessage)

		hub.broadcast <- payload

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "Status hook broadcasted successfully",
		})
	})

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		enableCORS(&w)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status": "ok",
			"service": "backend-go-websocket-gateway",
			"timestamp": time.Now().Format(time.RFC3339),
		})
	})

	port := ":8080"
	log.Printf("==================================================")
	log.Printf("   Go WebSocket Gateway running on port %s", port)
	log.Printf("   WebSocket:  ws://localhost%s/ws/client", port)
	log.Printf("   Agent Hook: http://localhost%s/api/agent-hook", port)
	log.Printf("==================================================")

	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
