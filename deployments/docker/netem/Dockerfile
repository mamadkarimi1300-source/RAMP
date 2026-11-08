FROM alpine:3.20
RUN apk add --no-cache iproute2 iptables tcpdump
COPY start-router.sh /usr/local/bin/start-router.sh
RUN chmod 0755 /usr/local/bin/start-router.sh
ENTRYPOINT ["/usr/local/bin/start-router.sh"]
