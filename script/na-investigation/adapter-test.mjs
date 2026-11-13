// Exercise the pinned public TS adapter, never load the native .node or run the app.
import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { createServer, request } from 'node:http'
import { stripTypeScriptTypes } from 'node:module'
import vm from 'node:vm'

const source = readFileSync('baseline/src/main/qqProtocol/direct-lib/sign.ts', 'utf8')
const requests = []
const server = createServer((req, res) => {
  requests.push({ address: req.socket.localAddress, path: req.url })
  const fixtures = { '/valid': [200, 'valid'], '/invalid': [401, 'invalid'], '/forbidden': [403, 'invalid'], '/retry': [503, 'retry:fixture unavailable'] }
  const [code, body] = fixtures[req.url] ?? [404, 'invalid']
  res.writeHead(code).end(body)
})
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const port = server.address().port
let proxy = {}
let mode = 'valid'
let received
const context = vm.createContext({ Buffer, console })
const noop = () => {}
const stubs = {
  '@/common/logger': { getLogger: () => ({ info: noop, warn: noop, error: noop, debug: noop }), isDebugEnabled: () => false },
  './profiles': { getActiveProfile: () => ({ family: 'linux' }) },
  '@/common/utils/environment': { getCdn: () => 'cf', getProtocol: () => 'linux' },
  './machineGuid': { loadMachineGuidSync: noop },
  './watch/device32': { device32FromGuid: noop },
  './macosDevice': { getMacosDevice: noop },
  './sign-proxy': { getSignProxy: () => proxy },
  '@/common/globalVars': { authTokenStatus: {} },
}
const module = new vm.SourceTextModule(stripTypeScriptTypes(source), { context })
await module.link(specifier => {
  const values = stubs[specifier]
  assert.ok(values, `Unexpected import: ${specifier}`)
  return new vm.SyntheticModule(Object.keys(values), function () {
    for (const [key, value] of Object.entries(values)) this.setExport(key, value)
  }, { context })
})
await module.evaluate()
const validate = module.namespace.validateAuthToken
const results = []
async function check(name, test) { await test(); results.push({ name, passed: true }) }
try {
  await check('empty token rejected before native access', async () => assert.equal(await validate('  '), 'invalid'))
  await check('missing native export returns retryable Error', async () => assert.equal((await validate('fixture')).message.includes('validateAuthToken'), true))
  proxy.validateAuthToken = async args => {
    received = args
    // This fixture adapter is NOT a reconstruction of the undocumented native HTTP protocol.
    return new Promise((resolve, reject) => {
      request({ host: '127.0.0.1', port, path: '/' + mode, method: 'GET', agent: false }, res => {
        let data = ''; res.on('data', chunk => { data += chunk }); res.on('end', () => resolve(data))
      }).on('error', reject).end()
    })
  }
  await check('valid result and trimmed token/CDN passed to native interface', async () => {
    assert.equal(await validate(' fixture '), 'valid')
    assert.equal(received.authToken, 'fixture'); assert.equal(received.cdn, 'cf')
  })
  for (const fixture of ['invalid', 'forbidden']) {
    mode = fixture
    await check(fixture + ' native result rejected', async () => assert.equal(await validate('fixture'), 'invalid'))
  }
  mode = 'retry'
  await check('native retry returned as Error', async () => assert.equal((await validate('fixture')).message, 'fixture unavailable'))
  proxy.validateAuthToken = async () => { throw new Error('offline fixture') }
  await check('native exception preserved', async () => assert.equal((await validate('fixture')).message, 'offline fixture'))
  assert.equal(requests.length, 4)
  assert.ok(requests.every(r => r.address === '127.0.0.1'))
} finally {
  await new Promise(resolve => server.close(resolve))
  writeFileSync('evidence/adapter-tests.json', JSON.stringify({
    baseline: 'dc2b2b90092ef0f571b5546878288b83fff1e436', results, requests,
    scope: 'Public TS adapter with synthetic native import and loopback fixture. No native code, real signatures, login, token issuance, expiry or revocation verified.',
  }, null, 2))
}
console.log(`${results.length} public adapter checks passed; ${requests.length} fixture requests, all loopback`)
