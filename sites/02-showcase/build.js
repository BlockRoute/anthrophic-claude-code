const fs = require('fs');
const path = require('path');
const here = __dirname;
const fonts = ['bricolage', 'archivo', 'spline-mono']
  .map((f) => fs.readFileSync(path.join(here, '../_assets/fonts', f + '.inline.css'), 'utf8'))
  .join('\n');
const app = fs.readFileSync(path.join(here, 'app.js'), 'utf8');
let html = fs.readFileSync(path.join(here, 'src.html'), 'utf8');
const site1 = process.env.SITE1_URL || 'https://daniel-yoon-ai-implementation-studio-cd-873bf09417.netlify.app';
html = html.replace('/*__FONTS__*/', fonts).replace('/*__APP__*/', () => app).replace(/__SITE1_URL__/g, site1);
fs.writeFileSync(path.join(here, 'index.html'), html);
console.log('built index.html', (fs.statSync(path.join(here, 'index.html')).size / 1024).toFixed(0) + 'KB');
