FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.work ./
COPY client/go.mod client/go.mod
COPY server/go.mod server/go.mod
COPY protocol/go.mod protocol/go.mod
COPY storage/go.mod storage/go.mod
COPY client/ client/
COPY protocol/ protocol/
COPY storage/ storage/
WORKDIR /src/client
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/ramp-client ./cmd/ramp-client

FROM alpine:3.20
RUN apk add --no-cache ca-certificates iproute2 && mkdir -p /var/lib/ramp
COPY --from=build /out/ramp-client /usr/local/bin/ramp-client
CMD ["/usr/local/bin/ramp-client"]
