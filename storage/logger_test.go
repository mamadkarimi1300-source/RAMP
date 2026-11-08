package storage

import (
	"errors"
	"sync"
	"testing"
	"time"
)

type memoryRepository struct {
	mu sync.Mutex
	events []Event
	closed bool
	fail bool
}

func (r *memoryRepository) InsertEvent(event Event) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.fail { return errors.New("write failed") }
	r.events = append(r.events, event)
	return nil
}

func (r *memoryRepository) Close() error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.closed = true
	return nil
}

func TestLoggerFlushesQueuedEventsOnClose(t *testing.T) {
	repo := &memoryRepository{}
	logger := NewLogger(repo, 8)
	for i := 0; i < 3; i++ {
		if !logger.Record(Event{SessionID:"test", EventType:"connection_accepted", Timestamp:time.Now()}) {
			t.Fatal("event unexpectedly dropped")
		}
	}
	if err := logger.Close(); err != nil { t.Fatal(err) }
	repo.mu.Lock()
	defer repo.mu.Unlock()
	if len(repo.events) != 3 { t.Fatalf("got %d persisted events, want 3", len(repo.events)) }
	if !repo.closed { t.Fatal("repository was not closed") }
}

func TestLoggerCountsWriteErrors(t *testing.T) {
	repo := &memoryRepository{fail:true}
	logger := NewLogger(repo, 2)
	logger.Record(Event{SessionID:"test", EventType:"failed-write"})
	if err := logger.Close(); err != nil { t.Fatal(err) }
	if logger.WriteErrors() != 1 { t.Fatalf("got %d write errors, want 1", logger.WriteErrors()) }
}
