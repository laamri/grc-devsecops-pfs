// Packaging contract: no generated key survives into the standalone image;
// Next.js receives valid, consistent keys only after container startup.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { test } = require('node:test');
const { initialize } = require('../frontend/docker/start.cjs');
const prepare = path.resolve(__dirname, '../frontend/docker/prepare-runtime.cjs');

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pfs-next-runtime-'));
  fs.mkdirSync(path.join(root, '.next/server'), { recursive: true });
  const keys = {
    encryptionKey: crypto.randomBytes(32).toString('base64'),
    previewModeId: crypto.randomBytes(16).toString('hex'),
    previewModeSigningKey: crypto.randomBytes(32).toString('hex'),
    previewModeEncryptionKey: crypto.randomBytes(32).toString('hex'),
  };
  const write = (file, data) => fs.writeFileSync(path.join(root, file), JSON.stringify(data));
  const read = file => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
  write('.next/server/server-reference-manifest.json', { node: {}, edge: {}, encryptionKey: keys.encryptionKey });
  fs.writeFileSync(path.join(root, '.next/server/server-reference-manifest.js'),
    `self.__RSC_SERVER_MANIFEST=${JSON.stringify(JSON.stringify({ node: {}, edge: {}, encryptionKey: keys.encryptionKey }))}`);
  const { encryptionKey: _unused, ...preview } = keys;
  write('.next/server/preview-props.json', preview);
  write('.next/prerender-manifest.json', { version: 4, routes: {}, preview });
  return { root, keys, read, write };
}

test('packaging removes build keys, startup restores valid coherent runtime keys', () => {
  const f = fixture();
  try {
    const result = spawnSync(process.execPath, [prepare, f.root]);
    assert.equal(result.status, 0);
    const sanitized = JSON.stringify([
      f.read('.next/server/server-reference-manifest.json'),
      f.read('.next/server/preview-props.json'), f.read('.next/prerender-manifest.json'),
    ]);
    assert(Object.values(f.keys).every(value => !sanitized.includes(value)));
    assert(!fs.readFileSync(path.join(f.root, '.next/server/server-reference-manifest.js'), 'utf8').includes(f.keys.encryptionKey));
    initialize(f.root);
    const first = f.read('.next/server/preview-props.json');
    assert.deepEqual(first, f.read('.next/prerender-manifest.json').preview);
    assert.equal(Buffer.from(f.read('.next/server/server-reference-manifest.json').encryptionKey, 'base64').length, 32);
    assert.equal(Buffer.from(first.previewModeEncryptionKey, 'hex').length, 32);
    initialize(f.root);
    assert.notEqual(f.read('.next/server/preview-props.json').previewModeSigningKey, first.previewModeSigningKey);
  } finally { fs.rmSync(f.root, { recursive: true }); }
});

test('packaging rejects a key newly embedded outside the known JSON fields', () => {
  const f = fixture();
  try {
    fs.writeFileSync(path.join(f.root, '.next/server/unexpected.js'), JSON.stringify(f.keys.encryptionKey));
    const result = spawnSync(process.execPath, [prepare, f.root], { encoding: 'utf8' });
    assert.notEqual(result.status, 0);
    assert(!result.stderr.includes(f.keys.encryptionKey));
  } finally { fs.rmSync(f.root, { recursive: true }); }
});

test('replicas can use a mounted runtime key set; invalid keys fail without disclosure', () => {
  const f = fixture();
  const old = process.env.PFS_NEXT_RUNTIME_KEYS_FILE;
  try {
    const supplied = path.join(f.root, 'mounted-keys.json');
    process.env.PFS_NEXT_RUNTIME_KEYS_FILE = supplied;
    fs.writeFileSync(supplied, JSON.stringify(f.keys));
    initialize(f.root);
    initialize(f.root);
    assert.equal(f.read('.next/server/preview-props.json').previewModeId, f.keys.previewModeId);
    fs.writeFileSync(supplied, JSON.stringify({ ...f.keys, previewModeSigningKey: null }));
    assert.throws(() => initialize(f.root), /Invalid runtime previewModeSigningKey \(value omitted\)/);
  } finally {
    if (old === undefined) delete process.env.PFS_NEXT_RUNTIME_KEYS_FILE;
    else process.env.PFS_NEXT_RUNTIME_KEYS_FILE = old;
    fs.rmSync(f.root, { recursive: true });
  }
});
