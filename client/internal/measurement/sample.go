package measurement

import "time"

type Sample struct {
	ObservedAt time.Time
	RTT time.Duration
	ThroughputMbps float64
	Available bool
	Failure string
}

func (s Sample) Valid() bool {
	return s.RTT>=0 && s.ThroughputMbps>=0 && (s.Available || s.Failure!="")
}
