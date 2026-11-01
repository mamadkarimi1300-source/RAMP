package bridge

import (
	"context"
	"crypto/tls"
	"errors"
	"io"
	"log"
	"net"
	"time"

	"github.com/mamadkarimi1300-source/RAMP/protocol"
	"github.com/mamadkarimi1300-source/RAMP/server/internal/egress"
)

type Config struct {
	ListenAddress string
	CertificateFile string
	KeyFile string
	Token string
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
	_ = raw.SetDeadline(time.Now().Add(15*time.Second))
	tlsConn,ok:=raw.(*tls.Conn)
	if !ok{return}
	if err:=tlsConn.Handshake();err!=nil{return}
	req,err:=protocol.ReadOpenRequest(tlsConn)
	if err!=nil { _=protocol.WriteStatus(tlsConn,protocol.StatusError); return }
	if !protocol.TokenEqual(req.Token,s.cfg.Token) {
		_ = protocol.WriteStatus(tlsConn,protocol.StatusError)
		return
	}
	ctx,cancel:=context.WithTimeout(parent,15*time.Second)
	dst,err:=s.egress.Connect(ctx,req.Host,req.Port)
	cancel()
	if err!=nil {
		_ = protocol.WriteStatus(tlsConn,protocol.StatusError)
		log.Printf("egress connect failed host=%q port=%d: %v",req.Host,req.Port,err)
		return
	}
	defer dst.Close()
	if err:=protocol.WriteStatus(tlsConn,protocol.StatusOK);err!=nil{return}
	_ = tlsConn.SetDeadline(time.Time{})
	_ = dst.SetDeadline(time.Time{})
	pipe(tlsConn,dst)
}

func pipe(a,b net.Conn) {
	done:=make(chan struct{},2)
	go func(){ _,_=io.Copy(b,a); _=b.Close(); done<-struct{}{} }()
	go func(){ _,_=io.Copy(a,b); _=a.Close(); done<-struct{}{} }()
	<-done
}
