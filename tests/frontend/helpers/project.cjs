const fs=require('node:fs'),path=require('node:path');
const PROJECT_ROOT=path.resolve(__dirname,'../../..');
const paths=require('../../../config/source_paths.json');
function sourcePath(name){const value=String(name);return path.isAbsolute(value)?value:path.join(PROJECT_ROOT,paths[value]||value)}
function readProjectFile(name,...options){return fs.readFileSync(sourcePath(name),...options)}
module.exports={PROJECT_ROOT,sourcePath,readProjectFile};
