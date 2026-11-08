FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.work ./
COPY client/go.mod client/go.mod
COPY server/go.mod server/go.mod
COPY protocol/go.mod protocol/go.mod
COPY storage/go.mod storage/go.mod
COPY client/ client/
COPY server/ server/
COPY protocol/ protocol/
COPY storage/ storage/
WORKDIR /src/server
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/ramp-server ./cmd/ramp-server

FROM alpine:3.20
RUN apk add --no-cache ca-certificates iproute2 && mkdir -p /var/lib/ramp
COPY --from=build /out/ramp-server /usr/local/bin/ramp-server
CMD ["/usr/local/bin/ramp-server"]
