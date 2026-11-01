package session

import (
	"errors"
	"sync"
	"time"
)

type State string

const (
	StateNew State = "new"
	StateConnecting State = "connecting"
	StateActive State = "active"
	StateDegraded State = "degraded"
	StateRecovering State = "recovering"
	StateClosed State = "closed"
)

var ErrInvalidTransition = errors.New("invalid session state transition")

type Session struct {
	ID string
	BridgeID string
	Transport string
	State State
	CreatedAt time.Time
	UpdatedAt time.Time
}

type Manager struct {
	mu sync.RWMutex
	items map[string]Session
}

func NewManager() *Manager { return &Manager{items:make(map[string]Session)} }

func (m *Manager) Create(id string) (Session,error) {
	if id=="" { return Session{},errors.New("session ID is required") }
	m.mu.Lock(); defer m.mu.Unlock()
	if _,exists:=m.items[id];exists{return Session{},errors.New("session already exists")}
	now:=time.Now().UTC()
	s:=Session{ID:id,State:StateNew,CreatedAt:now,UpdatedAt:now}
	m.items[id]=s
	return s,nil
}

func (m *Manager) Transition(id string,next State) (Session,error) {
	m.mu.Lock(); defer m.mu.Unlock()
	s,ok:=m.items[id]; if !ok{return Session{},errors.New("session not found")}
	if !allowed(s.State,next){return s,ErrInvalidTransition}
	s.State=next; s.UpdatedAt=time.Now().UTC(); m.items[id]=s
	return s,nil
}

func allowed(from,to State) bool {
	switch from {
	case StateNew: return to==StateConnecting || to==StateClosed
	case StateConnecting: return to==StateActive || to==StateClosed
	case StateActive: return to==StateDegraded || to==StateClosed
	case StateDegraded: return to==StateRecovering || to==StateClosed
	case StateRecovering: return to==StateActive || to==StateClosed
	default: return false
	}
}

func (m *Manager) Get(id string) (Session,bool) {
	m.mu.RLock(); defer m.mu.RUnlock(); s,ok:=m.items[id]; return s,ok
}
