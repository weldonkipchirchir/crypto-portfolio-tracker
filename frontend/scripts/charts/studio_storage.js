(function(g){'use strict';
function create(o){let ready=false,baseline='',timer=null,running=null,closed=false;
const signature=v=>JSON.stringify(v),status=(kind,text)=>{if(!closed)o.status?.(kind,text)};
async function start(){try{const context=await o.load(o.contextKey);if(context)await o.restore(context);baseline=signature(o.capture());ready=true;status('saved',context?'Saved workspace restored':'Autosave ready')}catch(e){ready=false;status('error','Restore unavailable: '+e.message)}}
function changed(){if(!ready||closed||signature(o.capture())===baseline)return;status('dirty','Unsaved changes');if(timer)clearTimeout(timer);timer=setTimeout(()=>{timer=null;flush().catch(()=>{})},o.delay??900)}
async function flush(force=false){if(timer){clearTimeout(timer);timer=null}if(running){await running;return flush(force)}if(!ready)throw Error('Workspace restore has not completed. Reopen Studio before saving.');const snapshot=o.capture(),encoded=signature(snapshot);if(!force&&encoded===baseline)return;status('saving','Saving setup…');running=(async()=>{try{await o.save(snapshot.key,snapshot.value);await o.save(o.contextKey,snapshot.context);baseline=encoded;status('saved','Setup saved to your account')}catch(e){status('error','Not saved: '+e.message);throw e}})();try{await running}finally{running=null}if(!closed&&signature(o.capture())!==baseline)changed()}
function dispose(){if(timer)clearTimeout(timer);if(ready)flush().catch(()=>{});closed=true}
return {start,changed,flush,dispose};}
g.OrbitStudioStorage={create};
})(typeof window!=='undefined'?window:globalThis);
