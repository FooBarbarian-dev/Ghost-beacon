#!/bin/bash
curl -s -X POST -H "Content-Type: application/json" \
  -H "x-hasura-admin-secret: myadminsecret" \
  --data '{"query":"query { oplog_oplogentry_aggregate { aggregate { count } } }"}' \
  http://localhost:8080/v1/graphql
echo ""

curl -s -X POST -H "Content-Type: application/json" \
  -H "x-hasura-admin-secret: myadminsecret" \
  --data '{"query":"query { oplog_oplogentry(where: { tool: { _ilike: \"%4.0%\" } }, limit: 5) { id start_date source_ip dest_ip tool entry_identifier } }"}' \
  http://localhost:8080/v1/graphql
echo ""

curl -s -X POST -H "Content-Type: application/json" \
  -H "x-hasura-admin-secret: myadminsecret" \
  --data '{"query":"query { oplog_oplogentry(where: { extra_fields: { _contains: { collected_from_port: 443 } } }, limit: 5) { source_ip tool extra_fields } }"}' \
  http://localhost:8080/v1/graphql
echo ""
