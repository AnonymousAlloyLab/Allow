"""One isolated preliminary build; no active formal project mutation."""
import json,pathlib,subprocess,shutil,tempfile
p=pathlib.Path(__file__).resolve().parent;root=p.parents[2]
d=json.loads((p/'existing-type-inventory.json').read_text());res={}
with tempfile.TemporaryDirectory(prefix='allow-image-preliminary-') as temp:
 w=pathlib.Path(temp)/'formal';shutil.copytree(root/'formal',w,ignore=shutil.ignore_patterns('.lake'))
 r=subprocess.run(['lake','build'],cwd=w,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (p/'preliminary-build.log').write_text(r.stdout);assert r.returncode==0,r.stdout
 for group,rows in d['groups'].items():
  text='import Allow\n' + ('\n'.join('example : ('+typ+') := @'+sym for sym,typ in rows.items()) if group=='inherited' else '\n'.join('#check '+sym for sym in rows))+'\n'
  (w/'Audit.lean').write_text(text)
  r=subprocess.run(['lake','env','lean','Audit.lean'],cwd=w,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (p/('preliminary-'+group+'.log')).write_text(r.stdout);assert r.returncode==0,(group,r.stdout[:300])
  if group!='inherited':assert r.stdout=='\n'.join(rows.values())+'\n',group
  res[group]={'propositions':len(rows),'exact_audit_pass':True}
 shutil.copyfile(p/'ImmutableImage.lean',w/'Candidate.lean')
 r=subprocess.run(['lake','env','lean','Candidate.lean'],cwd=w,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (p/'preliminary-candidate.log').write_text(r.stdout);assert r.returncode==0,r.stdout
(p/'preliminary-formal-report.json').write_text(json.dumps({'status':'PRELIMINARY_ONE_ISOLATED_BUILD_NOT_FINAL_TWO_BUILDS','groups':res,'existing_total':280,'candidate_theorems':7,'axiom_audit':'pending'},indent=2)+'\n')
