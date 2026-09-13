import { readFile, access } from 'node:fs/promises';
process.env.NODE_ENV='production';
const { createBuilder } = await import('vite');
const { runPrerender } = await import('vinext/internal/build/run-prerender');

// Use Vinext's build/prerender APIs so Windows Node can drain its handles.
// The upstream CLI calls process.exit(0) while libuv is still closing a handle.
// Keep build failures as nonzero exits and retain previous generated files.
const root=process.cwd().replaceAll('\\','/');
const builder=await createBuilder({root,mode:'production',build:{emptyOutDir:false}});
await builder.buildApp();
const result=await runPrerender({root});
if(!result?.routes.some(r=>r.route==='/'&&r.status==='rendered')||result.routes.some(r=>r.status==='error'))throw new Error('The current workspace route did not render successfully.');
const html=await readFile('dist/client/index.html','utf8');
if(!html.includes('Find the right summer'))throw new Error('Expected workspace route was not generated.');
await access('dist/client/index.rsc');
console.log('Build and static-route validation passed.');
