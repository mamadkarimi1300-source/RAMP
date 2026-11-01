package config

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"testing"
	"time"
)

func TestVerifySignedConfig(t *testing.T) {
	pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
	now:=time.Now().UTC()
	payload:=Payload{Version:1,IssuedAt:now.Add(-time.Minute),ExpiresAt:now.Add(time.Hour),Bridges:[]Bridge{{ID:"b1",Address:"127.0.0.1:8443",ServerName:"bridge.example",Transports:[]string{"tcp-tls"}}}}
	body,err:=json.Marshal(payload);if err!=nil{t.Fatal(err)}
	sig:=ed25519.Sign(priv,body)
	raw,err:=json.Marshal(Envelope{Payload:body,Signature:base64.StdEncoding.EncodeToString(sig)});if err!=nil{t.Fatal(err)}
	if _,err:=VerifySigned(raw,pub,now);err!=nil{t.Fatal(err)}
}
