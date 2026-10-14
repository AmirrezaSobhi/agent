"""Real contract mutations, with synthetic bytes and an in-memory Registry only."""
import hashlib
import json
from pathlib import Path
import pytest
from tools.release_sync import gitlab_release_publish as p
from tests.test_gitlab_release_publish import fixture_root, env, FakeAPI, SHA, PIPELINE


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def unified(fixture_root, env):
    root = fixture_root
    tag, version = 'v0.1.5', '0.1.5'
    (root/'agent/__init__.py').write_text('__version__ = "0.1.5"\n')
    old = root/'dist/MT5Agent-v0.1.4.exe'
    (root/'dist/MT5Agent-v0.1.5.exe').write_bytes(old.read_bytes())
    for path in (root/'reports').glob('*.json'):
        r=json.loads(path.read_text());r['candidate_version']=version;r['candidate_filename']='MT5Agent-v0.1.5.exe'
        if path.name=='build.json': r['build_job_id']='10'
        path.write_text(json.dumps(r))
    auth=json.loads((root/'docs/releases/v0.1.4-authorization.json').read_text());auth['tag']=tag;auth['approval_note_id']=93
    auth_path=root/'protected-authorization.json';auth_path.write_text(json.dumps(auth))
    (root/'docs/releases/v0.1.5-release-notes.md').write_text('# MT5Agent v0.1.5\nINTERNAL / PRE-PRODUCTION\nUNSIGNED — NOT APPROVED FOR PUBLIC DISTRIBUTION\n', encoding='utf-8')
    installer=b'tested unified installer';name='MT5Agent-Setup-v0.1.5-windows-x64.exe'
    directory=root/'dist/installer';directory.mkdir()
    (directory/name).write_bytes(installer)
    jobs={'agent':'10','desktop':'11','worker':'12','service':'13'}
    payload={
        'Agent/MT5Agent-v0.1.5.exe':old.read_bytes(),
        'Worker/MT5AgentWorker-v0.1.5.exe':b'worker',
        'Desktop/MT5Agent.Desktop.exe':b'desktop',
        'Service/MT5Agent.Service.exe':b'service',
        'Support/Install-MT5AgentService.ps1':b'install',
        'Support/Save-MT5AgentUserSettings.ps1':b'settings',
        'Support/Set-MT5RuntimeConfiguration.ps1':b'runtime',
        'Worker/Register-PackagedMT5Worker.ps1':b'register',
        'Worker/Unregister-PackagedMT5Worker.ps1':b'unregister'}
    manifest={'schema_version':1,'product':'MT5Agent','version':version,'architecture':'x64',
              'source_commit':SHA,'pipeline_id':PIPELINE,'installer_build_job_id':'13',
              'component_build_jobs':jobs,'setup_filename':name,'setup_size_bytes':len(installer),
              'setup_sha256':digest(installer),'service_identity':'LocalSystem',
              'signing':'unsigned internal artifact; public distribution prohibited',
              'component_versions':{'agent':version,'worker':version,'desktop':version+'.0',
                 'service':version+'.0','runtime_protocol':'1','management_protocol':'1'},
              'files':[{'path':n,'sha256':digest(b),'size_bytes':len(b)} for n,b in payload.items()]}
    mp=directory/(name[:-4]+'.manifest.json');mp.write_text(json.dumps(manifest))
    sp=directory/(name[:-4]+'.sha256');sp.write_text(f'{digest(installer)}  {name}\n')
    verify={'schema_version':1,'status':'PASS','source_commit':SHA,'pipeline_id':PIPELINE,
            'installer_build_job_id':'13','installer_verify_job_id':'14','installer':name,
            'installer_size_bytes':len(installer),'sha256':digest(installer),
            'manifest_sha256':digest(mp.read_bytes()),'sidecar_sha256':digest(sp.read_bytes())}
    (root/'reports/unified-installer-verification.json').write_text(json.dumps(verify))
    (root/'reports/desktop-build.json').write_text(json.dumps({'source_commit':SHA,'pipeline_id':PIPELINE,
       'build_job_id':'11','product_version':version,'desktop_executable_sha256':digest(b'desktop')}))
    (root/'reports/worker-build.json').write_text(json.dumps({'source_commit':SHA,'pipeline_id':PIPELINE,
       'build_job_id':'12','product_version':version,'package_version':version,'sha256':digest(b'worker'),
       'python_runtime_bundled':True,'mt5_dependency_bundled':True,'archive_inspection_success':True,
       'interactive_session_required':True,'terminal_included':False}))
    acceptance={**{k:verify[k] for k in ('schema_version','status','source_commit','pipeline_id','installer',
                   'sha256','installer_size_bytes','installer_build_job_id','installer_verify_job_id')},
                'installer_exit_code':0,'service_session_id':0,'agent_session_id':0,
                'freshness':'FRESH','mt5_connected':True,'no_trading':True,
                'worker_session_id':1,'mt5_session_id':1,'health_worker_session_id':1,
                'soak_seconds':901,'soak_samples':31,'soak_failed_samples':0,
                'captured_at':'2026-10-14T10:00:00Z'}
    ap=root/'protected-windows-acceptance.json';ap.write_text(json.dumps(acceptance))
    values=dict(env,CI_COMMIT_TAG=tag,MT5_RELEASE_CHANNEL='internal',
                MT5_RELEASE_APPROVAL_TOKEN='synthetic-read-only-token',
                MT5_RELEASE_AUTHORIZATION_FILE=str(auth_path),MT5_RELEASE_INSTALLER_ACCEPTANCE_FILE=str(ap))
    return root,values


