package tunnel

import (
	"crypto/tls"
	"crypto/x509"
	"errors"
	"fmt"
	"net"
	"os"
	"time"

	"github.com/mamadkarimi1300-source/RAMP/protocol"
)

type Config struct {
	Address    string
	ServerName string
	CAFile     string
	Token      string
}

type Dialer struct {
	cfg Config
	roots *x509.CertPool
}

func New(cfg Config) (*Dialer, error) {
	if cfg.Address == "" || cfg.ServerName == "" || cfg.CAFile == "" || cfg.Token == "" {
		return nil, errors.New("address, server name, CA file and token are required")
	}
	pem, err := os.ReadFile(cfg.CAFile)
	if err != nil { return nil, fmt.Errorf("read CA file: %w", err) }
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(pem) { return nil, errors.New("CA file contains no valid certificates") }
	return &Dialer{cfg:cfg, roots:roots}, nil
}

func (d *Dialer) Open(host string, port uint16) (*tls.Conn, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	raw, err := (&net.Dialer{Timeout:10*time.Second}).DialContext(ctx,"tcp",d.cfg.Address)
	if err != nil { return nil, fmt.Errorf("TCP dial: %w",err) }
	conn := tls.Client(raw,&tls.Config{
		MinVersion:tls.VersionTLS13,
		RootCAs:d.roots,
		ServerName:d.cfg.ServerName,
	})
	if err:=conn.HandshakeContext(ctx);err!=nil { raw.Close(); return nil,fmt.Errorf("TLS handshake: %w",err) }
	if err:=protocol.WriteOpenRequest(conn,protocol.OpenRequest{Token:d.cfg.Token,Host:host,Port:port});err!=nil {
		conn.Close()
		return nil,fmt.Errorf("write tunnel request: %w",err)
	}
	status,err:=protocol.ReadStatus(conn)
	if err!=nil { conn.Close(); return nil,fmt.Errorf("read tunnel status: %w",err) }
	if status!=protocol.StatusOK { conn.Close(); return nil,errors.New("server rejected tunnel request") }
	return conn,nil
}
