package bridge

import (
	"context"
	"crypto/tls"
	"errors"
	"io"
	"log"
	"net"
	"strconv"
	"sync/atomic"
	"time"

	"github.com/mamadkarimi1300-source/RAMP/protocol"
	"github.com/mamadkarimi1300-source/RAMP/server/internal/egress"
	"github.com/mamadkarimi1300-source/RAMP/storage"
)

var sessionSequence atomic.Uint64

type Config struct {
	ListenAddress string
	CertificateFile string
	KeyFile string
	Token string
	Events *storage.Logger
}

type Server struct {
	cfg Config
	egress egress.Connector
}

func New(cfg Config, connector egress.Connector) (*Server,error) {
	if cfg.ListenAddress=="" || cfg.CertificateFile=="" || cfg.KeyFile=="" || cfg.Token=="" {
		return nil,errors.New("listen address, TLS certificate, TLS key and access token are required")
	}
	if connector==nil { return nil,errors.New("egress connector is required") }
	return &Server{cfg:cfg,egress:connector},nil
}

func (s *Server) record(event storage.Event) {
	if s.cfg.Events != nil { s.cfg.Events.Record(event) }
}

func (s *Server) ListenAndServe(ctx context.Context) error {
	cert,err:=tls.LoadX509KeyPair(s.cfg.CertificateFile,s.cfg.KeyFile)
	if err!=nil{return err}
	ln,err:=tls.Listen("tcp",s.cfg.ListenAddress,&tls.Config{
		MinVersion:tls.VersionTLS13,
		Certificates:[]tls.Certificate{cert},
	})
	if err!=nil{return err}
	defer ln.Close()
	go func(){ <-ctx.Done(); _=ln.Close() }()
	log.Printf("RAMP bridge listening on %s (TLS 1.3)",s.cfg.ListenAddress)
	for {
		conn,err:=ln.Accept()
		if err!=nil {
			if ctx.Err()!=nil{return nil}
			return err
		}
		go s.handle(ctx,conn)
	}
}

func (s *Server) handle(parent context.Context, raw net.Conn) {
	defer raw.Close()
	sessionID := "bridge-" + strconv.FormatUint(sessionSequence.Add(1), 10)
	s.record(storage.Event{SessionID:sessionID, EventType:"connection_accepted", Network:"tcp", Status:"accepted"})
	started := time.Now()
	_ = raw.SetDeadline(started.Add(15*time.Second))
	tlsConn,ok:=raw.(*tls.Conn)
	if !ok {
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Status:"error", ErrorMessage:"accepted connection is not TLS"})
		return
	}
	if err:=tlsConn.Handshake();err!=nil {
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Transport:"tls-tcp", Network:"tcp", Status:"error", ErrorMessage:err.Error()})
		return
	}
	req,err:=protocol.ReadOpenRequest(tlsConn)
	if err!=nil {
		_ = protocol.WriteStatus(tlsConn,protocol.StatusError)
		s.record(storage.Event{SessionID:sessionID, EventType:"handshake_failed", Transport:"tls-tcp", Network:"tcp", Status:"error", ErrorMessage:err.Error()})
		return
	}
	destination := protocol.TargetAddress(req.Host, req.Port)
	if !protocol.TokenEqual(req.Token,s.cfg.Token) {
		_ = protocol.WriteStatus(tlsConn,protocol.StatusError)
		s.record(storage.Event{SessionID:sessionID, EventType:"authentication_failed", Destination:destination, Transport:"tls-tcp", Network:"tcp", Status:"rejected", ErrorMessage:"invalid access token"})
		return
	}
	s.record(storage.Event{SessionID:sessionID, EventType:"transport_selected", Destination:destination, Transport:"tls-tcp", Network:"tcp", Status:"selected"})
	ctx,cancel:=context.WithTimeout(parent,15*time.Second)
	dialStarted := time.Now()
	dst,err:=s.egress.Connect(ctx,req.Host,req.Port)
	dialLatency := time.Since(dialStarted).Milliseconds()
	cancel()
	if err!=nil {
		_ = protocol.WriteStatus(tlsConn,protocol.StatusError)
		s.record(storage.Event{SessionID:sessionID, EventType:"connection_failed", Destination:destination, Transport:"tls-tcp", Network:"tcp", LatencyMS:dialLatency, Status:"error", ErrorMessage:err.Error()})
		log.Printf("egress connect failed host=%q port=%d: %v",req.Host,req.Port,err)
		return
	}
	defer dst.Close()
	if err:=protocol.WriteStatus(tlsConn,protocol.StatusOK);err!=nil{return}
	_ = tlsConn.SetDeadline(time.Time{})
	_ = dst.SetDeadline(time.Time{})
	s.record(storage.Event{SessionID:sessionID, EventType:"connection_established", Destination:destination, Transport:"tls-tcp", Network:"tcp", LatencyMS:dialLatency, Status:"success"})
	sent,received:=pipe(tlsConn,dst)
	s.record(storage.Event{SessionID:sessionID, EventType:"connection_closed", Destination:destination, Transport:"tls-tcp", Network:"tcp", BytesSent:sent, BytesReceived:received, Status:"closed"})
}

// pipe returns tunnel-to-destination bytes first and destination-to-tunnel bytes second.
func pipe(a,b net.Conn) (int64,int64) {
	type result struct { count int64 }
	done:=make(chan result,2)
	go func(){ n,_:=io.Copy(b,a); _=b.Close(); done<-result{count:n} }()
	go func(){ n,_:=io.Copy(a,b); _=a.Close(); done<-result{count:n} }()
	first,second:=<-done,<-done
	return first.count,second.count
}
