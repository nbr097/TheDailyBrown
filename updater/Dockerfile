FROM docker:cli
RUN apk add --no-cache socat bash
COPY updater.sh /updater.sh
RUN chmod +x /updater.sh
CMD ["/updater.sh"]
