// Initialize writable container files before Next.js reads its manifests.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

function initialize(root) {
  const supplied = process.env.PFS_NEXT_RUNTIME_KEYS_FILE
    ? JSON.parse(fs.readFileSync(process.env.PFS_NEXT_RUNTIME_KEYS_FILE, 'utf8')) : null;
  const keys = supplied || {
    encryptionKey: crypto.randomBytes(32).toString('base64'),
    previewModeId: crypto.randomBytes(16).toString('hex'),
    previewModeSigningKey: crypto.randomBytes(32).toString('hex'),
    previewModeEncryptionKey: crypto.randomBytes(32).toString('hex'),
  };
  if (process.env.NEXT_SERVER_ACTIONS_ENCRYPTION_KEY) {
    keys.encryptionKey = process.env.NEXT_SERVER_ACTIONS_ENCRYPTION_KEY;
  }
  if (typeof keys.encryptionKey !== 'string'
    || ![16, 24, 32].includes(Buffer.from(keys.encryptionKey, 'base64').length)
    || Buffer.from(keys.encryptionKey, 'base64').toString('base64') !== keys.encryptionKey) {
    throw new Error('Invalid runtime encryptionKey (value omitted)');
  }
  for (const [field, length] of [
    ['previewModeId', 32], ['previewModeSigningKey', 64], ['previewModeEncryptionKey', 64],
  ]) {
    if (typeof keys[field] !== 'string'
      || !new RegExp(`^[a-f0-9]{${length}}$`, 'i').test(keys[field])) {
      throw new Error(`Invalid runtime ${field} (value omitted)`);
    }
  }
  const actionFile = path.join(root, '.next/server/server-reference-manifest.json');
  const previewFile = path.join(root, '.next/server/preview-props.json');
  const prerenderFile = path.join(root, '.next/prerender-manifest.json');
  const actions = JSON.parse(fs.readFileSync(actionFile, 'utf8'));
  const preview = JSON.parse(fs.readFileSync(previewFile, 'utf8'));
  const prerender = JSON.parse(fs.readFileSync(prerenderFile, 'utf8'));
  actions.encryptionKey = keys.encryptionKey;
  for (const field of ['previewModeId', 'previewModeSigningKey', 'previewModeEncryptionKey']) {
    preview[field] = keys[field];
    prerender.preview[field] = keys[field];
  }
  for (const [file, data] of [[actionFile, actions], [previewFile, preview], [prerenderFile, prerender]]) {
    fs.writeFileSync(`${file}.runtime`, JSON.stringify(data), { mode: 0o600 });
    fs.renameSync(`${file}.runtime`, file);
  }
  const actionJs = path.join(root, '.next/server/server-reference-manifest.js');
  fs.writeFileSync(`${actionJs}.runtime`,
    `self.__RSC_SERVER_MANIFEST=${JSON.stringify(JSON.stringify(actions))}`, { mode: 0o600 });
  fs.renameSync(`${actionJs}.runtime`, actionJs);
}

module.exports = { initialize };
if (require.main === module) {
  const root = path.resolve(__dirname, '..');
  initialize(root);
  require(path.join(root, 'server.js'));
}
