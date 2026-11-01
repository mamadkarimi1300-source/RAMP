package health

import (
	"sync"
	"time"
)

type Status string

const (
	Unknown Status = "unknown"
	Healthy Status = "healthy"
	Degraded Status = "degraded"
	Unhealthy Status = "unhealthy"
)

type Snapshot struct {
	Component string
	Status Status
	CheckedAt time.Time
	Detail string
}

type Registry struct {
	mu sync.RWMutex
	items map[string]Snapshot
}

func NewRegistry() *Registry { return &Registry{items:make(map[string]Snapshot)} }

func (r *Registry) Report(s Snapshot) {
	if s.Component=="" { return }
	if s.CheckedAt.IsZero() { s.CheckedAt=time.Now().UTC() }
	r.mu.Lock(); defer r.mu.Unlock(); r.items[s.Component]=s
}

func (r *Registry) Get(component string) (Snapshot,bool) {
	r.mu.RLock(); defer r.mu.RUnlock(); s,ok:=r.items[component]; return s,ok
}

func (r *Registry) All() []Snapshot {
	r.mu.RLock(); defer r.mu.RUnlock()
	out:=make([]Snapshot,0,len(r.items))
	for _,s:=range r.items { out=append(out,s) }
	return out
}
