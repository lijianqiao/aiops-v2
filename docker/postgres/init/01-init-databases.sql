-- Bootstrap auxiliary databases for the local Phase 1 stack.
--
-- The default ``POSTGRES_DB`` (aiops) is created by the postgres entrypoint.
-- NetBox and Langfuse each need their own database **owned by the aiops user**
-- so their schema migrations can issue CREATE statements without hitting the
-- PostgreSQL 15+ default that revokes CREATE on ``public`` for non-owners.
CREATE DATABASE netbox OWNER aiops;
CREATE DATABASE langfuse OWNER aiops;
