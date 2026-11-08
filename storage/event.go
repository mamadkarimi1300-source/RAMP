package storage

import "time"

// Event is a durable observation emitted by a RAMP component.
type Event struct {
	SessionID    string
	Timestamp    time.Time
	EventType    string
	Destination  string
	Transport    string
	Network      string
	LatencyMS    int64
	BytesSent    int64
	BytesReceived int64
	Status       string
	ErrorMessage string
}

// Repository persists component events.
type Repository interface {
	InsertEvent(Event) error
	Close() error
}
