package tunnel

import (
	"crypto/tls"
	"crypto/x509"
	"errors"
	"fmt"
	"os"

	"github.com/mamadkarimi1300-source/RAMP/protocol"
)

type Config struct {
	Address    string
	ServerName string
	CAFile     string
	Token      string
}

type Dialer struct { cfg Config }

func New(cfg Config) (*Dialer, error) {
	if cfg.Address == "" || cfg.ServerName == "" || cfg.CAFile == "" || cfg.Token == "" {
		return nil, errors.New("address, server name, CA file and token are required")
	}
	pem, err := os.ReadFile(cfg.CAFile)
	if err != nil { return nil, fmt.Errorf("read CA file: %w", err) }
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(pem) { return nil, errors.New("CA file contains no valid certificates") }
	_ = roots
	return &Dialer{cfg: cfg}, nil
}

func (d *Dialer) Open(host string, port uint16) (*tls.Conn, error) {
	pem, err := os.ReadFile(d.cfg.CAFile)
	if err != nil { return nil, fmt.Errorf("read CA file: %w", err) }
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(pem) { return nil, errors.New("CA file contains no valid certificates") }
	raw, err := tls.Dial("tcp", d.cfg.Address, &tls.Config{
		MinVersion: tls.VersionTLS13,
		RootCAs: roots,
		ServerName: d.cfg.ServerName,
	})
	if err != nil { return nil, fmt.Errorf("TLS dial: %w", err) }
	if err := protocol.WriteOpenRequest(raw, protocol.OpenRequest{Token:d.cfg.Token, Host:host, Port:port}); err != nil {
		raw.Close()
		return nil, fmt.Errorf("write tunnel request: %w", err)
	}
	status, err := protocol.ReadStatus(raw)
	if err != nil { raw.Close(); return nil, fmt.Errorf("read tunnel status: %w", err) }
	if status != protocol.StatusOK { raw.Close(); return nil, errors.New("server rejected tunnel request") }
	return raw, nil
}
