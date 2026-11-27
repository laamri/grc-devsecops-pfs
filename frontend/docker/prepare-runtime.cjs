// Run in the builder before any standalone files enter a published layer.
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(process.argv[2] || '.next/standalone');
const fields = new Set([
  'encryptionKey', 'previewModeSigningKey', 'previewModeEncryptionKey', 'previewModeId',
]);
const removed = new Set();
function files(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(dir, entry.name);
    return entry.isDirectory() ? files(file) : entry.isFile() ? [file] : [];
  });
}
const manifests = files(path.join(root, '.next')).filter(file => file.endsWith('.json'));
for (const file of manifests) {
  let changed = false;
  const manifest = JSON.parse(fs.readFileSync(file, 'utf8'), (key, value) => {
    if (fields.has(key) && typeof value === 'string' && value) {
      removed.add(value);
      changed = true;
      return '';
    }
    return value;
  });
  if (changed) fs.writeFileSync(file, JSON.stringify(manifest));
}
if (removed.size !== 4) throw new Error('Unexpected Next.js runtime key layout');
const actionJson = fs.readFileSync(path.join(root, '.next/server/server-reference-manifest.json'), 'utf8');
fs.writeFileSync(path.join(root, '.next/server/server-reference-manifest.js'),
  `self.__RSC_SERVER_MANIFEST=${JSON.stringify(actionJson)}`);
// Fail closed if Next.js starts embedding any of these values in another artifact.
for (const file of files(root)) {
  const content = fs.readFileSync(file);
  for (const value of removed) {
    if (content.includes(Buffer.from(value))) {
      throw new Error(`Build key remains in ${path.relative(root, file)} (value omitted)`);
    }
  }
}
console.log('Standalone prepared: build-time cryptographic material removed');
