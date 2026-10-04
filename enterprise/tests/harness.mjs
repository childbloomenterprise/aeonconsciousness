import { DatabaseSync } from "node:sqlite";
import { readFileSync, readdirSync } from "node:fs";
export function environment(file = ":memory:") {
  const db = new DatabaseSync(file);
  db.exec("PRAGMA foreign_keys=ON");
  for (const f of readdirSync("drizzle").filter((f) => f.endsWith(".sql")))
    db.exec(readFileSync(`drizzle/${f}`, "utf8"));
  const prepare = (sql) => {
    let values = [];
    return {
      bind(...args) {
        values = args;
        return this;
      },
      async first() {
        return db.prepare(sql).get(...values) || null;
      },
      async all() {
        return {
          results: db.prepare(sql).all(...values),
          meta: { changes: 0 },
        };
      },
      async run() {
        const s = db.prepare(sql);
        let results = [];
        if (/RETURNING/i.test(sql)) results = s.all(...values);
        else s.run(...values);
        return {
          results,
          meta: {
            changes: Number(db.prepare("SELECT changes() AS n").get().n),
          },
        };
      },
    };
  };
  const objects = new Map();
  return {
    DB: {
      prepare,
      async batch(statements) {
        db.exec("BEGIN IMMEDIATE");
        try {
          const result = [];
          for (const s of statements) result.push(await s.run());
          db.exec("COMMIT");
          return result;
        } catch (e) {
          db.exec("ROLLBACK");
          throw e;
        }
      },
    },
    BUCKET: {
      async put(k, v) {
        objects.set(k, new Uint8Array(v));
      },
      async get(k) {
        return objects.has(k) ? { body: objects.get(k) } : null;
      },
    },
    AEON_ADMIN_KEY: "test-admin-secret-long-and-never-deployed",
    db,
    objects,
  };
}
export function headers(subject = "owner", extra = {}) {
  return {
    "oai-authenticated-user-id": subject,
    "oai-authenticated-user-email": `${subject}@example.com`,
    origin: "https://console.test",
    "content-type": "application/json",
    ...extra,
  };
}
