#!/bin/sh
# Creates CouchDB's system databases and the vault database. Safe to re-run.
# The users are server admins defined in couchdb.yaml, not _users documents.
set -eu
C=http://couchdb:5984
A="$COUCHDB_USER:$COUCHDB_PASSWORD"

until curl -fsS -u "$A" "$C/_up" >/dev/null; do sleep 5; done

for db in _users _replicator vault; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -u "$A" -X PUT "$C/$db")
  case $code in 201|202|412) echo "$db: ok" ;; *) echo "creating $db: HTTP $code"; exit 1 ;; esac
done

# Database users from the first version of this script.
for u in obsidian mcp bridge; do
  rev=$(curl -s -u "$A" "$C/_users/org.couchdb.user:$u" | sed -n 's/.*"_rev":"\([^"]*\)".*/\1/p')
  [ -z "$rev" ] || curl -fsS -o /dev/null -u "$A" -X DELETE "$C/_users/org.couchdb.user:$u?rev=$rev"
done
