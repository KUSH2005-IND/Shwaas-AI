import type { Mutation } from "./types";
// Only pending mutations are persisted. No bearer tokens or record cache in localStorage.
const dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
  const req = indexedDB.open("shwaas-clinical-outbox", 1);
  req.onupgradeneeded = () => {
    req.result.createObjectStore("keys");
    req.result.createObjectStore("queue", { keyPath: "id" });
  };
  req.onsuccess = () => resolve(req.result);
  req.onerror = () => reject(req.error);
});
async function read<T>(
  store: string,
  key: IDBValidKey,
): Promise<T | undefined> {
  const db = await dbPromise;
  return new Promise((resolve, reject) => {
    const r = db.transaction(store).objectStore(store).get(key);
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
async function write(store: string, value: unknown, key?: IDBValidKey) {
  const db = await dbPromise;
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
const keyPromises = new Map<string, Promise<CryptoKey>>();
function key(owner: string) {
  if (!keyPromises.has(owner))
    keyPromises.set(
      owner,
      (async () => {
        const existing = await read<CryptoKey>("keys", owner);
        if (existing) return existing;
        const k = await crypto.subtle.generateKey(
          { name: "AES-GCM", length: 256 },
          false,
          ["encrypt", "decrypt"],
        );
        // Insert, never replace: simultaneous tabs must agree on one encryption key.
        const db = await dbPromise;
        try {
          await new Promise<void>((resolve, reject) => {
            const tx = db.transaction("keys", "readwrite");
            tx.objectStore("keys").add(k, owner);
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
          });
          return k;
        } catch (error) {
          const winner = await read<CryptoKey>("keys", owner);
          if (!winner) throw error;
          return winner;
        }
      })(),
    );
  return keyPromises.get(owner)!;
}
export async function enqueue(m: Mutation) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv, additionalData: new TextEncoder().encode(m.owner) },
    await key(m.owner),
    new TextEncoder().encode(JSON.stringify(m)),
  );
  await write("queue", { id: m.id, owner: m.owner, iv, ciphertext });
}
export async function pending(owner: string): Promise<Mutation[]> {
  const db = await dbPromise;
  const all = await new Promise<any[]>((resolve, reject) => {
    const r = db.transaction("queue").objectStore("queue").getAll();
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
  const result = [];
  for (const item of all.filter((x) => x.owner === owner)) {
    const plain = await crypto.subtle.decrypt(
      {
        name: "AES-GCM",
        iv: item.iv,
        additionalData: new TextEncoder().encode(owner),
      },
      await key(owner),
      item.ciphertext,
    );
    result.push(JSON.parse(new TextDecoder().decode(plain)));
  }
  return result.sort((a, b) => a.created.localeCompare(b.created));
}
export async function remove(id: string) {
  const db = await dbPromise;
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction("queue", "readwrite");
    tx.objectStore("queue").delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
