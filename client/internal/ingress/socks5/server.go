package socks5

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"strconv"
	"time"

	"github.com/mamadkarimi1300-source/RAMP/client/internal/tunnel"
)

type Server struct {
	Address string
	Dialer *tunnel.Dialer
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

func (s *Server) handle(local net.Conn) {
	defer local.Close()
	_ = local.SetDeadline(time.Now().Add(30*time.Second))
	var greeting [2]byte
	if _, err := io.ReadFull(local, greeting[:]); err != nil { return }
	if greeting[0] != 5 || greeting[1] == 0 { return }
	methods := make([]byte, int(greeting[1]))
	if _, err := io.ReadFull(local, methods); err != nil { return }
	found := false
	for _, m := range methods { if m == 0 { found = true } }
	if !found { _, _ = local.Write([]byte{5, 0xff}); return }
	if _, err := local.Write([]byte{5, 0}); err != nil { return }

	var head [4]byte
	if _, err := io.ReadFull(local, head[:]); err != nil { return }
	if head[0] != 5 || head[1] != 1 || head[2] != 0 {
		_ = writeReply(local, 7)
		return
	}
	host, err := readAddress(local, head[3])
	if err != nil { _ = writeReply(local, 8); return }
	var portBytes [2]byte
	if _, err := io.ReadFull(local, portBytes[:]); err != nil { return }
	port := binary.BigEndian.Uint16(portBytes[:])
	_ = local.SetDeadline(time.Time{})

	remote, err := s.Dialer.Open(host, port)
	if err != nil { _ = writeReply(local, 5); return }
	defer remote.Close()
	if err := writeReply(local, 0); err != nil { return }
	pipe(local, remote)
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

func pipe(a,b net.Conn) {
	done:=make(chan struct{},2)
	go func(){ _,_=io.Copy(b,a); _=b.Close(); done<-struct{}{} }()
	go func(){ _,_=io.Copy(a,b); _=a.Close(); done<-struct{}{} }()
	<-done
}

func ParseAddress(host string, port uint16) string { return net.JoinHostPort(host,strconv.Itoa(int(port))) }
