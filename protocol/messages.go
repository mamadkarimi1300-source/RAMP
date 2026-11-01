package protocol

import (
	"crypto/subtle"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
)

const (
	Magic      = "RAMP"
	Version    = uint8(1)
	MaxToken   = 4096
	MaxHost    = 253
	StatusOK   = uint8(0)
	StatusError = uint8(1)
)

var ErrInvalidRequest = errors.New("invalid RAMP tunnel request")

// OpenRequest is the first message sent inside an authenticated TLS connection.
// The token is protected in transit by TLS; it is not a substitute for TLS.
type OpenRequest struct {
	Token string
	Host  string
	Port  uint16
}

func (r OpenRequest) Validate() error {
	if len(r.Token) == 0 || len(r.Token) > MaxToken {
		return fmt.Errorf("%w: token length", ErrInvalidRequest)
	}
	if len(r.Host) == 0 || len(r.Host) > MaxHost {
		return fmt.Errorf("%w: host length", ErrInvalidRequest)
	}
	if r.Port == 0 {
		return fmt.Errorf("%w: port is zero", ErrInvalidRequest)
	}
	return nil
}

func WriteOpenRequest(w io.Writer, r OpenRequest) error {
	if err := r.Validate(); err != nil {
		return err
	}
	if _, err := io.WriteString(w, Magic); err != nil {
		return err
	}
	if err := binary.Write(w, binary.BigEndian, Version); err != nil {
		return err
	}
	if err := binary.Write(w, binary.BigEndian, uint16(len(r.Token))); err != nil {
		return err
	}
	if _, err := io.WriteString(w, r.Token); err != nil {
		return err
	}
	if err := binary.Write(w, binary.BigEndian, uint16(len(r.Host))); err != nil {
		return err
	}
	if _, err := io.WriteString(w, r.Host); err != nil {
		return err
	}
	return binary.Write(w, binary.BigEndian, r.Port)
}

func ReadOpenRequest(r io.Reader) (OpenRequest, error) {
	var req OpenRequest
	magic := make([]byte, len(Magic))
	if _, err := io.ReadFull(r, magic); err != nil {
		return req, err
	}
	if string(magic) != Magic {
		return req, ErrInvalidRequest
	}
	var version uint8
	if err := binary.Read(r, binary.BigEndian, &version); err != nil {
		return req, err
	}
	if version != Version {
		return req, fmt.Errorf("%w: unsupported version %d", ErrInvalidRequest, version)
	}
	var tokenLen uint16
	if err := binary.Read(r, binary.BigEndian, &tokenLen); err != nil {
		return req, err
	}
	if tokenLen == 0 || tokenLen > MaxToken {
		return req, ErrInvalidRequest
	}
	token := make([]byte, tokenLen)
	if _, err := io.ReadFull(r, token); err != nil {
		return req, err
	}
	var hostLen uint16
	if err := binary.Read(r, binary.BigEndian, &hostLen); err != nil {
		return req, err
	}
	if hostLen == 0 || hostLen > MaxHost {
		return req, ErrInvalidRequest
	}
	host := make([]byte, hostLen)
	if _, err := io.ReadFull(r, host); err != nil {
		return req, err
	}
	if err := binary.Read(r, binary.BigEndian, &req.Port); err != nil {
		return req, err
	}
	req.Token, req.Host = string(token), string(host)
	if err := req.Validate(); err != nil {
		return OpenRequest{}, err
	}
	return req, nil
}

func WriteStatus(w io.Writer, status uint8) error {
	return binary.Write(w, binary.BigEndian, status)
}

func ReadStatus(r io.Reader) (uint8, error) {
	var status uint8
	err := binary.Read(r, binary.BigEndian, &status)
	return status, err
}

// TokenEqual performs constant-time comparison after checking equal lengths.
func TokenEqual(got, want string) bool {
	if len(got) != len(want) {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(got), []byte(want)) == 1
}

func TargetAddress(host string, port uint16) string {
	return net.JoinHostPort(host, fmt.Sprintf("%d", port))
}
