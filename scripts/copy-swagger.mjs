import {mkdir,copyFile,cp} from 'node:fs/promises';
await mkdir('dist/swagger',{recursive:true});
for(const name of ['swagger-ui-bundle.js','swagger-ui.css']){
 await copyFile('node_modules/swagger-ui-dist/'+name,'dist/swagger/'+name);
}
// Original third-party notices accompany the shipped font/runtime assets.
await copyFile('docs/third-party-licenses.md','dist/third-party-licenses.txt');
await cp('docs/third-party/notices','dist/licenses',{recursive:true});
