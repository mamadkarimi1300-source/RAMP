package config

import (
	"crypto/ed25519"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"time"
)

type Envelope struct {
	Payload json.RawMessage `json:"payload"`
	Signature string `json:"signature"`
}

type Payload struct {
	Version int `json:"version"`
	IssuedAt time.Time `json:"issued_at"`
	ExpiresAt time.Time `json:"expires_at"`
	Bridges []Bridge `json:"bridges"`
}

type Bridge struct {
	ID string `json:"id"`
	Address string `json:"address"`
	ServerName string `json:"server_name"`
	Transports []string `json:"transports"`
}

func VerifySigned(raw []byte, publicKey ed25519.PublicKey, now time.Time) (Payload,error) {
	var envelope Envelope
	if err:=json.Unmarshal(raw,&envelope);err!=nil{return Payload{},fmt.Errorf("decode envelope: %w",err)}
	if len(envelope.Payload)==0 || len(publicKey)!=ed25519.PublicKeySize{return Payload{},errors.New("missing payload or invalid public key")}
	sig,err:=base64.StdEncoding.DecodeString(envelope.Signature)
	if err!=nil{return Payload{},fmt.Errorf("decode signature: %w",err)}
	if !ed25519.Verify(publicKey,envelope.Payload,sig){return Payload{},errors.New("configuration signature is invalid")}
	var payload Payload
	if err:=json.Unmarshal(envelope.Payload,&payload);err!=nil{return Payload{},fmt.Errorf("decode signed payload: %w",err)}
	if payload.Version!=1{return Payload{},fmt.Errorf("unsupported configuration version %d",payload.Version)}
	if payload.IssuedAt.IsZero() || payload.ExpiresAt.IsZero() || !payload.ExpiresAt.After(now) || payload.IssuedAt.After(now.Add(5*time.Minute)) {
		return Payload{},errors.New("configuration is expired or has an invalid issue time")
	}
	for _,b:=range payload.Bridges {
		if b.ID=="" || b.Address=="" || b.ServerName=="" {return Payload{},errors.New("bridge entry is incomplete")}
	}
	return payload,nil
}
