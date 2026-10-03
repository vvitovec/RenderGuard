import {mkdir,copyFile} from 'node:fs/promises';
await mkdir('dist/swagger',{recursive:true});
for(const name of ['swagger-ui-bundle.js','swagger-ui.css']){
 await copyFile('node_modules/swagger-ui-dist/'+name,'dist/swagger/'+name);
}
