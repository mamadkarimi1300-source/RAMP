package sqlite

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/mamadkarimi1300-source/RAMP/storage"
)

func TestInsertEventPersistsConnectionLog(t *testing.T) {
	path := filepath.Join(t.TempDir(), "nested", "ramp.db")
	db, err := Open(path)
	if err != nil { t.Fatal(err) }
	defer db.Close()

	event := storage.Event{
		SessionID: "session-test", Timestamp: time.Date(2026, 11, 8, 10, 0, 0, 0, time.UTC),
		EventType: "connection_established", Destination: "example.com:443",
		Transport: "tls-tcp", Network: "tcp", LatencyMS: 42, Status: "success",
	}
	if err := db.InsertEvent(event); err != nil { t.Fatal(err) }

	var sessionID, eventType, destination, status string
	var latency int64
	err = db.db.QueryRow("SELECT session_id, event_type, destination, latency_ms, status FROM connection_logs").Scan(
		&sessionID, &eventType, &destination, &latency, &status)
	if err != nil { t.Fatal(err) }
	if sessionID != event.SessionID || eventType != event.EventType || destination != event.Destination || latency != event.LatencyMS || status != event.Status {
		t.Fatalf("unexpected stored event: %q %q %q %d %q", sessionID, eventType, destination, latency, status)
	}
}

func TestOpenMigratesExistingDatabase(t *testing.T) {
	path := filepath.Join(t.TempDir(), "existing.db")
	first, err := Open(path)
	if err != nil { t.Fatal(err) }
	if err := first.Close(); err != nil { t.Fatal(err) }
	second, err := Open(path)
	if err != nil { t.Fatal(err) }
	defer second.Close()
	if _, err := second.db.Exec("SELECT COUNT(*) FROM connection_logs"); err != nil { t.Fatal(err) }
}
