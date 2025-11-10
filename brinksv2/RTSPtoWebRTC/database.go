package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	_ "github.com/lib/pq"
)

// Database configuration - connects to the same database as the FastAPI backend
const (
	DBHost     = "149.200.251.12"
	DBPort     = 5432
	DBUser     = "husain"
	DBPassword = "tt55oo77"
	DBName     = "razz"
)

// Camera represents a camera from the database
type Camera struct {
	ID        int
	Name      string
	RtspMain  string
	RtspSub   string
	Location  string
	CreatedAt time.Time
	UpdatedAt sql.NullTime
}

// LoadCamerasFromDB loads cameras from PostgreSQL and updates the config
func LoadCamerasFromDB() error {
	// Connection string
	connStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		DBHost, DBPort, DBUser, DBPassword, DBName)

	// Connect to database
	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return fmt.Errorf("error connecting to database: %v", err)
	}
	defer db.Close()

	// Test connection
	err = db.Ping()
	if err != nil {
		return fmt.Errorf("error pinging database: %v", err)
	}

	log.Println("Connected to PostgreSQL database")

	// Query cameras
	query := `SELECT id, name, rtsp_main, rtsp_sub, location, created_at, updated_at FROM cameras ORDER BY id`
	rows, err := db.Query(query)
	if err != nil {
		return fmt.Errorf("error querying cameras: %v", err)
	}
	defer rows.Close()

	// Clear existing streams and reload from database
	Config.mutex.Lock()
	Config.Streams = make(map[string]StreamST)
	
	cameraCount := 0
	for rows.Next() {
		var camera Camera
		err := rows.Scan(&camera.ID, &camera.Name, &camera.RtspMain, &camera.RtspSub,
			&camera.Location, &camera.CreatedAt, &camera.UpdatedAt)
		if err != nil {
			log.Printf("Error scanning camera row: %v", err)
			continue
		}

		// Create stream ID as camera1, camera2, etc.
		streamID := fmt.Sprintf("camera%d", camera.ID)
		
		// Use main stream for highest quality
		Config.Streams[streamID] = StreamST{
			URL:          camera.RtspMain,
			OnDemand:     false,
			DisableAudio: true,
			Debug:        false,
			Cl:           make(map[string]viewer),
		}

		cameraCount++
		log.Printf("Loaded camera: %s (ID: %d, Stream: %s, Location: %s)", 
			camera.Name, camera.ID, streamID, camera.Location)
	}
	Config.mutex.Unlock()

	if err = rows.Err(); err != nil {
		return fmt.Errorf("error iterating camera rows: %v", err)
	}

	log.Printf("Successfully loaded %d cameras from database", cameraCount)
	return nil
}
