package socks5

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"strconv"
	"sync/atomic"
	"time"

	"github.com/mamadkarimi1300-source/RAMP/client/internal/tunnel"
	"github.com/mamadkarimi1300-source/RAMP/storage"
)

var sessionSequence atomic.Uint64

type Server struct {
	Address string
	Dialer *tunnel.Dialer
	Events *storage.Logger
}

func (s *Server) ListenAndServe() error {
	if s.Dialer == nil { return errors.New("SOCKS5 tunnel dialer is required") }
	ln, err := net.Listen("tcp", s.Address)
	if err != nil { return err }
	defer ln.Close()
	for {
		conn, err := ln.Accept()
		if err != nil { return err }
		go s.handle(conn)
	}
}

func (s *Server) record(event storage.Event) {
	if s.Events != nil { s.Events.Record(event) }
}

func (s *Server) handle(local net.Conn) {
	defer local.Close()
	sessionID := "client-" + strconv.FormatUint(sessionSequence.Add(1), 10)
	started := time.Now()
	s.record(storage.Event{SessionID:sessionID, EventType:"connection_accepted", Network:"tcp", Status:"accepted"})
	_ = local.SetDeadline(time.Now().Add(30*time.Second))
	var greeting [2]byte
	if _, err := io.ReadFull(local, greeting[:]); err != nil {
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Status:"error", ErrorMessage:err.Error()})
		return
	}
	if greeting[0] != 5 || greeting[1] == 0 {
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Status:"error", ErrorMessage:"invalid SOCKS5 greeting"})
		return
	}
	methods := make([]byte, int(greeting[1]))
	if _, err := io.ReadFull(local, methods); err != nil {
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Status:"error", ErrorMessage:err.Error()})
		return
	}
	found := false
	for _, m := range methods { if m == 0 { found = true } }
	if !found {
		_, _ = local.Write([]byte{5, 0xff})
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Status:"rejected", ErrorMessage:"no-auth method not offered"})
		return
	}
	if _, err := local.Write([]byte{5, 0}); err != nil { return }

	var head [4]byte
	if _, err := io.ReadFull(local, head[:]); err != nil {
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Status:"error", ErrorMessage:err.Error()})
		return
	}
	if head[0] != 5 || head[1] != 1 || head[2] != 0 {
		_ = writeReply(local, 7)
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Status:"rejected", ErrorMessage:"unsupported SOCKS5 command"})
		return
	}
	host, err := readAddress(local, head[3])
	if err != nil {
		_ = writeReply(local, 8)
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Status:"error", ErrorMessage:err.Error()})
		return
	}
	var portBytes [2]byte
	if _, err := io.ReadFull(local, portBytes[:]); err != nil { return }
	port := binary.BigEndian.Uint16(portBytes[:])
	destination := net.JoinHostPort(host, strconv.Itoa(int(port)))
	_ = local.SetDeadline(time.Time{})

	s.record(storage.Event{SessionID:sessionID, EventType:"transport_selected", Destination:destination, Transport:"tls-tcp", Network:"tcp", Status:"selected"})
	remote, err := s.Dialer.Open(host, port)
	if err != nil {
		_ = writeReply(local, 5)
		s.record(storage.Event{SessionID:sessionID, EventType:"connection_failed", Destination:destination, Transport:"tls-tcp", Network:"tcp", LatencyMS:time.Since(started).Milliseconds(), Status:"error", ErrorMessage:err.Error()})
		return
	}
	defer remote.Close()
	if err := writeReply(local, 0); err != nil { return }
	s.record(storage.Event{SessionID:sessionID, EventType:"connection_established", Destination:destination, Transport:"tls-tcp", Network:"tcp", LatencyMS:time.Since(started).Milliseconds(), Status:"success"})
	sent, received := pipe(local, remote)
	s.record(storage.Event{SessionID:sessionID, EventType:"connection_closed", Destination:destination, Transport:"tls-tcp", Network:"tcp", BytesSent:sent, BytesReceived:received, Status:"closed"})
}

func readAddress(r io.Reader, atyp byte) (string, error) {
	switch atyp {
	case 1:
		b := make([]byte, 4); if _, err := io.ReadFull(r,b); err != nil { return "",err }; return net.IP(b).String(),nil
	case 3:
		var n [1]byte; if _,err:=io.ReadFull(r,n[:]); err!=nil{return "",err}
		if n[0]==0 { return "",errors.New("empty domain") }
		b:=make([]byte,int(n[0])); if _,err:=io.ReadFull(r,b); err!=nil{return "",err}; return string(b),nil
	case 4:
		b:=make([]byte,16); if _,err:=io.ReadFull(r,b); err!=nil{return "",err}; return net.IP(b).String(),nil
	default:
		return "",fmt.Errorf("unsupported SOCKS address type %d",atyp)
	}
}

func writeReply(w io.Writer, code byte) error {
	_,err:=w.Write([]byte{5,code,0,1,0,0,0,0,0,0}); return err
}

// pipe returns client-to-remote bytes first and remote-to-client bytes second.
func pipe(a,b net.Conn) (int64,int64) {
	type result struct { direction int; count int64 }
	done:=make(chan result,2)
	go func(){ n,_:=io.Copy(b,a); _=b.Close(); done<-result{direction:0,count:n} }()
	go func(){ n,_:=io.Copy(a,b); _=a.Close(); done<-result{direction:1,count:n} }()
	var sent,received int64
	for i:=0;i<2;i++ { r:=<-done; if r.direction==0 { sent=r.count } else { received=r.count } }
	return sent,received
}

func ParseAddress(host string, port uint16) string { return net.JoinHostPort(host,strconv.Itoa(int(port))) }
