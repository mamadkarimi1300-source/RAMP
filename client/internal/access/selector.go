package access

import (
	"errors"
	"sort"
)

type Candidate struct {
	BridgeID string
	Transport string
	Available bool
	RTTMillis float64
	ThroughputMbps float64
	RecentFailures int
}

type Selector struct { MaxRecentFailures int }

func (s Selector) Select(candidates []Candidate) (Candidate,error) {
	maxFailures:=s.MaxRecentFailures
	if maxFailures<=0 { maxFailures=3 }
	eligible:=make([]Candidate,0,len(candidates))
	for _,c:=range candidates {
		if c.Available && c.BridgeID!="" && c.Transport!="" && c.RTTMillis>=0 && c.ThroughputMbps>=0 && c.RecentFailures<maxFailures {
			eligible=append(eligible,c)
		}
	}
	if len(eligible)==0{return Candidate{},errors.New("no eligible access path")}
	score:=func(c Candidate) float64 {
		reliability:=1.0/float64(1+c.RecentFailures)
		return (c.ThroughputMbps/(1+c.RTTMillis))*reliability
	}
	sort.SliceStable(eligible,func(i,j int)bool{return score(eligible[i])>score(eligible[j])})
	return eligible[0],nil
}
