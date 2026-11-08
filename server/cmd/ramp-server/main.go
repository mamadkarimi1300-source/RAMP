package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/mamadkarimi1300-source/RAMP/server/internal/bridge"
	"github.com/mamadkarimi1300-source/RAMP/server/internal/egress"
	"github.com/mamadkarimi1300-source/RAMP/storage"
	"github.com/mamadkarimi1300-source/RAMP/storage/sqlite"
)

func main() {
	if err := run(); err != nil { log.Print(err); os.Exit(1) }
}

func run() error {
	listen:=flag.String("listen",":8443","public bridge listen address")
	cert:=flag.String("cert","","TLS certificate PEM file")
	key:=flag.String("key","","TLS private key PEM file")
	token:=flag.String("token",os.Getenv("RAMP_TOKEN"),"shared access token; prefer RAMP_TOKEN environment variable")
	dbPath:=flag.String("db",envOr("RAMP_SERVER_DB_PATH","data/server.db"),"SQLite event database path")
	flag.Parse()
	if *token=="" { returnErr := "missing token: set RAMP_TOKEN or pass -token"; return errors.New(returnErr) }

	store,err:=sqlite.Open(*dbPath)
	if err!=nil{return err}
	events:=storage.NewLogger(store,1024)
	defer func(){
		if err:=events.Close();err!=nil{log.Printf("close server event database: %v",err)}
		log.Printf("server event logger: dropped=%d write_errors=%d",events.Dropped(),events.WriteErrors())
	}()

	srv,err:=bridge.New(bridge.Config{ListenAddress:*listen,CertificateFile:*cert,KeyFile:*key,Token:*token,Events:events},egress.TCPConnector{Timeout:10*time.Second})
	if err!=nil{return err}
	ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
	defer stop()
	log.Printf("RAMP bridge event database: %s",*dbPath)
	return srv.ListenAndServe(ctx)
}

func envOr(key,fallback string) string {
	if value:=os.Getenv(key);value!="" { return value }
	return fallback
}
