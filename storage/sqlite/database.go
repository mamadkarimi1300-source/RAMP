package sqlite

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/mamadkarimi1300-source/RAMP/storage"
	_ "modernc.org/sqlite"
)

type Database struct { db *sql.DB }

func Open(path string) (*Database, error) {
	if path == "" { return nil, fmt.Errorf("database path is required") }
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, fmt.Errorf("create database directory: %w", err)
	}
	db, err := sql.Open("sqlite", path)
	if err != nil { return nil, fmt.Errorf("open sqlite database: %w", err) }
	db.SetMaxOpenConns(1)
	fail := func(err error) (*Database, error) { _ = db.Close(); return nil, err }
	if _, err = db.Exec("PRAGMA journal_mode=WAL"); err != nil { return fail(fmt.Errorf("enable WAL: %w", err)) }
	if _, err = db.Exec("PRAGMA busy_timeout=5000"); err != nil { return fail(fmt.Errorf("set busy timeout: %w", err)) }
	if _, err = db.Exec(schema); err != nil { return fail(fmt.Errorf("migrate event schema: %w", err)) }
	return &Database{db: db}, nil
}

const schema = `
CREATE TABLE IF NOT EXISTS connection_logs (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	session_id TEXT NOT NULL,
	timestamp TEXT NOT NULL,
	event_type TEXT NOT NULL,
	destination TEXT NOT NULL DEFAULT '',
	transport TEXT NOT NULL DEFAULT '',
	network TEXT NOT NULL DEFAULT '',
	latency_ms INTEGER NOT NULL DEFAULT 0,
	bytes_sent INTEGER NOT NULL DEFAULT 0,
	bytes_received INTEGER NOT NULL DEFAULT 0,
	status TEXT NOT NULL DEFAULT '',
	error_message TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_connection_logs_timestamp ON connection_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_connection_logs_session_id ON connection_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_connection_logs_destination ON connection_logs(destination);
CREATE INDEX IF NOT EXISTS idx_connection_logs_event_type ON connection_logs(event_type);
`

func (d *Database) InsertEvent(event storage.Event) error {
	if event.Timestamp.IsZero() { event.Timestamp = time.Now().UTC() }
	_, err := d.db.Exec(`
		INSERT INTO connection_logs (
			session_id, timestamp, event_type, destination, transport, network,
			latency_ms, bytes_sent, bytes_received, status, error_message
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		event.SessionID, event.Timestamp.UTC().Format(time.RFC3339Nano), event.EventType,
		event.Destination, event.Transport, event.Network, event.LatencyMS,
		event.BytesSent, event.BytesReceived, event.Status, event.ErrorMessage)
	if err != nil { return fmt.Errorf("insert connection event: %w", err) }
	return nil
}

func (d *Database) Close() error { return d.db.Close() }
