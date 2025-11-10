package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	// Load cameras from database
	log.Println("Loading cameras from database...")
	err := LoadCamerasFromDB()
	if err != nil {
		log.Fatalf("Failed to load cameras from database: %v", err)
	}

	go serveHTTP()
	go serveStreams()
	sigs := make(chan os.Signal, 1)
	done := make(chan bool, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		sig := <-sigs
		log.Println(sig)
		done <- true
	}()
	log.Println("Server Start Awaiting Signal")
	<-done
	log.Println("Exiting")
}
