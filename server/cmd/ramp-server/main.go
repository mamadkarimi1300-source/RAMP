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
)

func main() {
	listen:=flag.String("listen",":8443","public bridge listen address")
	cert:=flag.String("cert","","TLS certificate PEM file")
	key:=flag.String("key","","TLS private key PEM file")
	token:=flag.String("token",os.Getenv("RAMP_TOKEN"),"shared access token; prefer RAMP_TOKEN environment variable")
	flag.Parse()
	if *token=="" { log.Fatal("missing token: set RAMP_TOKEN or pass -token") }
	srv,err:=bridge.New(bridge.Config{ListenAddress:*listen,CertificateFile:*cert,KeyFile:*key,Token:*token},egress.TCPConnector{Timeout:10*time.Second})
	if err!=nil{log.Fatal(err)}
	ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
	defer stop()
	if err:=srv.ListenAndServe(ctx);err!=nil{log.Fatal(err)}
}