class UnifiedAPI(FakeAPI):
    def assert_tag_and_main(self,tag,sha):
        assert tag=='v0.1.5' and sha==SHA

    def create_release(self,payload):
        self.mutations.append(('release',payload['tag_name']))
        self.release_data={**payload,'commit':{'id':SHA}}
        return self.release_data


class Approved:
    def assert_owner_authorization_note(self,approval,owner):
        assert approval['approval_note_id']==93 and owner==23
    def assert_independent_owner_approval(self,reference,owner,sha):
        assert reference.endswith('/42') and owner==23 and sha==SHA


def test_unified_assets_publish_exact_tested_bytes_then_read_back_and_retry(unified):
    root,env=unified;api=UnifiedAPI()
    first=p.publish(env,root,dry_run=False,api=api,approval_api=Approved())
    assert first['result']=='published-and-verified'
    assert len(first['assets'])==9
    assert api.release_data['name']=='MT5Agent v0.1.5 — Windows Desktop Integration'
    name='MT5Agent-Setup-v0.1.5-windows-x64.exe'
    assert api.package[name]==(root/'dist/installer'/name).read_bytes()
    assert 'MT5Agent-v0.1.5.exe' not in api.package
    writes=list(api.mutations)
    assert p.publish(env,root,dry_run=False,api=api,approval_api=Approved())['result']=='matching-existing-release'
    assert api.mutations==writes


@pytest.mark.parametrize('file,key,value',[
    ('manifest','source_commit','b'*40),('manifest','pipeline_id','315'),
    ('manifest','setup_sha256','0'*64),('manifest','version','0.1.3'),
    ('verify','status','FAIL'),('verify','installer_build_job_id','99'),
    ('worker','build_job_id','99'),('worker','source_commit','b'*40),('worker','archive_inspection_success',False),
    ('live','sha256','0'*64),('live','pipeline_id','315'),('live','installer_exit_code',1),
    ('live','agent_session_id',1),('live','worker_session_id',True),
    ('live','health_worker_session_id',None),('live','mt5_session_id',2),
    ('live','freshness','STALE'),('live','soak_seconds',899),('live','soak_samples',29),
    ('live','soak_failed_samples',1),('live','no_trading',False)])
def test_bad_provenance_or_real_install_acceptance_rejects_before_writes(unified,file,key,value):
    root,env=unified
    paths={'manifest':root/'dist/installer/MT5Agent-Setup-v0.1.5-windows-x64.manifest.json',
           'verify':root/'reports/unified-installer-verification.json',
           'worker':root/'reports/worker-build.json','live':Path(env['MT5_RELEASE_INSTALLER_ACCEPTANCE_FILE'])}
    path=paths[file];data=json.loads(path.read_text());data[key]=value;path.write_text(json.dumps(data))
    api=UnifiedAPI()
    with pytest.raises(p.PublishError): p.publish(env,root,dry_run=False,api=api,approval_api=Approved())
    assert api.mutations==[]


def test_false_owner_approval_prevents_every_registry_write(unified):
    root,env=unified;api=UnifiedAPI()
    class Denied:
        def assert_independent_owner_approval(self,*args): raise p.PublishError('No real approval')
    with pytest.raises(p.PublishError,match='real approval'):
        p.publish(env,root,dry_run=False,api=api,approval_api=Denied())
    assert api.mutations==[]


@pytest.mark.parametrize('approved,level,commit,accepted',[
    ([{'user':{'id':23}}],30,SHA,True),([],30,SHA,False),
    ([{'user':{'id':17}}],30,SHA,False),([{'user':{'id':'23'}}],30,SHA,False),
    ([{'user':{'id':23}}],20,SHA,False),([{'user':{'id':23}}],30,'b'*40,False)])
