// S05 — Usuarios con privilegio mínimo (ejecuta en primer arranque con datos vacíos).
// Requiere MONGO_INITDB_ROOT_* y MONGO_READER_PASSWORD, MONGO_WRITER_PASSWORD, MONGO_ADMIN_PASSWORD.
// mongosh expone process.env con variables del contenedor.

(function () {
  function mustGet(name) {
    var v = process.env[name];
    if (!v || String(v).trim() === "") {
      throw new Error("Variable de entorno obligatoria para init MongoDB: " + name);
    }
    return v;
  }

  var readerPwd = mustGet("MONGO_READER_PASSWORD");
  var writerPwd = mustGet("MONGO_WRITER_PASSWORD");
  var adminPwd = mustGet("MONGO_ADMIN_PASSWORD");

  var nyxar = db.getSiblingDB("nyxar");

  nyxar.createUser({
    user: "nyxar_reader",
    pwd: readerPwd,
    roles: [{ role: "read", db: "nyxar" }],
  });

  nyxar.createUser({
    user: "nyxar_writer",
    pwd: writerPwd,
    roles: [{ role: "readWrite", db: "nyxar" }],
  });

  nyxar.createUser({
    user: "nyxar_admin",
    pwd: adminPwd,
    roles: [
      { role: "dbAdmin", db: "nyxar" },
      { role: "readWrite", db: "nyxar" },
    ],
  });

  // Intento best-effort: el usuario por defecto "admin" en admin suele no existir si ya usás MONGO_INITDB_ROOT_*.
  try {
    db.getSiblingDB("admin").updateUser("admin", { roles: [] });
  } catch (e) {
    print("Info: no se modificó usuario admin (esperado si no existe): " + e);
  }
})();
