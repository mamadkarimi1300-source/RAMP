package main

import (
	"flag"
	"log"
	"os"

	"github.com/mamadkarimi1300-source/RAMP/client/internal/ingress/socks5"
	"github.com/mamadkarimi1300-source/RAMP/client/internal/tunnel"
)

func main() {
	listen := flag.String("listen", "127.0.0.1:1080", "local SOCKS5 listen address")
	server := flag.String("server", "", "RAMP server address, host:port")
	serverName := flag.String("server-name", "", "TLS server name in the server certificate")
	ca := flag.String("ca", "", "PEM CA certificate used to verify the server")
	token := flag.String("token", os.Getenv("RAMP_TOKEN"), "shared access token; prefer RAMP_TOKEN environment variable")
	flag.Parse()

	dialer, err := tunnel.New(tunnel.Config{Address:*server, ServerName:*serverName, CAFile:*ca, Token:*token})
	if err != nil { log.Fatal(err) }
	log.Printf("RAMP client: SOCKS5 listening on %s; upstream=%s", *listen, *server)
	log.Fatal((&socks5.Server{Address:*listen, Dialer:dialer}).ListenAndServe())
}
