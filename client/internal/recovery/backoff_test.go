package recovery

import (
	"testing"
	"time"
)

func TestBackoffCaps(t *testing.T) {
	if got:=Backoff(0,time.Second,8*time.Second);got!=time.Second{t.Fatal(got)}
	if got:=Backoff(5,time.Second,8*time.Second);got!=8*time.Second{t.Fatal(got)}
}
