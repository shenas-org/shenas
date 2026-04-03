//! DuckDB connection and system table management.
//!
//! Mirrors the Python `app/db.py` -- same schema, same tables.

use std::path::Path;
use std::sync::Mutex;

use duckdb::{Connection, Result};

pub struct Database {
    conn: Mutex<Connection>,
}

impl Database {
    pub fn open(path: &Path) -> Result<Self> {
        let conn = Connection::open(path)?;
        let db = Self {
            conn: Mutex::new(conn),
        };
        db.ensure_system_tables()?;
        Ok(db)
    }

    pub fn open_memory() -> Result<Self> {
        let conn = Connection::open_in_memory()?;
        let db = Self {
            conn: Mutex::new(conn),
        };
        db.ensure_system_tables()?;
        Ok(db)
    }

    fn ensure_system_tables(&self) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute_batch(
            "CREATE SCHEMA IF NOT EXISTS shenas_system;
             CREATE SEQUENCE IF NOT EXISTS shenas_system.transforms_id_seq START 1;
             CREATE TABLE IF NOT EXISTS shenas_system.plugins (
                 kind VARCHAR NOT NULL,
                 name VARCHAR NOT NULL,
                 enabled BOOLEAN DEFAULT true,
                 added_at TIMESTAMP DEFAULT current_timestamp,
                 updated_at TIMESTAMP DEFAULT current_timestamp,
                 status_changed_at TIMESTAMP,
                 synced_at TIMESTAMP,
                 PRIMARY KEY (kind, name)
             );
             CREATE TABLE IF NOT EXISTS shenas_system.transforms (
                 id INTEGER PRIMARY KEY DEFAULT(nextval('shenas_system.transforms_id_seq')),
                 source_schema VARCHAR NOT NULL,
                 source_table VARCHAR NOT NULL,
                 target_schema VARCHAR NOT NULL,
                 target_table VARCHAR NOT NULL,
                 sql VARCHAR NOT NULL,
                 is_default BOOLEAN DEFAULT false,
                 enabled BOOLEAN DEFAULT true
             );",
        )?;
        Ok(())
    }

    /// Execute a SQL query and return results as JSON rows.
    pub fn query_json(&self, sql: &str) -> Result<Vec<serde_json::Value>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(sql)?;
        let column_count = stmt.column_count();
        let column_names: Vec<String> = (0..column_count)
            .map(|i| stmt.column_name(i).map_or("?", |v| v).to_string())
            .collect();

        let mut rows = Vec::new();
        let mut result_rows = stmt.query([])?;
        while let Some(row) = result_rows.next()? {
            let mut obj = serde_json::Map::new();
            for (i, name) in column_names.iter().enumerate() {
                let val: duckdb::types::Value = row.get(i)?;
                obj.insert(name.clone(), duckdb_value_to_json(val));
            }
            rows.push(serde_json::Value::Object(obj));
        }
        Ok(rows)
    }

    /// List all schemas and their tables.
    pub fn list_tables(&self) -> Result<Vec<serde_json::Value>> {
        self.query_json(
            "SELECT table_schema, table_name, estimated_size
             FROM information_schema.tables
             WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'main')
             ORDER BY table_schema, table_name",
        )
    }

    /// Get database status with schema/table info (matches Python db_status format).
    pub fn status(&self) -> Result<serde_json::Value> {
        let conn = self.conn.lock().unwrap();

        // Get schemas and tables (excluding system schemas and dlt internals)
        let mut stmt = conn.prepare(
            "SELECT table_schema, table_name
             FROM information_schema.tables
             WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'main', 'shenas_system')
             ORDER BY table_schema, table_name",
        )?;

        let mut schemas: std::collections::BTreeMap<String, Vec<serde_json::Value>> =
            std::collections::BTreeMap::new();

        let mut rows = stmt.query([])?;
        while let Some(row) = rows.next()? {
            let schema: String = row.get(0)?;
            let table: String = row.get(1)?;

            // Skip dlt internal tables
            if table.starts_with("_dlt_") {
                continue;
            }

            // Get row count
            let count_sql = format!("SELECT COUNT(*) FROM \"{}\".\"{}\"", schema, table);
            let count: i64 = conn
                .query_row(&count_sql, [], |r| r.get(0))
                .unwrap_or(0);

            schemas
                .entry(schema)
                .or_default()
                .push(serde_json::json!({
                    "name": table,
                    "rows": count,
                }));
        }

        let schemas_list: Vec<serde_json::Value> = schemas
            .into_iter()
            .map(|(name, tables)| {
                serde_json::json!({
                    "name": name,
                    "tables": tables,
                })
            })
            .collect();

        Ok(serde_json::json!({
            "path": "mobile (embedded)",
            "size_mb": 0,
            "schemas": schemas_list,
        }))
    }

    /// Execute a SQL statement (INSERT, DELETE, etc.) -- no results.
    pub fn execute(&self, sql: &str) -> Result<usize> {
        let conn = self.conn.lock().unwrap();
        conn.execute(sql, [])
    }

    /// Run all enabled transforms.
    pub fn run_transforms(&self) -> Result<Vec<String>> {
        let transforms = self.query_json(
            "SELECT id, source_schema, target_schema, target_table, sql
             FROM shenas_system.transforms WHERE enabled = true ORDER BY id",
        )?;
        let mut results = Vec::new();
        let conn = self.conn.lock().unwrap();
        for t in &transforms {
            let sql = t["sql"].as_str().unwrap_or("");
            let target = format!(
                "{}.{}",
                t["target_schema"].as_str().unwrap_or(""),
                t["target_table"].as_str().unwrap_or("")
            );
            match conn.execute_batch(sql) {
                Ok(_) => results.push(format!("OK: {}", target)),
                Err(e) => results.push(format!("ERROR {}: {}", target, e)),
            }
        }
        Ok(results)
    }
}

fn duckdb_value_to_json(val: duckdb::types::Value) -> serde_json::Value {
    match val {
        duckdb::types::Value::Null => serde_json::Value::Null,
        duckdb::types::Value::Boolean(b) => serde_json::Value::Bool(b),
        duckdb::types::Value::TinyInt(n) => serde_json::json!(n),
        duckdb::types::Value::SmallInt(n) => serde_json::json!(n),
        duckdb::types::Value::Int(n) => serde_json::json!(n),
        duckdb::types::Value::BigInt(n) => serde_json::json!(n),
        duckdb::types::Value::Float(n) => serde_json::json!(n),
        duckdb::types::Value::Double(n) => serde_json::json!(n),
        duckdb::types::Value::Text(s) => serde_json::Value::String(s),
        duckdb::types::Value::Timestamp(_, n) => serde_json::json!(n),
        _ => serde_json::Value::String(format!("{:?}", val)),
    }
}
