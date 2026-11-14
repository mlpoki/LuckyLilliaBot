const fs = require('node:fs');
const path = require('node:path');
const root = __dirname;
const desktop = fs.readFileSync(path.join(root, 'package-kind.txt'), 'utf8').trim() === 'Desktop';
const base = root;
const qq = path.join(base, 'bin', 'qq', 'QQ.app', 'Contents', 'MacOS', 'QQ');
const pmhqConfig = path.join(base, 'bin', 'pmhq', 'pmhq_config.json');
const config = JSON.parse(fs.readFileSync(pmhqConfig, 'utf8'));
config.qq_path = qq;
config.default_port = 13000;
fs.writeFileSync(pmhqConfig, JSON.stringify(config, null, 2));
if (desktop) {
  const file = path.join(base, 'app_settings.json');
  const settings = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : {};
  Object.assign(settings, {
    qq_path: qq,
    pmhq_path: path.join(base, 'bin', 'pmhq', 'pmhq'),
    node_path: path.join(base, 'bin', 'llbot', 'node'),
    llbot_path: path.join(base, 'bin', 'llbot', 'llbot.js'),
  });
  if (!fs.existsSync(file)) {
    Object.assign(settings, { auto_start_bot: false, auto_login: false, auto_login_qq: '', headless: false });
  }
  if (process.argv.includes('--ci')) settings.auto_start_bot = true;
  fs.writeFileSync(file, JSON.stringify(settings, null, 2));
}