def test_live_owner_approval_validates_membership_and_exact_merged_commit(approved,level,commit,accepted):
    client=p.GitLabAPI('https://gitlab.local/api/v4','1','synthetic',authentication_header='PRIVATE-TOKEN')
    values={'/members/all/23':{'id':23,'access_level':level,'state':'active'},
            '/merge_requests/42':{'state':'merged','target_branch':'main','merge_commit_sha':commit},
            '/merge_requests/42/approvals':{'approved_by':approved}}
    client.json=lambda method,path:values[path]
    if accepted: client.assert_independent_owner_approval('https://gitlab.local/root/agent/-/merge_requests/42',23,SHA)
    else:
        with pytest.raises(p.PublishError): client.assert_independent_owner_approval('https://gitlab.local/root/agent/-/merge_requests/42',23,SHA)


def test_approval_token_cannot_write_or_follow_redirects():
    client=p.GitLabAPI('https://gitlab.local/api/v4','1','synthetic',authentication_header='PRIVATE-TOKEN')
    with pytest.raises(p.PublishError,match='read-only'): client.request('PUT','/releases/v0.1.5',b'bad')
    with pytest.raises(p.PublishError,match='redirected'): p._DenyApprovalRedirects().redirect_request()


@pytest.mark.parametrize('missing',['MT5_RELEASE_AUTHORIZATION_FILE','MT5_RELEASE_APPROVAL_TOKEN','MT5_RELEASE_INSTALLER_ACCEPTANCE_FILE'])
def test_missing_approved_configuration_fails_closed(unified,missing):
    _,env=unified;env.pop(missing)
    with pytest.raises(p.PublishError,match=missing):p.validate_environment(env)


@pytest.mark.parametrize('change',['duplicate','traversal','unknown','worker_hash','version'])
def test_payload_forgery_fails_even_if_manifest_digest_is_recomputed(unified,change):
    root,env=unified;mp=root/'dist/installer/MT5Agent-Setup-v0.1.5-windows-x64.manifest.json'
    m=json.loads(mp.read_text())
    if change=='duplicate':m['files'][-1]=dict(m['files'][0])
    elif change=='traversal':m['files'][0]['path']='../Agent/MT5Agent-v0.1.5.exe'
    elif change=='unknown':m['files'][0]['path']='Support/credentials.json'
    elif change=='worker_hash':m['files'][1]['sha256']='0'*64
    else:m['component_versions']['agent']='0.1.3'
    mp.write_text(json.dumps(m));vp=root/'reports/unified-installer-verification.json'
    v=json.loads(vp.read_text());v['manifest_sha256']=digest(mp.read_bytes());vp.write_text(json.dumps(v))
    api=UnifiedAPI()
    with pytest.raises(p.PublishError):p.publish(env,root,dry_run=False,api=api,approval_api=Approved())
    assert api.mutations==[]


def test_corrupt_registry_readback_never_creates_release(unified):
    root,env=unified
    class Corrupt(UnifiedAPI):
        def download_package_file(self,version,name):return b'corrupted bytes'
    api=Corrupt()
    with pytest.raises(p.PublishError):p.publish(env,root,dry_run=False,api=api,approval_api=Approved())
    assert not any(action=='release' for action,_ in api.mutations)


@pytest.mark.parametrize('change', ['missing_id', 'wrong_author', 'edited', 'system', 'altered_body', 'invalid_json'])
def test_owner_record_cannot_be_forged_or_changed_by_variable_writer(change):
    approval={'schema_version':1,'approval_reference':'https://gitlab.local/root/agent/-/merge_requests/42',
              'approval_note_id':93,'commit_sha':SHA,'approved_by_user_id':23}
    body={k:v for k,v in approval.items() if k!='approval_note_id'}
    note={'id':93,'author':{'id':23},'system':False,'created_at':'2026-10-14T05:00:00Z',
          'updated_at':'2026-10-14T05:00:00Z','body':json.dumps(body)}
    if change=='missing_id':approval.pop('approval_note_id')
    elif change=='wrong_author':note['author']['id']=1
    elif change=='edited':note['updated_at']='2026-10-14T05:01:00Z'
    elif change=='system':note['system']=True
    elif change=='altered_body':note['body']=json.dumps({**body,'commit_sha':'b'*40})
    else:note['body']='not json'
    client=p.GitLabAPI('https://gitlab.local/api/v4','1','synthetic',authentication_header='PRIVATE-TOKEN')
    client.json=lambda method,path:note
    with pytest.raises(p.PublishError):client.assert_owner_authorization_note(approval,23)
