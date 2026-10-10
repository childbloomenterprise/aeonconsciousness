// Development-only D1/R2 adapters. Never included in the deployed Worker bundle.
import { DatabaseSync } from "node:sqlite";
import { createHash, randomUUID } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const migrations = fileURLToPath(new URL("../drizzle/", import.meta.url));
const digest = (value) => createHash("sha256").update(value).digest("hex");

export function localEnvironment(stateDir) {
  if (stateDir) mkdirSync(stateDir, { recursive: true, mode: 0o700 });
  const db = new DatabaseSync(
    stateDir ? join(stateDir, "control-plane.sqlite") : ":memory:",
  );
  db.exec("PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;");
  if (stateDir) db.exec("PRAGMA journal_mode=WAL;");
  try {
    db.exec(
      "CREATE TABLE IF NOT EXISTS __aeon_local_migrations (name TEXT PRIMARY KEY, sha256 TEXT NOT NULL)",
    );
    for (const name of readdirSync(migrations)
      .filter((f) => f.endsWith(".sql"))
      .sort()) {
      const sql = readFileSync(join(migrations, name), "utf8"),
        checksum = digest(sql);
      const previous = db
        .prepare("SELECT sha256 FROM __aeon_local_migrations WHERE name=?")
        .get(name);
      if (previous) {
        if (previous.sha256 !== checksum)
          throw new Error(`Applied local migration changed: ${name}`);
        continue;
      }
      db.exec("BEGIN IMMEDIATE");
      try {
        db.exec(sql);
        db.prepare("INSERT INTO __aeon_local_migrations VALUES (?,?)").run(
          name,
          checksum,
        );
        db.exec("COMMIT");
      } catch (error) {
        db.exec("ROLLBACK");
        throw error;
      }
    }
  } catch (error) {
    db.close();
    throw error;
  }
  const prepare = (sql) => {
    let values = [];
    return {
      bind(...args) {
        values = args;
        return this;
      },
      first() {
        return db.prepare(sql).get(...values) || null;
      },
      all() {
        return {
          results: db.prepare(sql).all(...values),
          meta: { changes: 0 },
        };
      },
      run() {
        const s = db.prepare(sql);
        const results = /RETURNING/i.test(sql)
          ? s.all(...values)
          : (s.run(...values), []);
        return {
          results,
          meta: {
            changes: Number(db.prepare("SELECT changes() AS n").get().n),
          },
        };
      },
    };
  };
  const objects = new Map(),
    bucketRoot = stateDir ? join(stateDir, "objects") : null;
  if (bucketRoot) mkdirSync(bucketRoot, { recursive: true, mode: 0o700 });
  const objectPath = (key) => join(bucketRoot, digest(key));
  return {
    DB: {
      prepare,
      batch(statements) {
        // No awaits here: concurrent requests cannot interleave the transaction.
        db.exec("BEGIN IMMEDIATE");
        try {
          const result = statements.map((s) => s.run());
          db.exec("COMMIT");
          return result;
        } catch (error) {
          db.exec("ROLLBACK");
          throw error;
        }
      },
    },
    BUCKET: {
      put(key, value) {
        const bytes = new Uint8Array(value);
        if (!bucketRoot) {
          objects.set(key, bytes);
          return;
        }
        const target = objectPath(key),
          temporary = `${target}.${randomUUID()}.tmp`;
        writeFileSync(temporary, bytes, { mode: 0o600 });
        renameSync(temporary, target);
      },
      get(key) {
        if (!bucketRoot)
          return objects.has(key) ? { body: objects.get(key) } : null;
        const target = objectPath(key);
        return existsSync(target) ? { body: readFileSync(target) } : null;
      },
    },
    AEON_ADMIN_KEY: randomUUID() + randomUUID(),
    AEON_OWNER_EMAIL: "local-owner@example.com",
    db,
    objects,
    close() {
      db.close();
    },
  };
}
