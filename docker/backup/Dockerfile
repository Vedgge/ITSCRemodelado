FROM postgres:16-alpine
RUN apk add --no-cache tar gzip
COPY docker/backup/backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh
# Nightly at 03:15.
RUN echo "15 3 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1" > /etc/crontabs/root
CMD ["crond", "-f", "-l", "8"]
