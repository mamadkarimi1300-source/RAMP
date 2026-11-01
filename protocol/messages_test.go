package protocol

import (
	"bytes"
	"testing"
)

func TestOpenRequestRoundTrip(t *testing.T) {
	in := OpenRequest{Token: "test-secret", Host: "example.com", Port: 443}
	var buf bytes.Buffer
	if err := WriteOpenRequest(&buf, in); err != nil { t.Fatal(err) }
	got, err := ReadOpenRequest(&buf)
	if err != nil { t.Fatal(err) }
	if got != in { t.Fatalf("got %#v, want %#v", got, in) }
}

func TestTokenEqual(t *testing.T) {
	if !TokenEqual("secret", "secret") { t.Fatal("equal tokens rejected") }
	if TokenEqual("secret", "other") { t.Fatal("different tokens accepted") }
}
