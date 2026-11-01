package access

import "testing"

func TestSelectorPrefersHealthyMeasuredPath(t *testing.T) {
	got,err:=(Selector{}).Select([]Candidate{
		{BridgeID:"a",Transport:"quic",Available:false,RTTMillis:10,ThroughputMbps:100},
		{BridgeID:"b",Transport:"tcp-tls",Available:true,RTTMillis:40,ThroughputMbps:20},
		{BridgeID:"c",Transport:"quic",Available:true,RTTMillis:30,ThroughputMbps:80},
	})
	if err!=nil{t.Fatal(err)}
	if got.BridgeID!="c"{t.Fatalf("selected %q, want c",got.BridgeID)}
}
