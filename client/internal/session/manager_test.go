package session

import "testing"

func TestSessionLifecycle(t *testing.T) {
	m:=NewManager()
	if _,err:=m.Create("s1");err!=nil{t.Fatal(err)}
	for _,state:=range []State{StateConnecting,StateActive,StateDegraded,StateRecovering,StateActive,StateClosed}{
		if _,err:=m.Transition("s1",state);err!=nil{t.Fatalf("transition to %s: %v",state,err)}
	}
	if _,err:=m.Transition("s1",StateActive);err!=ErrInvalidTransition{t.Fatalf("expected invalid transition, got %v",err)}
}
