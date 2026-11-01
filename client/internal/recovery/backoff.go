package recovery

import "time"

// Backoff returns a capped exponential delay. Callers should add bounded jitter
// before scheduling retries to avoid synchronized reconnect storms.
func Backoff(attempt int, base, maximum time.Duration) time.Duration {
	if base<=0 { base=time.Second }
	if maximum<base { maximum=base }
	if attempt<0 { attempt=0 }
	delay:=base
	for i:=0;i<attempt && delay<maximum;i++ {
		if delay>maximum/2 { return maximum }
		delay*=2
	}
	if delay>maximum{return maximum}
	return delay
}
