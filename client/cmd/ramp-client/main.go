package main

import (
	"flag"
	"log"
	"os"

	"github.com/mamadkarimi1300-source/RAMP/client/internal/ingress/socks5"
	"github.com/mamadkarimi1300-source/RAMP/client/internal/tunnel"
	"github.com/mamadkarimi1300-source/RAMP/storage"
	"github.com/mamadkarimi1300-source/RAMP/storage/sqlite"
)

func main() {
	if err := run(); err != nil { log.Print(err); os.Exit(1) }
}

func run() error {
	listen := flag.String("listen", "127.0.0.1:1080", "local SOCKS5 listen address")
	server := flag.String("server", "", "RAMP server address, host:port")
	serverName := flag.String("server-name", "", "TLS server name in the server certificate")
	ca := flag.String("ca", "", "PEM CA certificate used to verify the server")
	token := flag.String("token", os.Getenv("RAMP_TOKEN"), "shared access token; prefer RAMP_TOKEN environment variable")
	dbPath := flag.String("db", envOr("RAMP_CLIENT_DB_PATH", "data/client.db"), "SQLite event database path")
	flag.Parse()

	store, err := sqlite.Open(*dbPath)
	if err != nil { return err }
	events := storage.NewLogger(store, 1024)
	defer func() {
		if err := events.Close(); err != nil { log.Printf("close client event database: %v", err) }
		log.Printf("client event logger: dropped=%d write_errors=%d", events.Dropped(), events.WriteErrors())
	}()

	dialer, err := tunnel.New(tunnel.Config{Address:*server, ServerName:*serverName, CAFile:*ca, Token:*token})
	if err != nil { return err }
	log.Printf("RAMP client: SOCKS5 listening on %s; upstream=%s; event_db=%s", *listen, *server, *dbPath)
	return (&socks5.Server{Address:*listen, Dialer:dialer, Events:events}).ListenAndServe()
}

func envOr(key, fallback string) string {
	if value := os.Getenv(key); value != "" { return value }
	return fallback
}
