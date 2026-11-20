const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),directory=path.join(root,'tests/frontend');
const files=fs.readdirSync(directory).filter(n=>n.endsWith('.test.cjs')||n==='test_ui.cjs'||n.endsWith('_ui_test.js')).sort();let failed=0;
for(const file of files){const result=spawnSync(process.execPath,[path.join(directory,file)],{cwd:root,encoding:'utf8'});if(result.status!==0){failed++;process.stdout.write(file+'\n'+(result.stdout||'')+(result.stderr||''))}}
console.log(`Frontend: ${files.length-failed}/${files.length} test files passed.`);process.exitCode=failed?1:0;
