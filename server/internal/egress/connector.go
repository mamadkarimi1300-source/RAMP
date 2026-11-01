package egress

import (
	"context"
	"net"
	"time"

	"github.com/mamadkarimi1300-source/RAMP/protocol"
)

type Connector interface {
	Connect(context.Context, string, uint16) (net.Conn, error)
}

type TCPConnector struct { Timeout time.Duration }

func (c TCPConnector) Connect(ctx context.Context, host string, port uint16) (net.Conn, error) {
	timeout := c.Timeout
	if timeout <= 0 { timeout = 10*time.Second }
	d := net.Dialer{Timeout:timeout}
	return d.DialContext(ctx, "tcp", protocol.TargetAddress(host,port))
}
