#!/bin/sh
# Creates the vault database and its two users, and limits the database to them.
# Safe to re-run: existing objects are kept and the users' passwords reset to the
# Secret's values.
set -eu
C=http://couchdb:5984
A="$COUCHDB_USER:$COUCHDB_PASSWORD"

until curl -fsS -u "$A" "$C/_up" >/dev/null; do sleep 5; done

for db in _users _replicator vault; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -u "$A" -X PUT "$C/$db")
  case $code in 201|202|412) ;; *) echo "creating $db: HTTP $code"; exit 1 ;; esac
done

user() {
  rev=$(curl -s -u "$A" "$C/_users/org.couchdb.user:$1" | sed -n 's/.*"_rev":"\([^"]*\)".*/\1/p')
  code=$(printf '{"name":"%s","password":"%s","roles":[],"type":"user"%s}' \
      "$1" "$2" "${rev:+,\"_rev\":\"$rev\"}" |
    curl -s -o /dev/null -w '%{http_code}' -u "$A" -X PUT -H 'Content-Type: application/json' \
      --data-binary @- "$C/_users/org.couchdb.user:$1")
  case $code in 201|202) echo "user $1: ok" ;; *) echo "user $1: HTTP $code"; exit 1 ;; esac
}
user obsidian "$OBSIDIAN_PASSWORD"
user mcp "$MCP_PASSWORD"

# The Obsidian apps administer the database (LiveSync writes its own settings
# documents); the MCP server for Hermes only reads and writes notes.
code=$(curl -s -o /dev/null -w '%{http_code}' -u "$A" -X PUT -H 'Content-Type: application/json' \
  --data-binary '{"admins":{"names":["obsidian"],"roles":[]},"members":{"names":["obsidian","mcp"],"roles":[]}}' \
  "$C/vault/_security")
[ "$code" = 200 ] || { echo "vault security: HTTP $code"; exit 1; }
echo "vault: ok"
