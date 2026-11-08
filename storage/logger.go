package storage

import (
	"sync"
	"sync/atomic"
)

// Logger decouples network handlers from durable storage using a bounded queue.
// Record never waits for a database write; events are dropped when the queue is full.
type Logger struct {
	repo Repository
	queue chan Event
	mu sync.Mutex
	closed bool
	dropped atomic.Uint64
	writeErrors atomic.Uint64
	done chan struct{}
}

func NewLogger(repo Repository, queueSize int) *Logger {
	if queueSize < 1 { queueSize = 256 }
	l := &Logger{repo: repo, queue: make(chan Event, queueSize), done: make(chan struct{})}
	go l.writeLoop()
	return l
}

func (l *Logger) Record(event Event) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.closed {
		l.dropped.Add(1)
		return false
	}
	select {
	case l.queue <- event:
		return true
	default:
		l.dropped.Add(1)
		return false
	}
}

func (l *Logger) Dropped() uint64 { return l.dropped.Load() }
func (l *Logger) WriteErrors() uint64 { return l.writeErrors.Load() }

func (l *Logger) writeLoop() {
	defer close(l.done)
	for event := range l.queue {
		if err := l.repo.InsertEvent(event); err != nil {
			l.writeErrors.Add(1)
		}
	}
}

func (l *Logger) Close() error {
	l.mu.Lock()
	if !l.closed {
		l.closed = true
		close(l.queue)
	}
	l.mu.Unlock()
	<-l.done
	return l.repo.Close()
}
